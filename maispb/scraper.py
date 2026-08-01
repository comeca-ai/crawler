import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import re

def parse_maispb(url='https://www.maispb.com.br'):
    print(f"Fetching {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"Error fetching URL: {e}")
        if os.path.exists('maispb/index.html'):
            print("Using local cached file instead")
            with open('maispb/index.html', 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            sys.exit(1)

    soup = BeautifulSoup(html, 'html.parser')

    news = []
    seen_urls = set()

    for a in soup.find_all('a'):
        href = a.get('href')

        # maispb URLs generally have format: https://www.maispb.com.br/123456/title-slug.html
        if not href or not re.search(r'maispb\.com\.br/\d+/', href):
            continue

        full_url = href if href.startswith('http') else f"https://www.maispb.com.br{href}"
        # Strip query parameters for deduplication
        clean_url = full_url.split('?')[0]

        if clean_url in seen_urls:
            continue

        title = None

        # Strategy 1: Headers in a
        headers_in_a = a.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong'])
        if headers_in_a:
            title = " ".join([h.text.strip() for h in headers_in_a if len(h.text.strip()) > 5])

        # Strategy 2: Direct text in a
        if not title or len(title) < 20:
            text_in_a = a.text.strip()
            if len(text_in_a) > 20:
                title = text_in_a

        # Strategy 3: Look in parent if 'a' is an image wrapper
        if not title:
            parent_div = a.find_parent(['div', 'article', 'li'])
            if parent_div:
                for sibling_a in parent_div.find_all('a'):
                    if sibling_a.get('href') == href and sibling_a != a:
                        if sibling_a.text.strip():
                            title = sibling_a.text.strip()
                            break

        if not title or len(title) < 15:
            continue

        title = ' '.join(title.split())

        img_url = None

        # Strategy 1: Image inside 'a'
        img_tag = a.find('img')
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-src')

        # Strategy 2: Image in parent wrapper
        if not img_url:
            parent_div = a.find_parent(['div', 'article', 'li'])
            if parent_div:
                imgs = parent_div.find_all('img')
                for img in imgs:
                    src = img.get('src') or img.get('data-src')
                    if src and not 'pixel' in src.lower() and not src.endswith('.svg') and not src.endswith('.gif'):
                        img_url = src
                        break

        # Check adjacent links
        if not img_url:
            prev = a.find_previous_sibling('a', href=href)
            if prev:
                img_prev = prev.find('img')
                if img_prev:
                    img_url = img_prev.get('src') or img_prev.get('data-src')

            if not img_url:
                next_a = a.find_next_sibling('a', href=href)
                if next_a:
                    img_next = next_a.find('img')
                    if img_next:
                        img_url = img_next.get('src') or img_next.get('data-src')

        if img_url and not img_url.startswith('http') and not img_url.startswith('data:'):
            img_url = f"https://www.maispb.com.br{img_url}"

        if img_url and img_url.endswith('.svg'):
            img_url = None

        news.append({
            'titulo': title,
            'link': clean_url,
            'imagem': img_url
        })
        seen_urls.add(clean_url)

    return news

def main():
    print("Starting scraping process...")
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    news_items = parse_maispb()
    print(f"Found {len(news_items)} news items")

    output_path = os.path.join(os.path.dirname(__file__), 'noticias.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(news_items, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
