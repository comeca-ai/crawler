import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import re

def parse_portalcorreio(url='https://portalcorreio.com.br/'):
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
        if os.path.exists('portalcorreio/index.html'):
            print("Using local cached file instead")
            with open('portalcorreio/index.html', 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            sys.exit(1)

    soup = BeautifulSoup(html, 'html.parser')

    news = []
    seen_urls = set()

    # Exclude common non-news patterns
    exclude_paths = [
        'politica-de-privacidade', 'fale-conosco', 'expediente', 'quem-somos',
        'joao-pessoa-438-anos', 'joao-pessoa-439-anos', 'campina-grande-159-anos'
    ]

    for a in soup.find_all('a'):
        href = a.get('href')
        if not href or not href.startswith('https://portalcorreio.com.br/'): continue

        # News articles in portalcorreio usually are direct subpaths or under /colunas/
        path = href.replace('https://portalcorreio.com.br/', '').strip('/')
        if not path or path in exclude_paths: continue

        # Skip pure category links (usually short words with no hyphens)
        if '-' not in path and '/' not in path and len(path) < 15: continue

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

        # Check inside 'a' tag
        img = a.find('img')
        if img:
            img_url = img.get('data-src') or img.get('src')

        # Check in parent structure (often title and image are separate links to the same href)
        if not img_url:
            parent = a.find_parent(['div', 'article', 'li'])
            if parent:
                sibling_a = parent.find_all('a', href=href)
                for sa in sibling_a:
                    img = sa.find('img')
                    if img:
                        img_url = img.get('data-src') or img.get('src')
                        break

        title = re.sub(r'\s+', ' ', title).strip()

        # Ignore empty/placeholder images
        if img_url and ('empty' in img_url or 'placeholder' in img_url):
            img_url = None

        # Format image URL
        if img_url and img_url.endswith('.svg'):
            img_url = None
        elif img_url and not img_url.startswith('http') and not img_url.startswith('data:'):
            img_url = f"https://portalcorreio.com.br{img_url}"

        news.append({
            'titulo': title,
            'link': clean_href,
            'imagem': img_url
        })
        seen_urls.add(clean_href)

    return news

def main():
    print("Starting scraping process...")
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    news_items = parse_portalcorreio()
    print(f"Found {len(news_items)} news items")

    output_path = os.path.join(os.path.dirname(__file__), 'noticias.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(news_items, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
