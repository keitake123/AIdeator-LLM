import os
import time
import json
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Use a constant User-Agent for both token and GraphQL requests
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/99.0.4844.74 Safari/537.36"
)

# Custom exception for rate limiting
class RateLimitExceeded(Exception):
    """Exception raised when API rate limit is exceeded."""
    pass

# API Request Counter to track and limit requests
class APIRequestCounter:
    def __init__(self, daily_limit=950, hourly_limit=100):
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit
        self.daily_requests = 0
        self.hourly_requests = 0
        self.daily_reset = time.time() + 86400  # 24 hours
        self.hourly_reset = time.time() + 3600  # 1 hour
    
    def check_limits(self):
        while True:
            now = time.time()
            # Reset counters if needed
            if now > self.daily_reset:
                self.daily_requests = 0
                self.daily_reset = now + 86400
            if now > self.hourly_reset:
                self.hourly_requests = 0
                self.hourly_reset = now + 3600

            # If over daily limit, sleep until reset
            if self.daily_requests >= self.daily_limit:
                wait_time = self.daily_reset - now
                print(f"Daily API limit hit. Waiting {wait_time/60:.1f} minutes…")
                time.sleep(wait_time)
                continue  # re-check after sleep

            # If over hourly limit, sleep until reset
            if self.hourly_requests >= self.hourly_limit:
                wait_time = self.hourly_reset - now
                print(f"Hourly API limit hit. Waiting {wait_time/60:.1f} minutes…")
                time.sleep(wait_time)
                continue

            break
        return True
    
    def increment(self):
        self.daily_requests += 1
        self.hourly_requests += 1


