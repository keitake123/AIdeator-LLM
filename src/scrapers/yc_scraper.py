import os
import time
import json
import random
import logging
import traceback
from logging.handlers import RotatingFileHandler
from queue import Queue, Empty
from threading import Thread, Lock
from typing import Set, Dict, Any, Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ----------------------
# Configuration
# ----------------------
BASE_URL = "https://www.ycombinator.com/companies"
# List of batch identifiers to iterate through
BATCHES = [
    "X25", "W25", "F24", "S24", "W24", "S23", "W23", "S22", "W22", "S21", "W21", "S20", "W20", 
    "S19", "W19", "S18", "W18", "S17", "W17", "IK12", "S16", "W16", "S15", 
    "W15", "S14", "W14", "S13", "W13", "S12", "W12", "S11", "W11",
    "S10", "W10", "S09", "W09", "S08", "W08", "S07", "W07", "S06", 
    "W06", "S05"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/93.0.4577.63 Safari/537.36",
]
IMPLICIT_WAIT = 5
SCROLL_PAUSE = 1.5
MAX_SCROLLS = 200       # Reduced for each batch since they're smaller
MAX_STAGNANT_SCROLLS = 10  # Fewer scrolls before giving up on a batch
CHECKPOINT_INTERVAL = 50

data_dir = "data"
urls_file = os.path.join(data_dir, "company_urls.json")
batch_urls_dir = os.path.join(data_dir, "batch_urls")  # New directory for batch-specific URLs
checkpoint_file = os.path.join(data_dir, "checkpoint.json")
jsonl_file = os.path.join(data_dir, "yc_companies.jsonl")
json_file = os.path.join(data_dir, "yc_companies.json")
log_file = "yc_scraper.log"

# ----------------------
# Logging
# ----------------------
os.makedirs(data_dir, exist_ok=True)
os.makedirs(batch_urls_dir, exist_ok=True)  # Create batch URLs directory
logger = logging.getLogger("YCScraper")
logger.setLevel(logging.INFO)
rot_handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
rot_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(rot_handler)
logger.addHandler(logging.StreamHandler())

# ----------------------
# Retry Decorator
# ----------------------
def retry(exceptions, tries=3, delay=1, backoff=2):
    def deco(func):
        def wrapper(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"{func.__name__} error: {e}, retry in {mdelay}s...")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return deco

