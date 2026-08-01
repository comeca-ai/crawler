import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import re

def parse_paraibaonline(url='https://paraibaonline.com.br/'):
    print(f"Fetching {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"Error fetching URL: {e}")
        if os.path.exists('paraibaonline/index.html'):
            print("Using local cached file instead")
            with open('paraibaonline/index.html', 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            sys.exit(1)

    soup = BeautifulSoup(html, 'html.parser')

    news = []
    seen_urls = set()

    for a in soup.find_all('a'):
        href = a.get('href')
        if not href or not href.startswith('https://paraibaonline.com.br/'): continue
        if href.count('/') <= 4: continue # Skip root categories

        clean_href = href.split('?')[0]
        if clean_href in seen_urls: continue

        title = None
        headers_in_a = a.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if headers_in_a:
            title = " ".join([h.text.strip() for h in headers_in_a])

        if not title:
            title = a.text.strip()

        # Check parent context for titles if it's an image link
        if not title and a.find('img'):
            parent = a.parent
            for sibling_a in parent.find_all('a'):
                if sibling_a.get('href') == href and sibling_a.text.strip():
                    title = sibling_a.text.strip()
                    break

        if not title or len(title) < 15: continue

        # Try finding image
        img_url = None

        # ParaibaOnline uses <div class="img-post" style="background-image: url(...)">
        parent_with_bg = a.find('div', class_='img-post')
        if not parent_with_bg:
            parent_with_bg = a.find_parent('div', class_='img-post')

        if not parent_with_bg:
            img_post = a.find(class_=lambda x: x and 'img' in x.lower())
            if img_post and img_post.get('style'):
                parent_with_bg = img_post

        if parent_with_bg and parent_with_bg.get('style'):
            m = re.search(r'url\([\'"]?(.*?)[\'"]?\)', parent_with_bg.get('style'))
            if m: img_url = m.group(1)

        # Standard img check
        if not img_url:
            img = a.find('img')
            if not img:
                parent = a.find_parent('div')
                if parent:
                    sibling_a = parent.find_all('a', href=href)
                    for sa in sibling_a:
                        img = sa.find('img')
                        if img: break
                        sibling_bg = sa.find('div', class_='img-post')
                        if sibling_bg and sibling_bg.get('style'):
                            m = re.search(r'url\([\'"]?(.*?)[\'"]?\)', sibling_bg.get('style'))
                            if m: img_url = m.group(1)
                            break

            if img and not img_url:
                img_url = img.get('data-src') or img.get('data-lazy-src') or img.get('src')
                # Filter out empty placeholder images
                if img_url and ('empty-img' in img_url or 'placeholder' in img_url):
                    img_url = None

        title = re.sub(r'\s+', ' ', title).strip()

        if img_url and img_url.endswith('.svg'):
            img_url = None

        if img_url and not img_url.startswith('http') and not img_url.startswith('data:'):
            img_url = f"https://paraibaonline.com.br{img_url}"

        news.append({
            'title': title,
            'url': clean_href,
            'image': img_url
        })
        seen_urls.add(clean_href)

    return news

def main():
    print("Starting scraping process...")
    os.makedirs('paraibaonline', exist_ok=True)
    news_items = parse_paraibaonline()
    print(f"Found {len(news_items)} news items")

    output_path = os.path.join('paraibaonline', 'noticias.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(news_items, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
