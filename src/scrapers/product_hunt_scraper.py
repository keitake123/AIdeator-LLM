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

    def get_products_by_timeframe(
    self,
    days_range: int = 365,  # Default to roughly a year
    order: str = "VOTES",
    save_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch products from Product Hunt for a specific time range.
        Optionally save JSON in save_path.
        
        Args:
            days_range: Number of days to look back
            order: How to order the results (VOTES, NEWEST, etc)
            save_path: Directory to save results JSON
            
        Returns:
            List of product dictionaries
        """
        print(f"Fetching products ordered by {order}...")
        all_products: List[Dict[str, Any]] = []
        
        result = self.get_popular_products(order=order)
        all_products.extend(result["products"])
        
        page = 2
        while result["has_next_page"]:
            print(f"  Page {page}...")
            time.sleep(2)  # Be nice to the API
            result = self.get_popular_products(
                order=order,
                cursor=result["end_cursor"]
            )
            all_products.extend(result["products"])
            page += 1
            
            # Optional: stop after collecting a certain number of products
            if len(all_products) >= 1000:
                print(f"Reached 1000 products, stopping pagination.")
                break
        
        if save_path:
            os.makedirs(save_path, exist_ok=True)
            filename = f"producthunt_{order.lower()}.json"
            filepath = os.path.join(save_path, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(all_products, f, indent=2)
            print(f"Saved {len(all_products)} products to {filepath}")
        
        return all_products

if __name__ == "__main__":
    # Test run: fetch 3 popular products
    scraper = ProductHuntScraper()
    sample = scraper.get_popular_products(limit=3)
    os.makedirs("test_data", exist_ok=True)
    with open("test_data/test_results.json", "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2)
    print("✅ Test data saved to test_data/test_results.json")
