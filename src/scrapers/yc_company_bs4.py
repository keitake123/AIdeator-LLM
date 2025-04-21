import json
import re
import time
import requests
from bs4 import BeautifulSoup

def scrape_company(url, session):
    # Fetch via GET (not POST)
    resp = session.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1. profile picture (logo)
    pic_div = soup.find('div', class_='h-32 w-32 shrink-0 rounded-xl')
    pic_url = None
    if pic_div:
        img = pic_div.find('img')
        if img and img.get('src'):
            pic_url = img['src']
        else:
            style = pic_div.get('style', '')
            m = re.search(r'url\(([^)]+)\)', style)
            if m:
                pic_url = m.group(1).strip('"\'')
    
    # 2. title
    title_div = soup.find('div', class_='flex items-center gap-x-3')
    title = None
    if title_div:
        h1 = title_div.find('h1')
        title = h1.get_text(strip=True) if h1 else title_div.get_text(strip=True)
    
    # 3. blurb
    blurb_div = soup.find('div', class_='prose hidden max-w-full md:block')
    blurb = blurb_div.get_text(strip=True) if blurb_div else None

    # 4. full description
    desc_div = soup.find('div', class_='prose max-w-full whitespace-pre-line')
    description = desc_div.get_text(strip=True) if desc_div else None

    return {
        'url': url,
        'profile_picture': pic_url,
        'title': title,
        'blurb': blurb,
        'description': description
    }

def main():
    # Load your list of company URLs
    with open('data/company_urls.json', 'r') as f:
        urls = json.load(f)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; your-scraper/1.0)'
    })

    results = []
    total = len(urls)
    for i, url in enumerate(urls, 1):
        try:
            data = scrape_company(url, session)
            results.append(data)
            print(f"[{i}/{total}] scraped: {data['title']}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"[{i}/{total}] SKIP (404): {url}")
            else:
                print(f"[{i}/{total}] ERROR scraping {url}: {e}")
        except Exception as e:
            print(f"[{i}/{total}] ERROR scraping {url}: {e}")
        time.sleep(0.5)  # be polite!

    # Save to company_details.json
    with open('data/company_details.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()