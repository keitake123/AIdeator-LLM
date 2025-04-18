import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from ..config import Config

class YCScraper:
    def __init__(self):
        self.headers = Config.DEFAULT_HEADERS
        self.base_url = "https://www.ycombinator.com/companies"
        
    def scrape_companies(self, keywords: List[str] = None, limit: int = 5) -> List[Dict]:
        """
        Scrape Y Combinator companies page for relevant companies.
        
        Args:
            keywords: Optional list of keywords to filter companies
            limit: Maximum number of companies to return
            
        Returns:
            List of dictionaries containing company information
        """
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            companies = []
            
            # Find company cards - update selector based on actual HTML structure
            company_cards = soup.select('.company-card')[:limit]
            
            for card in company_cards:
                try:
                    title = card.select_one('.company-name').text.strip()
                    description = card.select_one('.company-description').text.strip()
                    url = card.select_one('a')['href']
                    if not url.startswith('http'):
                        url = f'https://www.ycombinator.com{url}'
                    
                    # If keywords are provided, check for matches
                    if keywords:
                        if not any(keyword.lower() in (title + description).lower() for keyword in keywords):
                            continue
                    
                    companies.append({
                        'title': title,
                        'description': description,
                        'url': url,
                        'source': 'Y Combinator'
                    })
                except (AttributeError, KeyError):
                    continue
                
                if len(companies) >= limit:
                    break
            
            return companies
            
        except Exception as e:
            print(f"Error scraping Y Combinator: {str(e)}")
            return []

    def get_recent_companies(self, limit: int = 5) -> List[Dict]:
        """
        Get the most recently added companies from Y Combinator.
        
        Args:
            limit: Maximum number of companies to return
            
        Returns:
            List of dictionaries containing company information
        """
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            companies = []
            
            # Find company cards - update selector based on actual HTML structure
            company_cards = soup.select('.company-card')[:limit]
            
            for card in company_cards:
                try:
                    title = card.select_one('.company-name').text.strip()
                    description = card.select_one('.company-description').text.strip()
                    url = card.select_one('a')['href']
                    if not url.startswith('http'):
                        url = f'https://www.ycombinator.com{url}'
                    
                    companies.append({
                        'title': title,
                        'description': description,
                        'url': url,
                        'source': 'Y Combinator'
                    })
                except (AttributeError, KeyError):
                    continue
                
                if len(companies) >= limit:
                    break
            
            return companies
            
        except Exception as e:
            print(f"Error getting recent companies: {str(e)}")
            return [] 