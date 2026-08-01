import requests
from bs4 import BeautifulSoup
import json
import os
import sys

def parse_jornal_da_paraiba(url='https://jornaldaparaiba.com.br/'):
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
        # Try local file if fetching fails
        if os.path.exists('jornal_da_paraiba/index.html'):
            print("Using local cached file instead")
            with open('jornal_da_paraiba/index.html', 'r', encoding='utf-8') as f:
                html = f.read()
        else:
            sys.exit(1)

    soup = BeautifulSoup(html, 'html.parser')

    news = []
    seen_urls = set()

    # Iterate all anchors to capture standard news links
    for a in soup.find_all('a'):
        href = a.get('href')
        if not href:
            continue

        if not (href.startswith('/') or href.startswith('http')):
            continue

        full_url = href if href.startswith('http') else f"https://jornaldaparaiba.com.br{href}"

        # Simple heuristic to exclude structural and social links
        skip_paths = ['/ultimas', '/esportes', '/entre-linhas', '/politica', '/qualaboa',
                     '/entretenimento', '/blogs', '/bichos', '/series', '/sobre', '/editais',
                     '/politica-de-privacidade', '/tabuas-de-mares']

        if href in skip_paths:
            continue

        if any(s in href for s in ['facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', '/cdn-cgi/']):
            continue

        if full_url in seen_urls:
            continue

        title = None

        # Look for headers inside 'a' (common for featured articles)
        headers_in_a = a.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if headers_in_a:
            for h in headers_in_a:
                t = h.get_text(separator=" ", strip=True)
                if len(t) > 20:
                    title = t
                    break

        # Look for text directly inside 'a'
        if not title:
            text_in_a = a.get_text(separator=" ", strip=True)
            if len(text_in_a) > 25 and not any(w in text_in_a.lower() for w in ['acessar', 'leia mais', 'veja mais']):
                # Filter out strings that are just categories combined with other stuff
                if "•" not in text_in_a and "|" not in text_in_a:
                    title = text_in_a

        # Check parent structure if 'a' only wraps an image (common for image links where title is a sibling)
        if not title and a.find('img') and not a.text.strip():
            # If a wraps just an image, check siblings or parents for the title
            parent = a.parent
            if parent:
                # Look for a header or paragraph with a link to the same href
                sibling_a = parent.find_all('a', href=href)
                for sa in sibling_a:
                    if sa != a:
                        sa_text = sa.get_text(separator=" ", strip=True)
                        if len(sa_text) > 20:
                            title = sa_text
                            break

        # Look for structured articles/divs explicitly
        if not title:
            parent_article = a.find_parent('article')
            if parent_article:
                headers = parent_article.find_all(['h1', 'h2', 'h3'])
                for h in headers:
                    h_text = h.get_text(separator=" ", strip=True)
                    if len(h_text) > 20:
                        title = h_text
                        break

        if title:
            # Clean up title (remove trailing/leading spaces or newlines)
            title = ' '.join(title.split())

            # Skip non-news titles that might have slipped through
            if any(title.startswith(x) for x in ["Caderno Animal", "Conversa Política", "Entre Linhas", "Pleno Poder"]):
                continue

            img_url = None
            img_tag = a.find('img')

            if img_tag:
                img_url = img_tag.get('src')
                if not img_url or img_url.endswith('.svg') or 'data:image' in img_url:
                    img_url = img_tag.get('data-src') or img_tag.get('data-lazy-src') or img_url
            else:
                # Look in parent
                parent = a.find_parent('article') or a.find_parent('div', class_=lambda x: x and ('post' in x.lower() or 'item' in x.lower()))
                if parent:
                    img_tag = parent.find('img')
                    if img_tag:
                        img_url = img_tag.get('src')
                        if not img_url or img_url.endswith('.svg') or 'data:image' in img_url:
                            img_url = img_tag.get('data-src') or img_tag.get('data-lazy-src') or img_url

            # Sometimes the image is in a previous sibling if `a` is just text
            if not img_url:
                prev = a.find_previous_sibling()
                if prev and prev.name == 'a' and prev.get('href') == href:
                    img = prev.find('img')
                    if img:
                        img_url = img.get('src')
                        if not img_url or img_url.endswith('.svg') or 'data:image' in img_url:
                            img_url = img.get('data-src') or img.get('data-lazy-src') or img_url

            # Format image URL
            if img_url and not img_url.startswith('http') and not img_url.startswith('data:'):
                img_url = f"https://jornaldaparaiba.com.br{img_url}"

            if img_url and img_url.endswith('.svg'):
                img_url = None

            news.append({
                'title': title,
                'url': full_url,
                'image': img_url
            })
            seen_urls.add(full_url)

    return news

def main():
    print("Starting scraping process...")
    os.makedirs('jornal_da_paraiba', exist_ok=True)
    news_items = parse_jornal_da_paraiba()
    print(f"Found {len(news_items)} news items")

    output_path = os.path.join('jornal_da_paraiba', 'noticias.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(news_items, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