# ----------------------
# Scraper
# ----------------------
class YCBulkScraper:
    def __init__(self, headless: bool=True, resume: bool=False, threads: int=4):
        self.headless = headless
        self.resume = resume
        self.num_threads = max(1, threads)
        self.url_lock = Lock()
        self.checkpoint_lock = Lock()
        self.file_lock = Lock()

        self.company_urls: Set[str] = set()
        self.processed_urls: Set[str] = set()
        self.batch_urls: Dict[str, Set[str]] = {}  # Track URLs by batch
        self.progress = 0
        self.completed_batches: Set[str] = set()  # Track completed batches

        if resume:
            self._load_urls()
            self._load_checkpoint()
            self._load_batch_status()

    def _init_driver(self) -> webdriver.Chrome:
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--disable-popup-blocking")
        opts.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
        drv = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        drv.implicitly_wait(IMPLICIT_WAIT)
        return drv

    def parse_url(self, href: str) -> Optional[str]:
        if not href:
            return None
        if href.startswith("/companies/"):
            url = f"https://www.ycombinator.com{href.split('?')[0]}"
            if "/founders" in url or "/directory" in url or url.endswith("/companies"):
                return None
            return url
        if 'ycombinator.com/companies/' in href:
            url = href.split('?')[0]
            if "/founders" in url or "/directory" in url or url.endswith("/companies"):
                return None
            return url
        return None

    @retry(Exception)
    def _scroll_and_collect_batch(self, driver: webdriver.Chrome, batch: str) -> Set[str]:
        """Collect company URLs for a specific batch."""
        batch_url = f"{BASE_URL}?batch={batch}"
        logger.info(f"Starting collection for batch {batch}: {batch_url}")
        
        batch_urls = set()
        driver.get(batch_url)
        
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/companies/']"))
            )
        except Exception as e:
            logger.warning(f"Timeout waiting for page to load for batch {batch}: {e}")
            # Take a screenshot to diagnose the issue
            debug_dir = os.path.join(data_dir, "debug", "batches")
            os.makedirs(debug_dir, exist_ok=True)
            driver.save_screenshot(os.path.join(debug_dir, f"{batch}_timeout.png"))
            return batch_urls
        
        last_h = driver.execute_script("return document.body.scrollHeight")
        last_count = 0
        stagnant = 0
        consecutive_no_new_links = 0  # Track consecutive scrolls with no new links

        # Debug directory
        debug_dir = os.path.join(data_dir, "debug", "batches")
        os.makedirs(debug_dir, exist_ok=True)
        
        # Take initial screenshot
        driver.save_screenshot(os.path.join(debug_dir, f"{batch}_initial.png"))
        
        # Initial count of links before scrolling
        initial_links = set()
        elems = driver.find_elements(By.CSS_SELECTOR, "a[href*='/companies/']")
        for e in elems:
            url = self.parse_url(e.get_attribute('href'))
            if url:
                initial_links.add(url)
        
        batch_urls.update(initial_links)
        logger.info(f"Found {len(initial_links)} initial links for batch {batch}")
        
        for i in range(MAX_SCROLLS):
            prev_url_count = len(batch_urls)
            
            # Try different scrolling strategies
            
            # 1. Try clicking "Show more" button if present
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(., 'Show') and contains(., 'more')]")
                if btn.is_displayed():
                    btn.click()
                    time.sleep(SCROLL_PAUSE)
                    logger.info(f"Clicked 'Show more' button for batch {batch}")
                    consecutive_no_new_links = 0  # Reset consecutive counter on button click
                    continue
            except:
                pass
            
            # 2. Regular scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE + random.random()*0.5)
            
            # 3. Occasionally do a scroll up and down to trigger different loading
            if i % 5 == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
                time.sleep(0.5)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)

            # Collect links using different methods
            all_links = set()
            
            # Method 1: Direct links
            elems = driver.find_elements(By.CSS_SELECTOR, "a[href*='/companies/']")
            for e in elems:
                url = self.parse_url(e.get_attribute('href'))
                if url:
                    all_links.add(url)
            
            # Method 2: Try to find containers with company cards
            try:
                containers = driver.find_elements(By.CSS_SELECTOR, ".company_card, [class*='company'], [class*='card']")
                for container in containers:
                    links = container.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        url = self.parse_url(link.get_attribute('href'))
                        if url:
                            all_links.add(url)
            except:
                pass
                
            # Method 3: Use JavaScript to find all company links
            try:
                js_links = driver.execute_script("""
                    const links = [];
                    document.querySelectorAll('a').forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && href.includes('/companies/') && 
                            !href.endsWith('/companies') && 
                            !href.includes('/founders') && 
                            !href.includes('/directory')) {
                            links.push(href);
                        }
                    });
                    return links;
                """)
                
                for href in js_links:
                    url = self.parse_url(href)
                    if url:
                        all_links.add(url)
            except Exception as e:
                logger.debug(f"JS extraction failed for batch {batch}: {e}")
            
            # Add all links to our batch set
            batch_urls.update(all_links)

            curr = len(batch_urls)
            new_h = driver.execute_script("return document.body.scrollHeight")
            
            # Check if we found any new links
            if curr == prev_url_count:
                consecutive_no_new_links += 1
                logger.info(f"Batch {batch}: No new links in scroll {i+1} ({consecutive_no_new_links} consecutive)")
            else:
                consecutive_no_new_links = 0  # Reset counter when we find new links
                logger.info(f"Batch {batch} - Scroll {i+1}: Found {curr - prev_url_count} new links, total {curr}")
                
            # Check for stagnation in page height (old method)
            if curr == last_count and new_h == last_h:
                stagnant += 1
            else:
                stagnant = 0
                last_count = curr
                last_h = new_h
                
            # Take screenshots periodically
            if i % 50 == 0 and i > 0:
                driver.save_screenshot(os.path.join(debug_dir, f"{batch}_scroll_{i}.png"))
                
            # Exit conditions
            
            # 1. Stop if we've had three consecutive scrolls with no new links
            if consecutive_no_new_links >= 3:
                logger.info(f"Batch {batch}: No new links after {consecutive_no_new_links} consecutive scrolls, breaking.")
                break
                
            # 2. Traditional stagnation check (backup method)
            if stagnant >= MAX_STAGNANT_SCROLLS:
                logger.info(f"Batch {batch}: Page height unchanged after {stagnant} scrolls, breaking.")
                break

        # Take final screenshot
        driver.save_screenshot(os.path.join(debug_dir, f"{batch}_final.png"))
        
        # Save page source for debugging
        with open(os.path.join(debug_dir, f"{batch}_final.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
            
        logger.info(f"Batch {batch}: Collection completed with {len(batch_urls)} URLs")
        return batch_urls

    def get_company_links_by_batch(self):
        """Collect company URLs by iterating through each batch."""
        if self.resume and self.company_urls:
            logger.info(f"Resuming with {len(self.company_urls)} preloaded URLs")
            return

        drv = self._init_driver()
        try:
            for batch in BATCHES:
                # Skip if we've already processed this batch
                if batch in self.completed_batches:
                    logger.info(f"Skipping already completed batch: {batch}")
                    continue
                
                # Collect URLs for this batch
                batch_urls = self._scroll_and_collect_batch(drv, batch)
                
                # Store batch URLs and save
                self.batch_urls[batch] = batch_urls
                self._save_batch_urls(batch, batch_urls)
                
                # Update overall URL set
                self.company_urls.update(batch_urls)
                
                # Mark batch as completed
                self.completed_batches.add(batch)
                self._save_batch_status()
                
                # Save overall URLs
                self._save_urls()
                
                # Random delay between batches to avoid blocking
                delay = random.uniform(2, 5)
                logger.info(f"Waiting {delay:.2f}s before next batch...")
                time.sleep(delay)
                
        except Exception as e:
            logger.error(f"Error during batch collection: {e}")
            logger.error(traceback.format_exc())
        finally:
            drv.quit()
            
        # Final save
        self._save_urls()
        self._save_batch_status()
        logger.info(f"Total URLs collected across all batches: {len(self.company_urls)}")

    def _load_urls(self):
        if not os.path.exists(urls_file):
            return
            
        try:
            with open(urls_file,'r') as f:
                self.company_urls=set(json.load(f))
            logger.info(f"Loaded {len(self.company_urls)} URLs")
        except Exception as e:
            logger.error(f"Failed loading URLs: {e}")

    def _save_urls(self):
        with self.url_lock:
            try:
                tmp=urls_file+'.tmp'
                with open(tmp,'w') as f:
                    json.dump(list(self.company_urls),f)
                os.replace(tmp,urls_file)
                logger.info(f"Saved {len(self.company_urls)} URLs")
            except Exception as e:
                logger.error(f"Failed saving URLs: {e}")

    def _save_batch_urls(self, batch: str, urls: Set[str]):
        """Save URLs for a specific batch."""
        batch_file = os.path.join(batch_urls_dir, f"{batch}_urls.json")
        try:
            tmp=batch_file+'.tmp'
            with open(tmp,'w') as f:
                json.dump(list(urls),f)
            os.replace(tmp,batch_file)
            logger.info(f"Saved {len(urls)} URLs for batch {batch}")
        except Exception as e:
            logger.error(f"Failed saving batch URLs for {batch}: {e}")

    def _load_batch_status(self):
        """Load the status of which batches have been completed."""
        status_file = os.path.join(data_dir, "batch_status.json")
        if not os.path.exists(status_file):
            return
            
        try:
            with open(status_file,'r') as f:
                data = json.load(f)
                self.completed_batches = set(data.get('completed_batches', []))
                
                # Also load the individual batch URLs
                for batch in self.completed_batches:
                    batch_file = os.path.join(batch_urls_dir, f"{batch}_urls.json")
                    if os.path.exists(batch_file):
                        with open(batch_file, 'r') as bf:
                            self.batch_urls[batch] = set(json.load(bf))
                    
            logger.info(f"Loaded {len(self.completed_batches)} completed batches")
        except Exception as e:
            logger.error(f"Failed loading batch status: {e}")

    def _save_batch_status(self):
        """Save the status of which batches have been completed."""
        status_file = os.path.join(data_dir, "batch_status.json")
        try:
            tmp=status_file+'.tmp'
            with open(tmp,'w') as f:
                json.dump({
                    'completed_batches': list(self.completed_batches),
                    'ts': time.time()
                },f)
            os.replace(tmp,status_file)
            logger.info(f"Saved batch status ({len(self.completed_batches)} completed)")
        except Exception as e:
            logger.error(f"Failed saving batch status: {e}")

    def _load_checkpoint(self):
        if not os.path.exists(checkpoint_file):
            return
            
        try:
            with open(checkpoint_file,'r') as f:
                data=json.load(f)
                self.processed_urls=set(data.get('processed_urls',[]))
            logger.info(f"Loaded {len(self.processed_urls)} processed URLs")
        except Exception as e:
            logger.error(f"Failed loading checkpoint: {e}")

    def _save_checkpoint(self):
        with self.checkpoint_lock:
            try:
                tmp=checkpoint_file+'.tmp'
                with open(tmp,'w') as f:
                    json.dump({'processed_urls':list(self.processed_urls),'ts':time.time()},f)
                os.replace(tmp,checkpoint_file)
                logger.info(f"Checkpoint saved ({len(self.processed_urls)} URLs)")
            except Exception as e:
                logger.error(f"Failed saving checkpoint: {e}")

    @retry(Exception)
    def scrape_detail(self, driver: webdriver.Chrome, url: str) -> Dict[str, Any]:
        driver.get(url)
        try:
            WebDriverWait(driver,10).until(EC.presence_of_element_located((By.TAG_NAME,'h1')))
        except:
            logger.warning(f"Slow load: {url}")

        # Company Name
        name='Unknown'
        h1=driver.find_elements(By.CSS_SELECTOR,'h1')
        if h1: name=h1[0].text.strip()

        # Blurb - try multiple selectors including the specific class mentioned
        blurb=''
        blurb_selectors = [
            ".prose.hidden.max-w-full.md\\:block",  # Specific class with escaped colon
            ".prose.hidden.max-w-full",             # Without md:block
            "div.prose.hidden",                     # Just the main classes
            ".tagline", 
            "[data-component='CompanyTagline']"
        ]
        
        # Try each selector individually
        for selector in blurb_selectors:
            be = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in be:
                text = elem.text.strip()
                if text:
                    blurb = text
                    break
            if blurb:
                break
        
        # If still no blurb, try JavaScript as a fallback
        if not blurb:
            try:
                blurb = driver.execute_script("""
                    // Try specific classes first
                    const elements = document.querySelectorAll('.prose.hidden, .prose.hidden.max-w-full, .prose.hidden.max-w-full.md\\\\:block');
                    for (const el of elements) {
                        if (el.textContent.trim()) return el.textContent.trim();
                    }
                    
                    // Fallback to short paragraphs that could be taglines
                    const paragraphs = document.querySelectorAll('p, h2, h3');
                    for (const p of paragraphs) {
                        const text = p.textContent.trim();
                        if (text && text.length > 10 && text.length < 200) return text;
                    }
                    return '';
                """)
            except Exception as e:
                logger.debug(f"JS blurb extraction error: {e}")

        # Description
        desc=''
        for sel in ['.prose.max-w-full.whitespace-pre-line','div.prose.max-w-full','.company-description']:
            ds=driver.find_elements(By.CSS_SELECTOR,sel)
            texts=[e.text.strip() for e in ds if e.text.strip()]
            if texts:
                desc=' '.join(texts)
                break

        # Logo
        logo=''
        for sel in ['.company-logo img','[data-component=\'CompanyLogo\'] img','img[alt*=logo]', 'header img', '.logo img']:
            ls=driver.find_elements(By.CSS_SELECTOR,sel)
            for e in ls:
                src=e.get_attribute('src')
                if src and src.endswith(tuple(['.png','.jpg','.jpeg','.svg'])):
                    logo=src; break
            if logo: break
        if not logo:
            try:
                logo=driver.execute_script("""
                    let imgs=[...document.querySelectorAll('img')];
                    for(let i of imgs){if(/\\.(png|jpe?g|svg)$/.test(i.src))return i.src;}return '';
                """)
            except:
                pass

        # Get batch information if available
        batch = ''
        try:
            # Try to find batch information on the page
            batch_elem = driver.find_elements(By.CSS_SELECTOR, '.batch, [data-component="CompanyBatch"], [class*="batch"]')
            if batch_elem:
                batch = batch_elem[0].text.strip()
            
            # If not found on page, try to extract from URL parameters
            if not batch and "batch=" in driver.current_url:
                batch_param = driver.current_url.split("batch=")[1].split("&")[0]
                if batch_param:
                    batch = batch_param
                    
            # Clean up batch string
            if batch:
                # Remove any "Batch: " or similar prefix
                batch = batch.replace("Batch:", "").replace("Batch", "").strip()
        except Exception as e:
            logger.debug(f"Error extracting batch: {e}")

        # Take screenshot for debugging
        debug_dir = os.path.join(data_dir, "debug", "companies")
        os.makedirs(debug_dir, exist_ok=True)
        company_slug = url.split('/')[-1]
        try:
            driver.save_screenshot(os.path.join(debug_dir, f"{company_slug}.png"))
        except:
            pass

        return {
            'name': name,
            'blurb': blurb,
            'description': desc,
            'logo_url': logo,
            'batch': batch,  # Add batch information
            'url': url,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

    def worker(self, idx:int, q:Queue, total:int):
        drv=self._init_driver()
        while True:
            try: url=q.get_nowait()
            except Empty: break
            if url in self.processed_urls:
                q.task_done(); continue
            try:
                detail=self.scrape_detail(drv,url)
                with self.file_lock, open(jsonl_file,'a') as f:
                    f.write(json.dumps(detail,ensure_ascii=False)+"\n")
                with self.checkpoint_lock:
                    self.processed_urls.add(url)
                    self.progress+=1
                    if self.progress%CHECKPOINT_INTERVAL==0: self._save_checkpoint()
                logger.info(f"[T{idx}] {self.progress}/{total} {detail['name']} - Blurb: {bool(detail['blurb'])} - Batch: {detail.get('batch', 'Unknown')}")
            except Exception as e:
                logger.error(f"Worker {idx} error on {url}: {str(e)}")
                logger.error(traceback.format_exc())
            finally:
                q.task_done()
        drv.quit(); logger.info(f"Worker {idx} done")

    def scrape_all(self,limit:int=0):
        # First collect all URLs by batch
        self.get_company_links_by_batch()
        
        # Then process the collected URLs
        to=[u for u in self.company_urls if u not in self.processed_urls]
        if limit>0: to=to[:limit]
        total=len(to)
        logger.info(f"Scraping {total} with {self.num_threads} threads")
        q=Queue(); [q.put(u) for u in to]
        ths=[Thread(target=self.worker,args=(i,q,total),daemon=True) for i in range(min(self.num_threads,total))]
        for t in ths: t.start()
        try:
            while q.qsize(): logger.info(f"{q.qsize()}/{total} remaining"); time.sleep(10)
            q.join()
        except KeyboardInterrupt:
            logger.info("Interrupted, saving checkpoint"); self._save_checkpoint(); return
        for t in ths: t.join()
        self._save_checkpoint(); logger.info("Done scraping")

    def consolidate(self):
        if not os.path.exists(jsonl_file): return logger.warning("No data")
        arr=[]
        try:
            with open(jsonl_file) as f: 
                for l in f:
                    if l.strip():
                        try:
                            arr.append(json.loads(l))
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing JSONL line: {e}")
            with open(json_file,'w') as f: 
                json.dump(arr,f,indent=2)
            logger.info(f"Consolidated {len(arr)} entries")
        except Exception as e:
            logger.error(f"Error during consolidation: {e}")
            logger.error(traceback.format_exc())

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--limit',type=int,default=0)
    p.add_argument('--resume',action='store_true'); p.add_argument('--visible',action='store_true')
    p.add_argument('--links-only',action='store_true'); p.add_argument('--threads',type=int,default=4)
    p.add_argument('--batch',help='Scrape only a specific batch (e.g., W23)')
    a=p.parse_args()
    
    sc=YCBulkScraper(headless=not a.visible,resume=a.resume,threads=a.threads)
    
    # If a specific batch is provided, only scrape that batch
    if a.batch:
        # Override BATCHES with just the specified batch
        BATCHES = [a.batch]
        logger.info(f"Scraping only batch: {a.batch}")
    
    if a.links_only: 
        sc.get_company_links_by_batch()  # Changed to batch method
    else: 
        sc.scrape_all(a.limit)
        sc.consolidate()