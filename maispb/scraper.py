import requests
from bs4 import BeautifulSoup
import json
import re
import os

def scrape_maispb():
    url = 'https://www.maispb.com.br'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return

    soup = BeautifulSoup(r.text, 'html.parser')

    articles = []
    seen_links = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']

        # News articles have ID and .html at the end
        if not re.match(r'https://www.maispb.com.br/\d+/[a-zA-Z0-9-]+\.html', href):
            continue

        # Remove query params or fragments for deduplication
        clean_href = href.split('?')[0].split('#')[0]

        if clean_href in seen_links:
            continue

        # Try to find an image. First look inside the a_tag, then its parent
        img_tag = a_tag.find('img')
        if not img_tag:
             parent = a_tag.parent
             for _ in range(2):
                  if parent:
                       img_tag = parent.find('img')
                       if img_tag:
                           break
                       parent = parent.parent

        img = None
        if img_tag:
            # Check lazy-loading attributes first
            img = img_tag.get('data-src') or img_tag.get('data-lazy-src') or img_tag.get('src')
            if img and img.startswith('data:image'):
                img = None # Ignore placeholder base64 images unless real one is found

        title = a_tag.text.strip()
        if not title:
             title = a_tag.get('title', '').strip()
        if not title:
             title_tag = a_tag.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
             if title_tag:
                 title = title_tag.text.strip()

        # If title is still empty, look at the parent or siblings
        if not title:
             parent = a_tag.parent
             if parent:
                 heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                 if heading:
                     title = heading.text.strip()

        if title and clean_href:
            articles.append({
                'titulo': title,
                'link': clean_href,
                'imagem': img
            })
            seen_links.add(clean_href)

    if not articles:
        print("No articles found.")
        return

    output_path = os.path.join(os.path.dirname(__file__), 'noticias.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=4, ensure_ascii=False)

    print(f"Successfully extracted {len(articles)} articles to {output_path}")

if __name__ == "__main__":
    scrape_maispb()
