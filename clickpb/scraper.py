import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import urllib.parse

def parse_clickpb(url='https://www.clickpb.com.br/'):
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
        if os.path.exists('clickpb/index.html'):
            print("Using local cached file instead")
            with open('clickpb/index.html', 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            sys.exit(1)

    soup = BeautifulSoup(html, 'html.parser')

    news = []
    seen_urls = set()

    for a in soup.find_all('a'):
        href = a.get('href')
        if not href:
            continue

        if not (href.startswith('/') or href.startswith('https://www.clickpb.com.br/')):
            continue

        full_url = href if href.startswith('http') else f"https://www.clickpb.com.br{href}"

        # Skip category links
        path_segments = [p for p in href.split('/') if p]
        if len(path_segments) == 1 and not href.endswith('.html'):
            continue

        # ClickPB uses .html for its news articles
        if not full_url.endswith('.html'):
            continue

        if full_url in seen_urls:
            continue

        title = None

        headers_in_a = a.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if headers_in_a:
            for h in headers_in_a:
                t = h.get_text(separator=" ", strip=True)
                if len(t) > 20:
                    title = t
                    break

        if not title:
            text_in_a = a.get_text(separator=" ", strip=True)
            if len(text_in_a) > 25:
                title = text_in_a

        # Some links are just wrappers for images and the title is in the previous sibling link
        if not title and a.find('img') and not a.text.strip():
            prev = a.find_previous_sibling('a', href=href)
            if prev:
                prev_text = prev.get_text(separator=" ", strip=True)
                if len(prev_text) > 20:
                    title = prev_text

        if title:
            title = ' '.join(title.split())

            img_url = None
            img_tag = a.find('img')

            if img_tag:
                img_url = img_tag.get('src')
                # Next.js image optimization handling
                if img_url and '/_next/image?url=' in img_url:
                    # Extract the original URL from Next.js proxy format
                    try:
                        parsed = urllib.parse.urlparse(img_url)
                        query = urllib.parse.parse_qs(parsed.query)
                        if 'url' in query:
                            img_url = query['url'][0]
                    except:
                        pass

                if not img_url or img_url.endswith('.svg') or 'data:image' in img_url:
                    img_url = img_tag.get('data-src') or img_tag.get('data-lazy-src') or img_url
            else:
                # Often the title link doesn't have an image, but an adjacent link does
                next_a = a.find_next_sibling('a', href=href)
                if next_a:
                    img_tag = next_a.find('img')
                    if img_tag:
                        img_url = img_tag.get('src')
                        if img_url and '/_next/image?url=' in img_url:
                            try:
                                parsed = urllib.parse.urlparse(img_url)
                                query = urllib.parse.parse_qs(parsed.query)
                                if 'url' in query:
                                    img_url = query['url'][0]
                            except:
                                pass

            if img_url and not img_url.startswith('http') and not img_url.startswith('data:'):
                img_url = f"https://www.clickpb.com.br{img_url}"

            if img_url and img_url.endswith('.svg'):
                img_url = None

            news.append({
                'titulo': title,
                'link': full_url,
                'imagem': img_url
            })
            seen_urls.add(full_url)

    return news

def main():
    print("Starting scraping process...")
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    news_items = parse_clickpb()
    print(f"Found {len(news_items)} news items")

    output_path = os.path.join(os.path.dirname(__file__), 'noticias.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(news_items, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
