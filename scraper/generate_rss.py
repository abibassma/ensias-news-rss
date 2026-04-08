#!/usr/bin/env python3
import os, re, sys
# from datetime import datetime
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

BASE = "https://ensias.um5.ac.ma"
LIST_URL = "https://ensias.um5.ac.ma/news/"

def fetch(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

'''
def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    # Adjust selector if needed: target the repeating news item element
    items = []
    for el in soup.select("div.card, article, .news-item, .post, li"):  # broad; script filters below
        a = el.find("a", href=True)
        if not a: continue
        href = urljoin(BASE, a["href"])
        title = (a.get_text(strip=True) or el.find(["h1","h2","h3","h4"]).get_text(strip=True) if el.find(["h1","h2","h3","h4"]) else None)
        if not title: title = a.get_text(strip=True)
        # Try to find a date in element
        date_text = None
        time_el = el.find("time")
        if time_el and time_el.get("datetime"):
            date_text = time_el["datetime"]
        elif time_el:
            date_text = time_el.get_text(strip=True)
        else:
            # search for common date patterns
            dt = el.get_text(" ", strip=True)
            m = re.search(r"(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})", dt)
            date_text = m.group(1) if m else None
        items.append({"title": title, "link": href, "date": date_text})
    # Deduplicate by link and keep first occurrences
    seen = set(); uniq=[]
    for it in items:
        if it["link"] in seen: continue
        seen.add(it["link"]); uniq.append(it)
    return uniq
'''

def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("div.view-content")
    if not container:
        return []
    items = []
    for row in container.select("div.views-row"):
        a = row.select_one("div.views-field.views-field-title a")
        if not a:
            continue
        title = a.get_text(strip=True)
        link = urljoin(BASE, a["href"])
        # image (optional)
        img = row.select_one("div.views-field-field-image img")
        image_url = urljoin(BASE, img["src"]) if img and img.get("src") else None
        # summary / teaser
        body_el = row.select_one("div.views-field.views-field-body .field-content")
        summary = body_el.get_text(" ", strip=True) if body_el else ""
        # try to find a date in the row (not present here) — leave None
        items.append({
            "title": title,
            "link": link,
            "image": image_url,
            "summary": summary,
            "date": None
        })
    return items


def parse_item_date(date_text):
    if not date_text: return None
    for fmt in ("%Y-%m-%d","%d %B %Y","%d %b %Y","%B %d, %Y","%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_text.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def build_feed(items):
    fg = FeedGenerator()
    fg.id(LIST_URL)
    fg.title("ENSIAS News (generated)")
    fg.link(href=LIST_URL, rel="alternate")
    fg.link(href=urljoin(LIST_URL, "rss.xml"), rel="self")
    fg.description("Auto-generated RSS feed for ENSIAS news page")
    fg.language("en")
    '''
    for it in items[:30]:
        fe = fg.add_entry()
        fe.id(it["link"])
        fe.link(href=it["link"])
        fe.title(it["title"])
        dt = parse_item_date(it.get("date"))
        if dt:
            fe.pubDate(dt)
        else:
            fe.pubDate(datetime.now(timezone.utc))
        # Optional: fetch article page for description (skipped for speed)
        fe.description(it.get("title"))
    '''
    for it in items[:30]:
        fe = fg.add_entry()
        fe.id(it["link"])
        fe.link(href=it["link"])
        fe.title(it["title"])
        # description: include image if present
        desc = it.get("summary") or it.get("title")
        if it.get("image"):
            desc = f'<img src="{it["image"]}" alt=""/><br/>' + desc
        fe.description(desc)
        # pubDate: use now if no date
        dt = it.get("date")
        if dt:
            fe.pubDate(dt)
        else:
            fe.pubDate(datetime.now(timezone.utc))

    return fg.rss_str(pretty=True)



def main():
    html = fetch(LIST_URL)
    items = parse_list(html)
    items = list(reversed(items)) # ensure newest first
    rss = build_feed(items)
    out_dir = os.path.join(os.getcwd(), "..", "docs") if os.path.basename(os.getcwd()) == "scraper" else "docs"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "rss.xml"), "wb") as f:
        f.write(rss)
    print("Wrote", os.path.join(out_dir, "rss.xml"))

if __name__ == "__main__":
    main()
