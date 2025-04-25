import os
import time
import json
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from datetime import datetime

# Load environment variables
load_dotenv()

# Use a constant User-Agent for both token and GraphQL requests
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/99.0.4844.74 Safari/537.36"
)

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
    A scraper for Product Hunt leaderboard data using OAuth2 client credentials.
    """
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None
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
        self.request_delay = 1.0  # seconds
        self.last_request_time = 0.0

    def _respect_rate_limit(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()

    def get_popular_products(
        self,
        order: str = "VOTES",
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Fetch a single page of popular Product Hunt products.
        
        Args:
            order: Ordering method ("VOTES", "NEWEST", etc.)
            cursor: Pagination cursor for next page
            limit: Maximum number of products to return
            
        Returns:
            Dict with 'products', 'has_next_page', 'end_cursor'
        """
        self._respect_rate_limit()
        
        query = """
        query GetProducts($first: Int!, $after: String, $order: PostsOrder) {
        posts(first: $first, after: $after, order: $order) {
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
        
        variables: Dict[str, Any] = {
            "first": limit,
            "order": order
        }
        
        if cursor:
            variables["after"] = cursor
        
        resp = requests.post(
            self.api_url,
            json={"query": query, "variables": variables},
            headers=self.headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        if errors := data.get("errors"):
            print(f"GraphQL errors: {errors}")
            return {"products": [], "has_next_page": False, "end_cursor": None}
        
        posts = data["data"]["posts"]
        page_info = posts["pageInfo"]
        edges = posts["edges"]
        
        products: List[Dict[str, Any]] = []
        for edge in edges:
            node = edge["node"]
            products.append({
                "title": node["name"],
                "blurb": node.get("tagline", ""),
                "description": node.get("description", ""),
                "url": node.get("website", ""),
                "profile_picture": node.get("thumbnail", {}).get("url", ""),
                "source": "producthunt"
            })
        
        return {
            "products": products,
            "has_next_page": page_info.get("hasNextPage", False),
            "end_cursor": page_info.get("endCursor")
        }

    def get_products_by_year_range(
        self,
        start_year: int = 2021,
        end_year: Optional[int] = None,
        save_path: Optional[str] = None,
        max_per_year: Optional[int] = None  # Optional limit for testing
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch products from Product Hunt for a range of years.
        Optionally save JSON per year in save_path.
        
        Args:
            start_year: First year to fetch (inclusive)
            end_year: Last year to fetch (inclusive), defaults to current year
            save_path: Directory to save results JSON
            max_per_year: Optional limit of products per year (for testing)
            
        Returns:
            Dictionary with years as keys and lists of products as values
        """
        # If end_year not provided, use current year
        if end_year is None:
            end_year = datetime.now().year
        
        all_products: Dict[str, List[Dict[str, Any]]] = {}
        
        # Loop through each year
        for year in range(start_year, end_year + 1):
            year_str = str(year)
            print(f"Fetching products for {year_str}...")
            
            # Create date ranges for this year
            start_date = f"{year_str}-01-01"
            # For current year, use current date as end_date
            if year == datetime.now().year:
                end_date = datetime.now().strftime("%Y-%m-%d")
            else:
                end_date = f"{year_str}-12-31"
            
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
            
            # Initialize for this year
            year_products: List[Dict[str, Any]] = []
            cursor = None
            page = 1
            
            # Paginate through all results for this year
            while True:
                # Check if we've hit the max per year limit (if specified)
                if max_per_year and len(year_products) >= max_per_year:
                    print(f"  Reached limit of {max_per_year} products for {year_str}")
                    break
                
                self._respect_rate_limit()
                
                variables = {
                    "first": 50,  # Maximum allowed per page
                    "postedAfter": start_date,
                    "postedBefore": end_date
                }
                if cursor:
                    variables["after"] = cursor
                
                print(f"  Fetching page {page} for {year_str}...")
                
                try:
                    resp = requests.post(
                        self.api_url,
                        json={"query": query, "variables": variables},
                        headers=self.headers,
                        timeout=15
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if errors := data.get("errors"):
                        print(f"GraphQL errors for {year_str}, page {page}: {errors}")
                        break
                    
                    posts_data = data.get("data", {}).get("posts", {})
                    edges = posts_data.get("edges", [])
                    page_info = posts_data.get("pageInfo", {})
                    
                    # Check if we got any products
                    if not edges:
                        print(f"  No products found for {year_str}, page {page}")
                        break
                    
                    # Process products on this page with simplified fields
                    for edge in edges:
                        node = edge["node"]
                        
                        # Create product with simplified field names
                        product = {
                            "title": node["name"],
                            "blurb": node.get("tagline", ""),
                            "description": node.get("description", ""),
                            "url": node.get("website", ""),
                            "profile_picture": node.get("thumbnail", {}).get("url", ""),
                            "source": "producthunt",
                            "year": year_str
                        }
                        
                        year_products.append(product)
                        
                        # Check if we've hit the max per year limit
                        if max_per_year and len(year_products) >= max_per_year:
                            break
                    
                    # Check if we need to get more pages
                    has_next_page = page_info.get("hasNextPage", False)
                    if not has_next_page:
                        print(f"  No more pages for {year_str}")
                        break
                    
                    # Get cursor for next page
                    cursor = page_info.get("endCursor")
                    if not cursor:
                        print(f"  No cursor for next page in {year_str}, stopping.")
                        break
                    
                    # Increment page counter
                    page += 1
                    
                    # Add a delay between pages to be nice to the API
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error fetching {year_str}, page {page}: {str(e)}")
                    break
            
            # Save year data if requested
            if save_path and year_products:
                os.makedirs(save_path, exist_ok=True)
                filepath = os.path.join(save_path, f"producthunt_{year_str}.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(year_products, f, indent=2)
                print(f"  Saved {len(year_products)} products for {year_str}")
            
            # Add to overall results
            all_products[year_str] = year_products
            print(f"  Total products for {year_str}: {len(year_products)}")
            
            # Wait between years to be nice to the API
            if year < end_year:
                print(f"Waiting before fetching next year...")
                time.sleep(5)
        
        # Save combined data if requested
        if save_path:
            all_filepath = os.path.join(save_path, "producthunt_all_years.json")
            with open(all_filepath, "w", encoding="utf-8") as f:
                json.dump(all_products, f, indent=2)
            
            # Also create a flat list for easier processing by the relevancy matcher
            flat_products = []
            for year_list in all_products.values():
                flat_products.extend(year_list)
            
            flat_filepath = os.path.join(save_path, "producthunt_flat.json")
            with open(flat_filepath, "w", encoding="utf-8") as f:
                json.dump(flat_products, f, indent=2)
            
            # Get total count
            total_count = sum(len(products) for products in all_products.values())
            print(f"Total products: {total_count}")
        
        return all_productsSaved {len(year_products)} products for {year_str}")
            
            # Add to overall results
            all_products[year_str] = year_products
            print(f"  Total products for {year_str}: {len(year_products)}")
            
            # Wait between years to be nice to the API
            if year < end_year:
                print(f"Waiting before fetching next year...")
                time.sleep(5)
        
        # Save combined data if requested
        if save_path:
            all_filepath = os.path.join(save_path, "producthunt_all_years.json")
            with open(all_filepath, "w", encoding="utf-8") as f:
                json.dump(all_products, f, indent=2)
            
            # Also create a flat list for easier processing by the relevancy matcher
            flat_products = []
            for year_list in all_products.values():
                flat_products.extend(year_list)
            
            flat_filepath = os.path.join(save_path, "producthunt_flat.json")
            with open(flat_filepath, "w", encoding="utf-8") as f:
                json.dump(flat_products, f, indent=2)
            
            # Get total count
            total_count = sum(len(products) for products in all_products.values())
            print(f"Total products: {total_count}")
        
        return all_products
    
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
        
        result = []
        cursor = None
        page = 1
        
        while len(result) < limit:
            self._respect_rate_limit()
            
            page_result = self.get_popular_products(
                order="NEWEST",
                cursor=cursor,
                limit=min(50, limit - len(result))
            )
            
            products = page_result["products"]
            result.extend(products)
            
            print(f"  Fetched page {page}, total products so far: {len(result)}")
            
            # Check if we can get more
            if not page_result["has_next_page"] or not page_result["end_cursor"]:
                break
                
            cursor = page_result["end_cursor"]
            page += 1
            
            # Add a delay between pages
            time.sleep(2)
        
        # Add source identifier if not already present
        for product in result:
            if "source" not in product:
                product["source"] = "producthunt"
        
        # Save if requested
        if save_path:
            os.makedirs(save_path, exist_ok=True)
            filepath = os.path.join(save_path, "producthunt_latest.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"Saved {len(result)} latest products")
        
        return result

# if __name__ == "__main__":
#     # Create scraper instance
#     scraper = ProductHuntScraper()
#     
#     # Scrape all products from 2021 to current year
#     all_products = scraper.get_products_by_year_range(
#         start_year=2021,
#         end_year=None,  # Use current year
#         save_path="data"
#     )
#     
#     # Print summary of results
#     print("\nSummary of scraped data:")
#     for year, products in all_products.items():
#         print(f"Year {year}: {len(products)} products")

if __name__ == "__main__":
    """Test function to get products from yesterday with simplified fields"""
    from datetime import datetime, timedelta
    
    # Create scraper instance
    scraper = ProductHuntScraper()
    
    # Get yesterday's date
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    
    print(f"Fetching Product Hunt products launched on {yesterday_str}...")
    
    # GraphQL query with date filtering for a specific day
    query = """
    query ProductsByExactDate($first: Int!, $after: String, $postedAfter: DateTime!, $postedBefore: DateTime!) {
      posts(
        first: $first,
        after: $after,
        postedAfter: $postedAfter,
        postedBefore: $postedBefore,
        order: NEWEST
      ) {
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
    
    # Initialize product list
    yesterday_products = []
    cursor = None
    page = 1
    
    # Paginate through all results for yesterday
    while True:
        scraper._respect_rate_limit()
        
        # End time is start of today (midnight)
        today_midnight = datetime(today.year, today.month, today.day)
        # Start time is start of yesterday (midnight)
        yesterday_midnight = datetime(yesterday.year, yesterday.month, yesterday.day)
        
        variables = {
            "first": 50,  # Maximum allowed per page
            "postedAfter": yesterday_midnight.strftime("%Y-%m-%d"),
            "postedBefore": today_midnight.strftime("%Y-%m-%d")
        }
        if cursor:
            variables["after"] = cursor
        
        print(f"  Fetching page {page}...")
        
        try:
            resp = requests.post(
                scraper.api_url,
                json={"query": query, "variables": variables},
                headers=scraper.headers,
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            
            if errors := data.get("errors"):
                print(f"GraphQL errors for yesterday, page {page}: {errors}")
                break
            
            posts_data = data.get("data", {}).get("posts", {})
            edges = posts_data.get("edges", [])
            page_info = posts_data.get("pageInfo", {})
            
            # Check if we got any products
            if not edges:
                print(f"  No products found for yesterday, page {page}")
                break
            
            # Process products on this page with simplified fields
            for edge in edges:
                node = edge["node"]
                
                # Create product with your specified field names
                product = {
                    "title": node.get("name", ""),
                    "blurb": node.get("tagline", ""),
                    "description": node.get("description", ""),
                    "url": node.get("website", ""),
                    "profile_picture": node.get("thumbnail", {}).get("url", ""),
                    "source": "producthunt"
                }
                
                yesterday_products.append(product)
            
            print(f"  Found {len(edges)} products on page {page}")
            
            # Check if we need to get more pages
            has_next_page = page_info.get("hasNextPage", False)
            if not has_next_page:
                print(f"  No more pages for yesterday")
                break
            
            # Get cursor for next page
            cursor = page_info.get("endCursor")
            if not cursor:
                print(f"  No cursor for next page, stopping.")
                break
            
            # Increment page counter
            page += 1
            
            # Add a delay between pages to be nice to the API
            time.sleep(2)
            
        except Exception as e:
            print(f"Error fetching yesterday's products, page {page}: {str(e)}")
            break
    
    # Save the results
    if yesterday_products:
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", f"producthunt_yesterday_{yesterday_str}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(yesterday_products, f, indent=2)
        print(f"\nSuccessfully saved {len(yesterday_products)} products from yesterday to {filepath}")
    else:
        print("\nNo products found from yesterday to save.")