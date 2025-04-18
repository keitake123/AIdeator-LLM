import time
import json
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class YCScraper:
    def __init__(self):
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize the driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.base_url = "https://www.ycombinator.com/companies"
        
    def get_company_links(self, limit: int = 10) -> List[str]:
        """
        Scrape the YC companies directory page to get links to individual company pages.
        """
        try:
            print(f"Loading the companies directory page: {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait longer for the page to load initially
            print("Waiting for companies to load (this may take 15-20 seconds)...")
            
            # Initial fixed wait to ensure page starts loading properly
            time.sleep(20)
            
            # Then try to detect loading completion
            try:
                WebDriverWait(self.driver, 30).until_not(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'loading companies')]"))
                )
                print("Loading message disappeared - content should be loaded")
            except:
                print("Loading message not found or timed out - continuing anyway")
            
            # Additional longer wait to be extra safe
            print("Giving page additional time to fully render...")
            time.sleep(10)
            
            # Check if content is visible
            print("Looking for company links based on the DOM structure...")
            
            # Find all company links based on the DOM structure from the screenshot
            company_links = []
            
            # Using the exact class from the screenshot
            try:
                print("Looking for links with class '_company_i9oky_355' or similar...")
                # Try with wildcard for the dynamic class name part
                links = self.driver.find_elements(By.CSS_SELECTOR, "a[class*='_company_']")
                if links:
                    print(f"Found {len(links)} links with company class")
                    for link in links:
                        href = link.get_attribute("href")
                        # Also try to get the href property directly
                        if not href:
                            try:
                                href = self.driver.execute_script("return arguments[0].getAttribute('href');", link)
                            except:
                                pass
                                
                        normalized_url = self.parse_company_url(href)
                        if normalized_url:
                            company_links.append(normalized_url)
            except Exception as e:
                print(f"Error finding company links with class: {str(e)}")
            
            # If no links found, try with href attribute
            if not company_links:
                print("Trying with href attribute starting with '/companies/'...")
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, "a[href^='/companies/']")
                    if links:
                        print(f"Found {len(links)} links with href starting with '/companies/'")
                        for link in links:
                            href = link.get_attribute("href")
                            normalized_url = self.parse_company_url(href)
                            if normalized_url:
                                company_links.append(normalized_url)
                except Exception as e:
                    print(f"Error finding links with href: {str(e)}")
            
            # If still no links, try JavaScript approach
            if not company_links:
                print("Using JavaScript to extract company links...")
                try:
                    js_links = self.driver.execute_script("""
                        const companyLinks = [];
                        // Get all anchor elements
                        const anchors = document.querySelectorAll('a');
                        
                        // Iterate through each anchor
                        for (const a of anchors) {
                            // Check href attribute
                            const href = a.getAttribute('href');
                            if (href && href.includes('/companies/') && !href.endsWith('/companies')) {
                                // Skip known non-company pages
                                if (!href.includes('/founders') && !href.includes('/directory')) {
                                    companyLinks.push(href);
                                }
                            }
                        }
                        
                        return companyLinks;
                    """)
                    
                    if js_links:
                        print(f"Found {len(js_links)} links using JavaScript")
                        for href in js_links:
                            normalized_url = self.parse_company_url(href)
                            if normalized_url:
                                company_links.append(normalized_url)
                except Exception as e:
                    print(f"Error using JavaScript to extract links: {str(e)}")
            
            # Take a screenshot for debugging
            debug_dir = "debug_data"
            os.makedirs(debug_dir, exist_ok=True)
            screenshot_path = os.path.join(debug_dir, "company_links_debug.png")
            self.driver.save_screenshot(screenshot_path)
            print(f"Screenshot saved as {screenshot_path} for debugging")
            
            # Save page source for debugging
            html_path = os.path.join(debug_dir, "company_links_debug.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"Page source saved as {html_path} for debugging")
            
            # Remove duplicates while preserving order
            filtered_links = []
            seen = set()
            for link in company_links:
                if link not in seen:
                    seen.add(link)
                    filtered_links.append(link)
            
            # Filter out any remaining non-company links
            company_links = [link for link in filtered_links if '/companies/' in link and 
                           not link.endswith('/companies') and
                           not '/founders' in link and 
                           not '/directory' in link]
            
            print(f"Found {len(company_links)} unique company links")
            
            # Limit the number of links
            if limit > 0:
                company_links = company_links[:limit]
                
            return company_links
            
        except Exception as e:
            print(f"Error getting company links: {str(e)}")
            
            # Take a screenshot for error debugging
            debug_dir = "debug_data"
            os.makedirs(debug_dir, exist_ok=True)
            self.driver.save_screenshot(os.path.join(debug_dir, "error_screenshot.png"))
            
            return []
    
    def parse_company_url(self, href):
        """
        Parse and normalize company URLs, handling both relative and absolute URLs.
        """
        if not href:
            return None
            
        # Handle relative URLs (starting with /)
        if href.startswith('/companies/'):
            return f"https://www.ycombinator.com{href}"
            
        # Handle absolute URLs
        if 'ycombinator.com/companies/' in href:
            return href
            
        return None
    
    
    def scrape_companies(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Main method to scrape detailed information for YC companies.
        """
        try:
            # First get the company links
            company_links = self.get_company_links(limit)
            
            # Then scrape details for each company
            companies_data = []
            for i, link in enumerate(company_links, 1):
                print(f"\nScraping company {i}/{len(company_links)}: {link}")
                company_data = self.scrape_company_details(link)
                companies_data.append(company_data)
                
                # Add a small delay between requests to avoid overloading the server
                if i < len(company_links):
                    time.sleep(2)
            
            return companies_data
            
        except Exception as e:
            print(f"Error in scraping process: {str(e)}")
            return []
        finally:
            # Always close the browser
            self.driver.quit()

    def scrape_company_details(self, company_url: str) -> Dict[str, Any]:
        """
        Scrape detailed information from an individual company page.
        """
        try:
            print(f"Loading company page: {company_url}")
            self.driver.get(company_url)
            
            # Wait just briefly for company detail page to load
            print("Waiting for company details to load...")
            time.sleep(2)
            
            # Create a debug directory for screenshots and HTML
            debug_dir = "debug_data"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Get company name from URL for naming debug files
            company_slug = company_url.split('/')[-1]
            
            # Take a screenshot for debugging
            screenshot_path = os.path.join(debug_dir, f"company_detail_{company_slug}.png")
            self.driver.save_screenshot(screenshot_path)
            
            # Save HTML for debugging
            html_path = os.path.join(debug_dir, f"company_detail_{company_slug}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            
            # Extract company name using various selectors
            company_name = "Unknown Company"
            name_selectors = [
                "h1", 
                ".company-name", 
                ".CompanyHeader_name__5_lbo",
                "[data-component='CompanyName']",
                ".company-profile-header h1",
                ".headline"
            ]
            
            for selector in name_selectors:
                try:
                    name_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in name_elements:
                        name = element.text.strip()
                        if name and len(name) < 100:  # Basic validation
                            company_name = name
                            break
                    if company_name != "Unknown Company":
                        break
                except Exception as e:
                    print(f"Error extracting name with selector {selector}: {str(e)}")
            
            # If selectors don't work, try JavaScript
            if company_name == "Unknown Company":
                try:
                    company_name = self.driver.execute_script("""
                        // Look for h1 elements
                        const h1s = document.querySelectorAll('h1');
                        for (const h1 of h1s) {
                            if (h1.textContent && h1.textContent.trim().length < 100) {
                                return h1.textContent.trim();
                            }
                        }
                        return 'Unknown Company';
                    """)
                except Exception as e:
                    print(f"Error extracting name with JavaScript: {str(e)}")
            
            # Extract company blurb (short description/tagline)
            company_blurb = ""
            blurb_selectors = [
                # NEW SELECTORS FROM SCREENSHOT
                ".prose.hidden.max-w-full",      # From the first screenshot
                "div.prose.hidden",              # More generic version
                ".text-xl",                      # From the first screenshot (text class)
                
                # Original selectors as fallback
                ".company-one-liner", 
                ".tagline",
                "[data-component='CompanyTagline']"
            ]
            
            for selector in blurb_selectors:
                try:
                    blurb_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in blurb_elements:
                        blurb = element.text.strip()
                        if blurb:
                            company_blurb = blurb
                            break
                    if company_blurb:
                        break
                except Exception as e:
                    print(f"Error extracting blurb with selector {selector}: {str(e)}")
            
            # If selectors don't work, try JavaScript for blurb
            if not company_blurb:
                try:
                    company_blurb = self.driver.execute_script("""
                        // Try to find tagline based on the screenshots
                        // First try the specific classes from screenshots
                        const blurbElements = [
                            ...document.querySelectorAll('.prose.hidden.max-w-full'),
                            ...document.querySelectorAll('.text-xl'),
                            ...document.querySelectorAll('div.prose.hidden')
                        ];
                        
                        for (const el of blurbElements) {
                            const text = el.textContent.trim();
                            if (text) {
                                return text;
                            }
                        }
                        
                        // Fallback to more generic short text blocks
                        const taglineElements = [
                            ...document.querySelectorAll('h2'),
                            ...document.querySelectorAll('p')
                        ];
                        
                        for (const el of taglineElements) {
                            const text = el.textContent.trim();
                            // Taglines are typically short
                            if (text && text.length > 10 && text.length < 200) {
                                return text;
                            }
                        }
                        return '';
                    """)
                except Exception as e:
                    print(f"Error extracting blurb with JavaScript: {str(e)}")
            
            # Extract detailed description
            company_description = ""
            description_selectors = [
                # NEW SELECTORS FROM SCREENSHOT
                ".prose.max-w-full.whitespace-pre-line",  # From the second screenshot
                "div.prose.max-w-full",                   # More general version
                
                # Original selectors as fallback
                ".company-description", 
                ".about-description",
                "[data-component='CompanyDescription']"
            ]
            
            for selector in description_selectors:
                try:
                    desc_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if desc_elements:
                        # Combine multiple paragraphs if found
                        description_text = " ".join([el.text.strip() for el in desc_elements if el.text.strip()])
                        if description_text:
                            company_description = description_text
                            break
                except Exception as e:
                    print(f"Error extracting description with selector {selector}: {str(e)}")
            
            # If selectors don't work, try JavaScript
            if not company_description:
                try:
                    company_description = self.driver.execute_script("""
                        // Try to find the description content based on screenshots
                        const descElements = document.querySelectorAll('.prose.max-w-full.whitespace-pre-line, div.prose.max-w-full');
                        
                        for (const el of descElements) {
                            const text = el.textContent.trim();
                            if (text && text.length > 100) {
                                return text;
                            }
                        }
                        
                        // Fallback to finding the longest paragraph
                        const paragraphs = document.querySelectorAll('p');
                        let longestContent = '';
                        
                        for (const p of paragraphs) {
                            const text = p.textContent.trim();
                            if (text.length > longestContent.length) {
                                longestContent = text;
                            }
                        }
                        
                        return longestContent;
                    """)
                except Exception as e:
                    print(f"Error extracting description with JavaScript: {str(e)}")
            
            # Extract company logo/profile picture URL
            company_logo_url = ""
            logo_selectors = [
                ".company-logo img", 
                ".CompanyHeader_logo__Yd4Bz img",
                ".logo img",
                "[data-component='CompanyLogo'] img",
                "img[alt*='logo']",
                ".profile-pic img",
                "header img",      # Images in header
                ".header img",     # Images in elements with header class
                "img"              # Any image as last resort
            ]
            
            for selector in logo_selectors:
                try:
                    logo_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in logo_elements:
                        src = element.get_attribute("src")
                        if src and (src.endswith('.png') or src.endswith('.jpg') or src.endswith('.jpeg') or src.endswith('.svg')):
                            company_logo_url = src
                            break
                    if company_logo_url:
                        break
                except Exception as e:
                    print(f"Error extracting logo with selector {selector}: {str(e)}")
            
            # If selectors don't work, try JavaScript
            if not company_logo_url:
                try:
                    company_logo_url = self.driver.execute_script("""
                        // Try to find company logo
                        const images = document.querySelectorAll('img');
                        for (const img of images) {
                            const src = img.getAttribute('src');
                            if (src && (src.endsWith('.png') || src.endsWith('.jpg') || 
                                src.endsWith('.jpeg') || src.endsWith('.svg'))) {
                                
                                // Prioritize images that might be logos
                                const alt = img.getAttribute('alt') || '';
                                if (alt.toLowerCase().includes('logo')) {
                                    return src;
                                }
                                
                                // Check if the image is reasonably sized (logos are usually square-ish)
                                const width = img.width;
                                const height = img.height;
                                if (width > 30 && height > 30 && width/height < 3 && height/width < 3) {
                                    return src;
                                }
                            }
                        }
                        return '';
                    """)
                except Exception as e:
                    print(f"Error extracting logo with JavaScript: {str(e)}")
            
            # Construct company data object
            company_data = {
                'name': company_name,
                'blurb': company_blurb,
                'description': company_description,
                'logo_url': company_logo_url,
                'url': company_url,
                'source': 'Y Combinator'
            }
            
            print(f"Scraped details for: {company_name}")
            return company_data
            
        except Exception as e:
            print(f"Error scraping company details: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'name': "Error",
                'blurb': "",
                'description': f"Failed to scrape: {str(e)}",
                'logo_url': "",
                'url': company_url,
                'source': 'Y Combinator'
            }
        
    def save_companies_to_file(self, companies: List[Dict[str, Any]], filename: str = "yc_companies_detailed.json") -> bool:
        """
        Save scraped companies to a JSON file.
        """
        try:
            os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(companies, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved {len(companies)} companies to {filename}")
            return True
        except Exception as e:
            print(f"Error saving companies to file: {str(e)}")
            return False


if __name__ == "__main__":
    # Test the scraper with a limit of 5 companies
    scraper = YCScraper()
    
    print("Running test scrape for the first 5 YC companies...")
    
    # Use the scrape_companies method with a limit of 5
    companies = scraper.scrape_companies(limit=5)
    
    # Save the test results
    test_file = "test_data/yc_companies_detailed.json"
    scraper.save_companies_to_file(companies, test_file)
    
    # Print results
    print(f"\nTotal companies scraped in test: {len(companies)}")
    
    if companies:
        print("\nList of all companies in test:")
        for i, company in enumerate(companies, 1):
            print(f"{i}. {company['name']}")
            print(f"   Blurb: {company['blurb']}")
            print(f"   Description: {company['description'][:100]}..." if len(company['description']) > 100 else f"   Description: {company['description']}")
            print(f"   Logo URL: {company['logo_url']}")
            print(f"   Company URL: {company['url']}")
            print()
    else:
        print("\nNo companies found. Check the logs for debugging.")
    
    print(f"Test data saved to {test_file}")