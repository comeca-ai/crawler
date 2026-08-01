#!/usr/bin/env python3
"""
clickpb_crawler.py

Crawler robusto para clickpb.com.br (exemplo) com boas práticas:
- respeita robots.txt
- usa User-Agent configurável
- retry/backoff e timeout
- rate limiting
- suporta sitemap (opcional)
- salva resultados em CSV

Use em Codespaces ou localmente.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_BASE = "https://www.clickpb.com.br/"
DEFAULT_USER_AGENT = "comeca-ai-crawler/1.0 (+https://github.com/comeca-ai/crawler)"
DEFAULT_RATE = 1.0
DEFAULT_TIMEOUT = 10
DEFAULT_OUTPUT = "results.csv"


logger = logging.getLogger("clickpb_crawler")


@dataclass
class Article:
    title: str
    url: str
    summary: Optional[str] = None
    date: Optional[str] = None
    author: Optional[str] = None
    snippet: Optional[str] = None


def create_session(user_agent: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def load_robots(base_url: str) -> RobotFileParser:
    rp = RobotFileParser()
    robots_url = urljoin(base_url, "robots.txt")
    rp.set_url(robots_url)
    try:
        rp.read()
        logger.debug("Loaded robots.txt from %s", robots_url)
    except Exception:
        logger.warning("Could not read robots.txt (%s). Proceeding cautiously.", robots_url)
    return rp


def can_fetch(rp: RobotFileParser, user_agent: str, url: str) -> bool:
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        # If robot parser fails, return True so caller can decide; default to True
        return True


def fetch(session: requests.Session, url: str, timeout: int) -> Optional[str]:
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.error("Request failed for %s: %s", url, e)
        return None


# Candidate selectors (attempts in order)
ARTICLE_CONTAINERS = [
    "ul.list-news > li",
    ".listagem-noticias li",
    "div.card-noticia",
    "article",
    ".news-list .item",
    ".news-item",
    ".feed .item",
]
TITLE_SELECTORS = ["h2 a", "h3 a", ".title a", ".entry-title a", ".news-headline", "a"]
SUMMARY_SELECTORS = [".summary", ".excerpt", ".lead", ".chapeu", ".entry-summary"]
URL_SELECTOR = "a"
DATE_SELECTORS = ["time", ".post-date", ".published", ".data", ".entry-date"]
AUTHOR_SELECTORS = [".author", ".byline", ".autor", ".entry-author", ".meta-author"]


def parse_homepage(html: str, base: str) -> List[Article]:
    soup = BeautifulSoup(html, "html.parser")
    found: List[Article] = []
    for container in ARTICLE_CONTAINERS:
        items = soup.select(container)
        if not items:
            continue
        logger.debug("Using container selector '%s' -> found %d items", container, len(items))
        for item in items:
            title = None
            url = None
            summary = None
            for tsel in TITLE_SELECTORS:
                el = item.select_one(tsel)
                if el:
                    title = el.get_text(strip=True)
                    if el.has_attr("href"):
                        url = urljoin(base, el["href"])
                    break
            if not url:
                a = item.select_one(URL_SELECTOR)
                if a and a.has_attr("href"):
                    url = urljoin(base, a["href"])
                    if not title:
                        title = a.get_text(strip=True)
            for ssel in SUMMARY_SELECTORS:
                s = item.select_one(ssel)
                if s:
                    summary = s.get_text(strip=True)
                    break
            if title or url:
                found.append(Article(title=title or "", url=url or "", summary=summary))
        if found:
            break
    if not found:
        logger.warning("No articles found on homepage with current selectors. Check selectors in code.")
    return found


def parse_article(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    date_text = None
    author_text = None
    for dsel in DATE_SELECTORS:
        el = soup.select_one(dsel)
        if el:
            date_text = el.get_text(strip=True)
            break
    for asel in AUTHOR_SELECTORS:
        el = soup.select_one(asel)
        if el:
            author_text = el.get_text(strip=True)
            break
    paragraphs = soup.select("article p") or soup.select(".entry-content p")
    snippet = None
    if paragraphs:
        snippet = "\n\n".join(p.get_text(strip=True) for p in paragraphs[:6])
    return {"date": date_text, "author": author_text, "snippet": snippet}


def parse_sitemap_for_urls(sitemap_xml: str, base: str) -> List[str]:
    # Simple XML parse to extract <loc> elements. Avoid heavy deps for portability.
    from xml.etree import ElementTree as ET

    urls: List[str] = []
    try:
        root = ET.fromstring(sitemap_xml)
        for loc in root.findall(".//{*}loc"):
            if loc.text:
                urls.append(loc.text.strip())
    except ET.ParseError:
        logger.warning("Could not parse sitemap XML")
    return urls


def save_csv(path: str, rows: List[Article]):
    fieldnames = ["title", "url", "summary", "date", "author", "snippet"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for a in rows:
            writer.writerow({
                "title": a.title,
                "url": a.url,
                "summary": a.summary or "",
                "date": a.date or "",
                "author": a.author or "",
                "snippet": a.snippet or "",
            })
    logger.info("Saved %d rows to %s", len(rows), path)


def is_same_domain(url: str, base: str) -> bool:
    try:
        return urlparse(url).netloc == urlparse(base).netloc
    except Exception:
        return False


def run(base: str, user_agent: str, rate: float, timeout: int, out_csv: str, use_sitemap: bool, limit: int):
    session = create_session(user_agent)
    rp = load_robots(base)

    to_visit: List[str] = []
    results: List[Article] = []

    if use_sitemap:
        sitemap_url = urljoin(base, "sitemap.xml")
        logger.info("Attempting to fetch sitemap: %s", sitemap_url)
        sitemap_xml = fetch(session, sitemap_url, timeout)
        if sitemap_xml:
            urls = parse_sitemap_for_urls(sitemap_xml, base)
            logger.info("Sitemap provided %d urls", len(urls))
            # Filter same domain
            to_visit = [u for u in urls if is_same_domain(u, base)]

    if not to_visit:
        logger.info("Fetching homepage: %s", base)
        homepage = fetch(session, base, timeout)
        if not homepage:
            logger.error("Failed to fetch homepage. Exiting.")
            return
        articles = parse_homepage(homepage, base)
        for a in articles:
            if a.url and can_fetch(rp, user_agent, a.url):
                to_visit.append(a.url)
            else:
                logger.debug("Skipping (robots or missing url): %s", a.url)

    visited = 0
    for url in to_visit:
        if visited >= limit:
            logger.info("Reached processing limit: %d", limit)
            break
        if not can_fetch(rp, user_agent, url):
            logger.info("Robots disallow URL, skipping: %s", url)
            continue
        logger.info("Fetching article %d: %s", visited + 1, url)
        html = fetch(session, url, timeout)
        if not html:
            continue
        meta = parse_article(html)
        # Attempt to keep title/summary from homepage if present by matching URL
        title = meta.get("title") if meta.get("title") else ""
        # Build Article; maintain any known title by looking at URL page title
        page_soup = BeautifulSoup(html, "html.parser")
        page_title_el = page_soup.select_one("meta[property='og:title'], meta[name='title']")
        if page_title_el and page_title_el.get("content"):
            title = page_title_el.get("content")
        if not title:
            # fallback to h1
            h1 = page_soup.select_one("h1")
            title = h1.get_text(strip=True) if h1 else ""
        summary = None
        # try meta description
        meta_desc = page_soup.select_one("meta[name='description']")
        if meta_desc and meta_desc.get("content"):
            summary = meta_desc.get("content")
        article = Article(title=title, url=url, summary=summary, date=meta.get("date"), author=meta.get("author"), snippet=meta.get("snippet"))
        results.append(article)
        visited += 1
        time.sleep(rate)

    if results:
        save_csv(out_csv, results)
    else:
        logger.info("No results to save.")


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Crawler simples para clickpb.com.br (exemplo)")
    parser.add_argument("--base", default=DEFAULT_BASE, help="Base URL (default: %(default)s)")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent header")
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE, help="Seconds between requests")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout seconds")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="CSV output file")
    parser.add_argument("--sitemap", action="store_true", help="Try reading sitemap.xml for URLs")
    parser.add_argument("--limit", type=int, default=20, help="Max number of articles to process")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    try:
        run(base=args.base, user_agent=args.user_agent, rate=args.rate, timeout=args.timeout, out_csv=args.output, use_sitemap=args.sitemap, limit=args.limit)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
