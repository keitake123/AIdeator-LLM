import os
import time
import json
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

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
                id
                name
                tagline
                description
                url
                votesCount
                commentsCount
                website
                createdAt
                thumbnail {
                url
                }
                topics {
                edges {
                    node {
                    name
                    }
                }
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
            topics = [t["node"]["name"] for t in node["topics"]["edges"]]
            products.append({
                "id": node["id"],
                "title": node["name"],
                "description": node.get("tagline", ""),
                "full_description": node.get("description", ""),
                "url": node.get("url") or node.get("website", ""),
                "thumbnail": node.get("thumbnail", {}).get("url", ""),
                "upvotes": node.get("votesCount", 0),
                "comments": node.get("commentsCount", 0),
                "created_at": node.get("createdAt", ""),
                "topics": topics
            })
        
        return {
            "products": products,
            "has_next_page": page_info.get("hasNextPage", False),
            "end_cursor": page_info.get("endCursor")
        }

    def get_products_by_year_range(
        self,
        start_year: int = 2020,
        end_year: int = 2025,
        save_path: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch products from Product Hunt for a range of years.
        Optionally save JSON per year in save_path.
        
        Args:
            start_year: First year to fetch (inclusive)
            end_year: Last year to fetch (inclusive)
            save_path: Directory to save results JSON
            
        Returns:
            Dictionary with years as keys and lists of products as values
        """
        all_products: Dict[str, List[Dict[str, Any]]] = {}
        
        # Loop through each year
        for year in range(start_year, end_year + 1):
            year_str = str(year)
            print(f"Fetching products for {year_str}...")
            
            # Create date ranges for this year
            start_date = f"{year_str}-01-01"
            end_date = f"{year_str}-12-31"
            
            # GraphQL query with date filtering
            query = """
            query ProductsByDate($first: Int!, $after: String, $postedAfter: DateTime!, $postedBefore: DateTime!) {
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
                    id
                    name
                    tagline
                    description
                    url
                    votesCount
                    commentsCount
                    website
                    createdAt
                    thumbnail {
                    url
                    }
                    topics {
                    edges {
                        node {
                        name
                        }
                    }
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
                    
                    # Process products on this page
                    for edge in edges:
                        node = edge["node"]
                        topics = [t["node"]["name"] for t in node["topics"]["edges"]]
                        
                        year_products.append({
                            "id": node["id"],
                            "title": node["name"],
                            "description": node.get("tagline", ""),
                            "full_description": node.get("description", ""),
                            "url": node.get("url") or node.get("website", ""),
                            "thumbnail": node.get("thumbnail", {}).get("url", ""),
                            "upvotes": node.get("votesCount", 0),
                            "comments": node.get("commentsCount", 0),
                            "created_at": node.get("createdAt", ""),
                            "topics": topics,
                            "year": year_str
                        })
                    
                    # Check if we need to get more pages
                    has_next_page = page_info.get("hasNextPage", False)
                    if not has_next_page:
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
            
            # Wait between years to be nice to the API
            if year < end_year:
                print(f"Waiting before fetching next year...")
                time.sleep(5)
        
        # Save combined data if requested
        if save_path:
            all_filepath = os.path.join(save_path, "producthunt_all_years.json")
            with open(all_filepath, "w", encoding="utf-8") as f:
                json.dump(all_products, f, indent=2)
            
            # Get total count
            total_count = sum(len(products) for products in all_products.values())
            print(f"Total products: {total_count}")
        
        return all_products
    

if __name__ == "__main__":
    # Create scraper instance
    scraper = ProductHuntScraper()
    
    # Test the year-based function with a limit of 3 products for the year 2023
    print("Running test for year 2023 with a limit of 3 products...")
    
    # Define a simplified test function that only gets a few products
    def test_get_products_for_year(year=2023, limit=3):
        """Test function to get a small sample of products for a specific year"""
        # Create date ranges for this year
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        # GraphQL query with date filtering
        query = """
        query ProductsByDate($first: Int!, $postedAfter: DateTime!, $postedBefore: DateTime!) {
          posts(
            first: $first,
            postedAfter: $postedAfter,
            postedBefore: $postedBefore,
            order: VOTES
          ) {
            edges {
              node {
                id
                name
                tagline
                description
                url
                votesCount
                commentsCount
                website
                createdAt
                thumbnail {
                  url
                }
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "first": limit,
            "postedAfter": start_date,
            "postedBefore": end_date
        }
        
        resp = requests.post(
            scraper.api_url,
            json={"query": query, "variables": variables},
            headers=scraper.headers,
            timeout=15
        )
        
        data = resp.json()
        
        if errors := data.get("errors"):
            print(f"GraphQL errors: {errors}")
            return {"products": []}
        
        posts_data = data.get("data", {}).get("posts", {})
        edges = posts_data.get("edges", [])
        
        # Process products
        products = []
        for edge in edges:
            node = edge["node"]
            topics = [t["node"]["name"] for t in node["topics"]["edges"]]
            
            products.append({
                "id": node["id"],
                "title": node["name"],
                "description": node.get("tagline", ""),
                "full_description": node.get("description", ""),
                "url": node.get("url") or node.get("website", ""),
                "thumbnail": node.get("thumbnail", {}).get("url", ""),
                "upvotes": node.get("votesCount", 0),
                "comments": node.get("commentsCount", 0),
                "created_at": node.get("createdAt", ""),
                "topics": topics,
                "year": str(year)
            })
        
        return {"products": products}
    
    # Run the test function
    test_result = test_get_products_for_year(year=2023, limit=3)
    
    # Save the test results
    os.makedirs("test_data", exist_ok=True)
    with open("test_data/test_year_2023_top3.json", "w", encoding="utf-8") as f:
        json.dump(test_result, f, indent=2)
    
    print(f"✅ Test data saved to test_data/test_year_2023_top3.json")
    print(f"Found {len(test_result['products'])} products for 2023")
    
    # Once this works, you can uncomment this to run the full scraper:
    """
    # Scrape all products from 2020-2025
    all_products = scraper.get_products_by_year_range(
        start_year=2020,
        end_year=2025,
        save_path="data"
    )
    
    # Print summary of results
    print("\nSummary of scraped data:")
    for year, products in all_products.items():
        print(f"Year {year}: {len(products)} products")
    """

# if __name__ == "__main__":
#     # Uncomment for a quick test
#     """
#     scraper = ProductHuntScraper()
#     sample = scraper.get_popular_products(limit=3)
#     os.makedirs("test_data", exist_ok=True)
#     with open("test_data/test_results.json", "w", encoding="utf-8") as f:
#         json.dump(sample, f, indent=2)
#     print("✅ Test data saved to test_data/test_results.json")
#     """
    
#     # Scrape all products from 2020-2025
#     scraper = ProductHuntScraper()
#     all_products = scraper.get_products_by_year_range(
#         start_year=2020,
#         end_year=2025,
#         save_path="data"
#     )
    
#     # Print summary of results
#     print("\nSummary of scraped data:")
#     for year, products in all_products.items():
#         print(f"Year {year}: {len(products)} products")