def get_oauth_token(client_id: str, client_secret: str) -> Optional[str]:
    """
    Obtain an OAuth2 client_credentials token from Product Hunt.
    Includes browser-like headers to bypass Cloudflare challenge.
    """
    token_url = "https://api.producthunt.com/v2/oauth/token"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        "Origin": "https://api.producthunt.com",
        "Referer": "https://api.producthunt.com/"
    }
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    try:
        resp = requests.post(
            token_url,
            json=payload,
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        print(f"Failed to get token: {resp.status_code}\n{resp.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Token request error: {e}")
        return None

    data = resp.json()
    token = data.get("access_token")
    if not token:
        print(f"No access_token in response: {data}")
    return token


class ProductHuntScraper:
    """
    A scraper for Product Hunt with improved chunking and rate limit handling.
    """
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        base_delay: float = 2.0,  # Increased base delay
        checkpoint_dir: str = "data/checkpoints"
    ):
        # Load credentials
        self.client_id = client_id or os.getenv("PRODUCTHUNT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("PRODUCTHUNT_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing Product Hunt credentials."
                " Set PRODUCTHUNT_CLIENT_ID and PRODUCTHUNT_CLIENT_SECRET in .env"
            )
        
        # Fetch OAuth token
        self.access_token = get_oauth_token(self.client_id, self.client_secret)
        if not self.access_token:
            raise ValueError("Failed to obtain OAuth token")

        # GraphQL endpoint and headers
        self.api_url = "https://api.producthunt.com/v2/api/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT
        }

        # Rate limit settings
        self.request_delay = base_delay
        self.last_request_time = 0.0
        self.retry_count = 0
        self.max_retries = 5
        
        # Request counter for tracking API limits
        self.request_counter = APIRequestCounter()
        
        # Checkpoint directory
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        # Checkpoint file for tracking overall progress
        self.checkpoint_file = os.path.join(self.checkpoint_dir, "scraping_progress.json")

        self.items_since_flush   = 0             # how many new items since last write
        self.flush_threshold     = 100           # flush when this many accumulated
        self.all_products        = {}            # global store of everything so far
        self.global_save_path    = None          # where to write the combined JSON

    def _respect_rate_limit(self) -> None:
        """Respect rate limits with exponential backoff on 429 errors"""
        # First check if we're approaching API limits
        self.request_counter.check_limits()
        
        # Then handle regular rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        
        # If we've had 429 errors recently, add exponential backoff
        if self.retry_count > 0:
            backoff_time = min(300, 2 ** self.retry_count)  # Cap at 5 minutes
            print(f"⚠️ Rate limited, backing off for {backoff_time} seconds...")
            time.sleep(backoff_time)
            # Decrease retry count over time
            self.retry_count = max(0, self.retry_count - 1)
        
        self.last_request_time = time.time()
        self.request_counter.increment()

    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load enhanced checkpoint data with product-level tracking"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, "r") as f:
                    checkpoint = json.load(f)
                    print(f"Loaded checkpoint from {self.checkpoint_file}")
                    
                    # Ensure the structure includes product tracking if it's an older checkpoint
                    if "product_tracking" not in checkpoint:
                        checkpoint["product_tracking"] = {
                            "seen_products": {},  # Dictionary to store seen product IDs by period
                            "last_product_ids": {}  # Last product ID seen in each period
                        }
                    return checkpoint
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading checkpoint: {e}")
        
        # Default checkpoint structure with product tracking
        return {
            "last_completed": {
                "year": None,
                "month": None
            },
            "completed_periods": {},
            "pagination_cursors": {},  # Keep for backward compatibility
            "product_tracking": {
                "seen_products": {},  # Dictionary to store seen product IDs by period
                "last_product_ids": {}  # Last product ID seen in each period
            },
            "stats": {
                "total_products": 0
            }
        }

    def _save_checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """Save enhanced checkpoint data"""
        try:
            with open(self.checkpoint_file + ".tmp", 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            os.replace(self.checkpoint_file + ".tmp", self.checkpoint_file)
            print(f"Checkpoint saved with product-level tracking")
        except IOError as e:
            print(f"Error saving checkpoint: {e}")

    def _update_checkpoint_with_product(self, checkpoint: Dict[str, Any], 
                                    period_name: str, product_id: str) -> None:
        """Update checkpoint with a seen product ID"""
        if "product_tracking" not in checkpoint:
            checkpoint["product_tracking"] = {
                "seen_products": {},
                "last_product_ids": {}
            }
        
        # Initialize period tracking if needed
        if period_name not in checkpoint["product_tracking"]["seen_products"]:
            checkpoint["product_tracking"]["seen_products"][period_name] = []
        
        # Add product ID to seen products if not already there
        if product_id not in checkpoint["product_tracking"]["seen_products"][period_name]:
            checkpoint["product_tracking"]["seen_products"][period_name].append(product_id)
        
        # Update last seen product ID
        checkpoint["product_tracking"]["last_product_ids"][period_name] = product_id

    def _fetch_products_for_period(
        self,
        start_date: str,
        end_date: str,
        period_name: str,
        save_path: Optional[str] = None,
        max_products: Optional[int] = None,
        resume_cursor: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Fetch products for a specific time period with product-level tracking.
        Skips already seen products and continues from exactly where we left off.
        """
        # GraphQL query with date filtering
        query = """
        query ProductsByDate($first: Int!, $after: String, $postedAfter: DateTime!, $postedBefore: DateTime!) {
        posts(
            first: $first,
            after: $after,
            postedAfter: $postedAfter,
            postedBefore: $postedBefore,
            order: VOTES
        ) {
            pageInfo {
            hasNextPage
            endCursor
            }
            edges {
            node {
                id
                name
                tagline
                description
                website
                votesCount
                thumbnail {
                url
                }
            }
            }
        }
        }
        """
        
        # Load checkpoint to get seen products
        checkpoint = self._load_checkpoint()
        product_tracking = checkpoint.get("product_tracking", {"seen_products": {}, "last_product_ids": {}})
        seen_products = set(product_tracking.get("seen_products", {}).get(period_name, []))
        
        print(f"Starting fetch for {period_name}" + (f" resuming from cursor" if resume_cursor else ""))
        print(f"Already seen {len(seen_products)} products in this period")
        
        # Create set of all product keys for duplicate detection
        existing_product_keys = set()
        for year_products in self.all_products.values():
            for product in year_products:
                product_key = (product.get("title", ""), product.get("url", ""))
                existing_product_keys.add(product_key)
        
        print(f"Pre-loaded {len(existing_product_keys)} existing product keys for duplicate detection")
        
        period_products = []
        cursor = resume_cursor
        last_saved_cursor = cursor
        page = 1 if cursor is None else "resuming"
        low_upvotes_streak = 0
        last_product_id = None
        
        # Track duplicate detection metrics
        duplicate_streak = 0
        max_duplicate_streak = 10
        
        while True:
            if max_products and len(period_products) >= max_products:
                print(f"  Reached limit of {max_products} products for {period_name}")
                break
            
            self._respect_rate_limit()
            
            # Convert dates to ISO format
            start_dt = f"{start_date}T00:00:00Z"
            end_dt = f"{end_date}T23:59:59Z"
            variables = {
                "first": 50,
                "postedAfter": start_dt,
                "postedBefore": end_dt
            }
            if cursor:
                variables["after"] = cursor
            
            page_display = "resumed page" if page == "resuming" else f"page {page}"
            print(f"  Fetching {page_display} for {period_name}...")
            
            try:
                resp = requests.post(
                    self.api_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=15
                )
                
                # Handle rate limiting
                if resp.status_code == 429:
                    self.retry_count += 1
                    if self.retry_count <= self.max_retries:
                        backoff_time = min(300, 2 ** self.retry_count)
                        print(f"⚠️ Rate limited (429). Backing off for {backoff_time} seconds...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        print(f"⛔ Maximum retries reached for {period_name}, page {page}")
                        raise RateLimitExceeded(f"Rate limit exceeded for {period_name}")
                
                # Handle other errors
                resp.raise_for_status()
                data = resp.json()
                
                if errors := data.get("errors"):
                    print(f"⚠️ GraphQL errors for {period_name}, page {page}: {errors}")
                    time.sleep(5)
                    if page > 1 or page == "resuming":
                        break
                    else:
                        raise Exception(f"GraphQL errors on first page for {period_name}")
                
                # Get page data
                posts_data = data.get("data", {}).get("posts", {})
                edges = posts_data.get("edges", [])
                page_info = posts_data.get("pageInfo", {})
                
                # Get and save the cursor
                new_cursor = page_info.get("endCursor")
                if new_cursor:
                    last_saved_cursor = new_cursor
                
                # Check if we got any products
                if not edges:
                    print(f"  No products found for {period_name}, {page_display}")
                    break
                
                # Reset retry count on successful response
                if self.retry_count > 0:
                    self.retry_count = max(0, self.retry_count - 1)
                
                # Reset page metrics
                products_on_page = 0
                already_seen_on_page = 0
                low_upvotes_on_page = 0
                new_on_page = 0
                
                # Process products on this page
                for edge in edges:
                    node = edge["node"]
                    products_on_page += 1
                    
                    # Get product ID directly from the API
                    product_id = node.get("id", "")
                    
                    # Skip already seen products (precise tracking)
                    if product_id in seen_products:
                        already_seen_on_page += 1
                        duplicate_streak += 1
                        continue
                    
                    # Check upvotes
                    votes_count = node.get("votesCount", 0)
                    if votes_count < 100:
                        low_upvotes_streak += 1
                        low_upvotes_on_page += 1
                        
                        # Still track this as seen even if we don't save it
                        seen_products.add(product_id)
                        self._update_checkpoint_with_product(checkpoint, period_name, product_id)
                        continue
                    else:
                        low_upvotes_streak = 0
                    
                    # Create simplified product object
                    product = {
                        "id": product_id,  # Add the ID for tracking
                        "title": node["name"],
                        "blurb": node.get("tagline", ""),
                        "description": node.get("description", ""),
                        "url": node.get("website", ""),
                        "profile_picture": node.get("thumbnail", {}).get("url", ""),
                        "source": "producthunt",
                        "period": period_name,
                        "votes": votes_count
                    }
                    
                    # Additional check for duplicate detection using title/URL
                    product_key = (product["title"], product.get("url", ""))
                    
                    # If it's a duplicate by title/URL but not by ID, still track it
                    if product_key in existing_product_keys:
                        duplicate_streak += 1
                        already_seen_on_page += 1
                        
                        # Still mark as seen in checkpoint
                        seen_products.add(product_id)
                        self._update_checkpoint_with_product(checkpoint, period_name, product_id)
                        continue
                    else:
                        # New product - reset duplicate streak
                        duplicate_streak = 0
                        new_on_page += 1
                        
                        # Add to existing keys for future checks
                        existing_product_keys.add(product_key)
                        
                        # Mark as seen in checkpoint
                        seen_products.add(product_id)
                        self._update_checkpoint_with_product(checkpoint, period_name, product_id)
                        
                        # Add to period products and global dict
                        period_products.append(product)
                        
                        # Add to global product list
                        year_key = period_name.split("/")[0]
                        self.all_products.setdefault(year_key, []).append(product)
                        self.items_since_flush += 1
                        
                        # Update last product ID for resumption
                        last_product_id = product_id
                        
                        # Flush periodically
                        if self.global_save_path and self.items_since_flush >= self.flush_threshold:
                            self._append_to_combined_file(flush=True)
                            self._save_checkpoint(checkpoint)  # Save checkpoint with updated product tracking
                            self.items_since_flush = 0
                    
                    # Check max products again after potentially adding
                    if max_products and len(period_products) >= max_products:
                        break
                
                # After processing page, print stats and check stopping conditions
                print(f"  Page results: {new_on_page} new, {already_seen_on_page} already seen, {low_upvotes_on_page} low upvotes (of {products_on_page} total)")
                
                # Stop if this page was mostly already seen
                if products_on_page > 10 and already_seen_on_page >= products_on_page * 0.8:
                    print(f"  Found {already_seen_on_page}/{products_on_page} already seen products on this page. Stopping search.")
                    break
                    
                # Stop if we hit our duplicate streak threshold
                if duplicate_streak >= max_duplicate_streak:
                    print(f"  Found {duplicate_streak} consecutive duplicate products. Stopping search.")
                    break
                
                # Check for low upvotes streak
                if low_upvotes_streak >= 3:
                    print(f"  Found {low_upvotes_streak} consecutive products with <100 upvotes. Stopping search.")
                    break

                # Check low upvotes threshold on current page
                if products_on_page > 0 and low_upvotes_on_page >= products_on_page * 0.8:
                    print(f"  Found {low_upvotes_on_page}/{products_on_page} products with <100 upvotes on this page. Stopping search.")
                    break
                
                # Check if there are more pages
                has_next_page = page_info.get("hasNextPage", False)
                if not has_next_page:
                    print(f"  No more pages for {period_name}")
                    break
                
                # Get cursor for next page
                cursor = page_info.get("endCursor")
                if not cursor:
                    print(f"  No cursor for next page in {period_name}, stopping.")
                    break
                
                # Save checkpoint after each page
                self._save_checkpoint(checkpoint)
                
                # Increment page counter
                if page != "resuming":
                    page += 1
                else:
                    page = 2
                
                # Add a small delay between pages
                time.sleep(2)
                
            except RateLimitExceeded:
                print(f"⛔ Rate limit exceeded for {period_name}, stopping.")
                if save_path and period_products:
                    self._append_to_period_file(period_name, period_products, save_path)
                    self._save_checkpoint(checkpoint)
                    print(f"  Saved partial {len(period_products)} products for {period_name}")
                return period_products, last_saved_cursor
            except Exception as e:
                print(f"⚠️ Error fetching {period_name}, page {page}: {str(e)}")
                if period_products:
                    self._save_checkpoint(checkpoint)
                    break
                raise
        
        # Final checkpoint save
        self._save_checkpoint(checkpoint)
        
        # Save period data if requested
        if save_path and period_products:
            self._append_to_period_file(period_name, period_products, save_path)
            print(f"  Saved {len(period_products)} products for {period_name}")
        
        return period_products, last_saved_cursor

    def _fetch_products_for_month(
        self,
        year: int,
        month: int,
        save_path: Optional[str] = None,
        max_products: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch products for a specific month, with day-by-day fallback if needed.
        Uses cursor-based checkpointing for precise resumption.
        """
        year_str = str(year)
        month_str = f"{month:02d}"
        period_name = f"{year_str}/{month_str}"
        
        # Add a set to track products we've seen across all fetches
        # Use a global tracker for duplication prevention
        if not hasattr(self, '_global_product_keys'):
            self._global_product_keys = set()
        
        # Get start and end dates for this month
        start_date = f"{year_str}-{month_str}-01"
        
        # Calculate end date (last day of month)
        if month == 12:
            next_month_year = year + 1
            next_month = 1
        else:
            next_month_year = year
            next_month = month + 1
            
        next_month_date = datetime(next_month_year, next_month, 1)
        end_date = (next_month_date - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Check if we have a saved cursor for this period
        checkpoint = self._load_checkpoint()
        resume_cursor = checkpoint.get("pagination_cursors", {}).get(period_name)
        if resume_cursor:
            print(f"Found saved cursor for {period_name}, will resume from exact position")
        
        # Try to fetch the whole month
        try:
            print(f"Attempting to fetch {'remainder of' if resume_cursor else 'full'} month {period_name}...")
            month_products, last_cursor = self._fetch_products_for_period(
                start_date=start_date,
                end_date=end_date,
                period_name=period_name,
                save_path=save_path,
                max_products=max_products,
                resume_cursor=resume_cursor
            )
            
            # Save the cursor for future resumption
            if last_cursor:
                checkpoint["pagination_cursors"][period_name] = last_cursor
                self._save_checkpoint(checkpoint)
                print(f"Saved pagination cursor for {period_name} for precise resumption")
            
            # Deduplicate against global tracker
            unique_products = []
            for product in month_products:
                product_key = (product.get('title', ''), product.get('url', ''))
                if product_key not in self._global_product_keys:
                    self._global_product_keys.add(product_key)
                    unique_products.append(product)
            
            return unique_products
            
        except (RateLimitExceeded, Exception) as e:
            # If we hit rate limits or other errors, switch to day-by-day chunking
            print(f"⚠️ Error fetching month {period_name}: {str(e)}")
            print(f"Switching to day-by-day fetching for {period_name}")
            
            # Get days in month
            days_in_month = (next_month_date - datetime(year, month, 1)).days
            
            # Create daily checkpoints directory
            daily_checkpoint_dir = os.path.join(self.checkpoint_dir, f"{year_str}_{month_str}_daily")
            os.makedirs(daily_checkpoint_dir, exist_ok=True)
            
            # Load daily checkpoint if exists
            daily_checkpoint_file = os.path.join(daily_checkpoint_dir, "daily_progress.json")
            if os.path.exists(daily_checkpoint_file):
                try:
                    with open(daily_checkpoint_file, "r") as f:
                        daily_checkpoint = json.load(f)
                except (json.JSONDecodeError, IOError):
                    daily_checkpoint = {"completed_days": [], "pagination_cursors": {}}
            else:
                daily_checkpoint = {"completed_days": [], "pagination_cursors": {}}
            
            # Fetch day by day
            month_products = []
            for day in range(1, days_in_month + 1):
                # Skip if already completed
                if day in daily_checkpoint["completed_days"]:
                    print(f"  Skipping already completed day {year_str}-{month_str}-{day:02d}")
                    # Load products from saved file
                    day_filepath = os.path.join(daily_checkpoint_dir, f"day_{day:02d}.json")
                    if os.path.exists(day_filepath):
                        try:
                            with open(day_filepath, "r") as f:
                                day_products = json.load(f)
                                month_products.extend(day_products)
                                print(f"  Loaded {len(day_products)} products from {day_filepath}")
                        except (json.JSONDecodeError, IOError) as e:
                            print(f"  Error loading day products: {e}")
                    continue
                
                # Current day
                day_date = f"{year_str}-{month_str}-{day:02d}"
                next_day_date = datetime(year, month, day) + timedelta(days=1)
                next_day = next_day_date.strftime("%Y-%m-%d")
                day_period_name = f"{period_name}/{day:02d}"
                
                # Check for cursor to resume this specific day
                day_cursor = daily_checkpoint.get("pagination_cursors", {}).get(day_period_name)
                
                try:
                    print(f"Fetching products for {day_date}" + 
                        (" resuming from saved position" if day_cursor else ""))
                        
                    day_products, last_cursor = self._fetch_products_for_period(
                        start_date=day_date,
                        end_date=next_day,
                        period_name=day_period_name,
                        save_path=daily_checkpoint_dir,
                        max_products=max_products,
                        resume_cursor=day_cursor
                    )
                    
                    # Save cursor for future resumption
                    if last_cursor:
                        if "pagination_cursors" not in daily_checkpoint:
                            daily_checkpoint["pagination_cursors"] = {}
                        daily_checkpoint["pagination_cursors"][day_period_name] = last_cursor
                    
                    # Save this day's products
                    day_filepath = os.path.join(daily_checkpoint_dir, f"day_{day:02d}.json")
                    with open(day_filepath, "w") as f:
                        json.dump(day_products, f, indent=2)
                    
                    # Update daily checkpoint
                    daily_checkpoint["completed_days"].append(day)
                    with open(daily_checkpoint_file, "w") as f:
                        json.dump(daily_checkpoint, f, indent=2)
                    
                    # Add to month products
                    month_products.extend(day_products)
                    
                    # Add significant delay between days
                    if day < days_in_month:
                        print(f"  Waiting between days to respect rate limits...")
                        time.sleep(30)  # 30 seconds between days
                        
                except Exception as e:
                    print(f"⚠️ Error fetching day {day_date}: {str(e)}")
                    # Save monthly progress so far
                    if save_path and month_products:
                        month_filepath = os.path.join(save_path, f"{period_name.replace('/', '_')}_partial.json")
                        with open(month_filepath, "w", encoding="utf-8") as f:
                            json.dump(month_products, f, indent=2)
                        print(f"  Saved partial {len(month_products)} products for {period_name}")
                    
                    # If fatal error, re-raise
                    if isinstance(e, KeyboardInterrupt):
                        raise
                    
                    # Otherwise add delay and continue with next day
                    time.sleep(60)  # 1 minute delay after error
            
            # Initialize global deduplication tracker if it doesn't exist
            if not hasattr(self, '_global_product_keys'):
                self._global_product_keys = set()

            # Deduplicate against global tracker
            unique_products = []
            for product in month_products:
                product_key = (product.get('title', ''), product.get('url', ''))
                if product_key not in self._global_product_keys:
                    self._global_product_keys.add(product_key)
                    unique_products.append(product)

            # Save unique products if requested
            if save_path and unique_products:
                month_filepath = os.path.join(save_path, f"{period_name.replace('/', '_')}.json")
                with open(month_filepath, "w", encoding="utf-8") as f:
                    json.dump(unique_products, f, indent=2)
                print(f"  Saved {len(unique_products)} unique products for {period_name}")

            return unique_products
        

    def _append_to_period_file(self, period_name: str, products: List[Dict[str, Any]], save_path: str) -> None:
        """Append products to a period-specific file without overwriting existing content."""
        period_filepath = os.path.join(save_path, f"{period_name.replace('/', '_')}.json")
        
        # Check if file exists and load existing data
        existing_products = []
        if os.path.exists(period_filepath):
            try:
                with open(period_filepath, "r", encoding="utf-8") as f:
                    existing_products = json.load(f)
                    print(f"  Loaded {len(existing_products)} existing products from {period_filepath}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"  Error loading existing products from {period_filepath}: {e}")
                # If we can't load it, create a backup
                if os.path.getsize(period_filepath) > 0:
                    backup_path = f"{period_filepath}.bak"
                    try:
                        import shutil
                        shutil.copy2(period_filepath, backup_path)
                        print(f"  Created backup of corrupted file at {backup_path}")
                    except Exception as backup_error:
                        print(f"  Failed to create backup: {backup_error}")
        
        # Merge new products with existing ones
        # Create a set of existing product identifiers to avoid duplicates
        existing_ids = set()
        for product in existing_products:
            # Create a unique identifier based on title and URL
            product_id = (product.get("title", ""), product.get("url", ""))
            existing_ids.add(product_id)
        
        # Only add products that don't already exist
        new_added = 0
        for product in products:
            product_id = (product.get("title", ""), product.get("url", ""))
            if product_id not in existing_ids:
                existing_products.append(product)
                existing_ids.add(product_id)
                new_added += 1
        
        # Write the merged list back to the file
        with open(period_filepath, "w", encoding="utf-8") as f:
            json.dump(existing_products, f, indent=2)
        
        print(f"  Added {new_added} new products to {period_filepath} (total: {len(existing_products)})")

    def _append_to_combined_file(self, flush: bool = False) -> None:
        """Append products to the combined file without overwriting existing content."""
        if not self.global_save_path:
            return
        
        combined_file = os.path.join(self.global_save_path, "producthunt_all_years.json")
        
        # Check if the file exists and load existing data
        existing_data = {}
        if os.path.exists(combined_file):
            try:
                with open(combined_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    if flush:
                        print(f"⚡ Loaded existing data from {combined_file} for update")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading existing combined data: {e}")
                # If we can't load it, create a backup
                if os.path.getsize(combined_file) > 0:
                    backup_path = f"{combined_file}.bak"
                    try:
                        import shutil
                        shutil.copy2(combined_file, backup_path)
                        print(f"Created backup of corrupted file at {backup_path}")
                    except Exception as backup_error:
                        print(f"Failed to create backup: {backup_error}")
        
        # Merge new products with existing ones
        products_added = 0
        for year, products in self.all_products.items():
            # Get existing products for this year
            existing_year_products = existing_data.get(year, [])
            
            # Create a set of existing product identifiers
            existing_ids = set()
            for product in existing_year_products:
                product_id = (product.get("title", ""), product.get("url", ""))
                existing_ids.add(product_id)
            
            # Add only new products
            for product in products:
                product_id = (product.get("title", ""), product.get("url", ""))
                if product_id not in existing_ids:
                    existing_year_products.append(product)
                    existing_ids.add(product_id)
                    products_added += 1
            
            # Update the existing data
            existing_data[year] = existing_year_products
        
        # Write the merged data back to the file
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2)
        
        if flush:
            print(f"⚡ Flushed {products_added} new items to {combined_file}")


    def get_products_by_year_range(
        self,
        start_year: int = 2020,
        end_year: Optional[int] = None,
        save_path: Optional[str] = None,
        max_per_month: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch products from Product Hunt for a range of years.
        Uses cursor-based checkpointing for precise resumption.
        """
        from datetime import datetime

        # Default to current year if not specified
        if end_year is None:
            end_year = datetime.now().year

        # Prepare output directory
        if save_path:
            os.makedirs(save_path, exist_ok=True)

        # ─── set up global state for mid-run flushing ───────────────────
        self.global_save_path = save_path
        self.all_products = {}
        self.items_since_flush = 0
        
        # Before starting, load existing data to avoid duplicates
        if save_path:
            combined_file = os.path.join(save_path, "producthunt_all_years.json")
            if os.path.exists(combined_file):
                try:
                    with open(combined_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                        print(f"Loaded existing data from {combined_file}")
                        # Pre-populate all_products with existing data to enable deduplication
                        for year, products in existing_data.items():
                            self.all_products[year] = products.copy()
                        print(f"Pre-loaded {sum(len(products) for products in self.all_products.values())} products from {len(self.all_products)} years")
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading existing data: {e}")

        # Load checkpoint state
        checkpoint = self._load_checkpoint()
        last_year = checkpoint["last_completed"].get("year")
        last_month = checkpoint["last_completed"].get("month")

        today = datetime.now()

        # Iterate through each year
        for year in range(start_year, end_year + 1):
            year_str = str(year)
            print(f"\n==== Fetching products for {year_str} ====")

            # Determine which month to start at (resume support)
            start_month = 1
            if last_year is not None and year == last_year:
                start_month = last_month + 1

            # Iterate through each month
            for month in range(start_month, 13):
                # Skip future months
                if year == today.year and month > today.month:
                    print(f"Skipping future month {year}-{month:02d}")
                    break

                month_key = f"{year}_{month:02d}"
                # Skip already checkpointed months
                if month_key in checkpoint["completed_periods"]:
                    print(f"Skipping already completed month {year}-{month:02d}")
                    continue

                try:
                    print(f"\n--- Fetching products for {year_str}-{month:02d} ---")
                    month_products = self._fetch_products_for_month(
                        year=year,
                        month=month,
                        save_path=save_path,            # Enable per-month file saving with append
                        max_products=max_per_month
                    )
                    
                    # Update checkpoint
                    checkpoint["last_completed"] = {"year": year, "month": month}
                    checkpoint["completed_periods"][month_key] = {
                        "products": len(month_products),
                        "timestamp": datetime.now().isoformat()
                    }
                    checkpoint["stats"]["total_products"] += len(month_products)
                    self._save_checkpoint(checkpoint)

                    # Append to combined data after each month completes
                    if save_path:
                        self._append_to_combined_file(flush=True)
                        print(f"Combined data updated with latest products from {year}-{month:02d}")

                    # Wait between months to respect rate limits
                    if month < 12:
                        print(f"\nWaiting between months to respect rate limits...")
                        time.sleep(15)

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"⚠️ Error processing month {year}-{month:02d}: {str(e)}")
                    time.sleep(20)  # pause then continue

            # Wait between years
            if year < end_year:
                print(f"\nWaiting before fetching next year...")
                time.sleep(20)

        # Once all years are done, ensure all data is saved
        if save_path:
            self._append_to_combined_file(flush=True)
            
            # Load the final combined data to return
            combined_file = os.path.join(save_path, "producthunt_all_years.json")
            with open(combined_file, "r", encoding="utf-8") as f:
                all_products = json.load(f)
            
            total_count = sum(len(v) for v in all_products.values())
            print(f"✅ All years saved to {combined_file} ({total_count} total items)")
            return all_products
        else:
            # If no save path, return the in-memory data
            return self.all_products


    def get_latest_products(self, limit: int = 100, save_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch the latest products from Product Hunt.
        This is a convenience method that's faster than retrieving by year when you just want recent products.
        
        Args:
            limit: Maximum number of products to return
            save_path: Optional path to save results
            
        Returns:
            List of product dictionaries
        """
        print(f"Fetching latest {limit} products...")
        
        # GraphQL query for latest products
        query = """
        query GetLatestProducts($first: Int!, $after: String) {
        posts(first: $first, after: $after, order: NEWEST) {
            pageInfo {
            hasNextPage
            endCursor
            }
            edges {
            node {
                name
                tagline
                description
                website
                thumbnail {
                url
                }
            }
            }
        }
        }
        """
        
        result = []
        cursor = None
        page = 1
        
        while len(result) < limit:
            self._respect_rate_limit()
            
            variables = {
                "first": min(50, limit - len(result)),
            }
            if cursor:
                variables["after"] = cursor
            
            print(f"  Fetching page {page}...")
            
            try:
                resp = requests.post(
                    self.api_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=15
                )
                
                # Handle rate limiting
                if resp.status_code == 429:
                    self.retry_count += 1
                    if self.retry_count <= self.max_retries:
                        backoff_time = min(300, 2 ** self.retry_count)
                        print(f"⚠️ Rate limited (429). Backing off for {backoff_time} seconds...")
                        time.sleep(backoff_time)
                        continue  # Retry the request
                    else:
                        print(f"⛔ Maximum retries reached for latest products, page {page}")
                        break
                
                # Handle other errors
                resp.raise_for_status()
                data = resp.json()
                
                if errors := data.get("errors"):
                    print(f"⚠️ GraphQL errors for latest products, page {page}: {errors}")
                    break
                
                posts_data = data.get("data", {}).get("posts", {})
                edges = posts_data.get("edges", [])
                page_info = posts_data.get("pageInfo", {})
                
                # Check if we got any products
                if not edges:
                    print(f"  No products found for latest products, page {page}")
                    break
                
                # Reset retry count on successful response
                if self.retry_count > 0:
                    self.retry_count = max(0, self.retry_count - 1)
                
                # Process products on this page
                for edge in edges:
                    node = edge["node"]
                    
                    # Create product with simplified field names
                    product = {
                        "title": node["name"],
                        "blurb": node.get("tagline", ""),
                        "description": node.get("description", ""),
                        "url": node.get("website", ""),
                        "profile_picture": node.get("thumbnail", {}).get("url", ""),
                        "source": "producthunt"
                    }
                    
                    result.append(product)
                
                print(f"  Fetched page {page}, total products so far: {len(result)}")
                
                # Check if we can get more
                if not page_info.get("hasNextPage", False) or not page_info.get("endCursor"):
                    break
                    
                cursor = page_info.get("endCursor")
                page += 1
                
                # Add a delay between pages
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Error fetching latest products, page {page}: {str(e)}")
                break
        
        # Save if requested
        if save_path and result:
            os.makedirs(save_path, exist_ok=True)
            filepath = os.path.join(save_path, "producthunt_latest.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"Saved {len(result)} latest products")
        
        return result


if __name__ == "__main__":
    """Script to fetch all Product Hunt products from 2015 to current date."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Product Hunt Scraper with chunking")
    parser.add_argument("--start-year", type=int, default=2020, help="Start year (default: 2020)")
    parser.add_argument("--end-year", type=int, default=None, help="End year (default: current year)")
    parser.add_argument("--max-per-month", type=int, default=None, help="Max products per month (for testing)")
    parser.add_argument("--save-path", type=str, default="data", help="Path to save data (default: 'data')")
    parser.add_argument("--latest", type=int, default=None, help="Fetch only latest N products instead of by year range")
    parser.add_argument("--delay", type=float, default=2.0, help="Base delay between requests (default: 2.0)")
    args = parser.parse_args()
    
    print("====================================")
    print("PRODUCT HUNT COMPLETE DATA SCRAPER")
    print("====================================")
    print(f"Using chunked approach with monthly and daily fallback")
    
    # Create scraper instance with specified base delay
    scraper = ProductHuntScraper(base_delay=args.delay)
    
    try:
        if args.latest:
            # Just fetch latest products if --latest is specified
            print(f"Fetching latest {args.latest} products...")
            products = scraper.get_latest_products(
                limit=args.latest,
                save_path=args.save_path
            )
            print(f"Fetched {len(products)} latest products")
        else:
            # Otherwise fetch by year range
            print(f"Fetching products from {args.start_year} to {args.end_year or 'now'}")
            print(f"Data will be saved to the '{args.save_path}' directory.")
            print(f"Using chunks with checkpointing for reliable scraping.")
            print(f"This process may take a long time to complete.\n")
            
            if args.max_per_month:
                print(f"⚠️ Testing mode: Limiting to {args.max_per_month} products per month")
            
            # Scrape all products from start_year to end_year
            all_products = scraper.get_products_by_year_range(
                start_year=args.start_year,
                end_year=args.end_year,
                save_path=args.save_path,
                max_per_month=args.max_per_month
            )
            
            # Print summary of results
            print("\n====================================")
            print("SCRAPING COMPLETE")
            print("====================================")
            total_count = 0
            print("Summary of scraped data:")
            for year, products in all_products.items():
                product_count = len(products)
                total_count += product_count
                print(f"Year {year}: {product_count} products")
                
            print(f"\nTotal products scraped: {total_count}")
            print(f"Data saved to: {args.save_path}/producthunt_all_years.json")
    
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user. Progress has been saved.")
        print("You can resume later by running the script again.\n")
    
    except Exception as e:
        import traceback
        print(f"\n\nError during scraping: {str(e)}")
        traceback.print_exc()
        print("\nProgress has been saved. You can resume later by running the script again.\n")
    
    print("====================================")