#!/usr/bin/env python3
"""
update_news.py
- Updates leaderboard.json's timestamp (UTC)
- Pulls Top 5 AI news items from official feeds
- Writes back to leaderboard.json under the "news" array
"""

import json, time, re
from datetime import datetime, timezone
import urllib.request
import xml.etree.ElementTree as ET

JSON_PATH = "leaderboard.json"
MAX_ITEMS = 5
FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://deepmind.google/discover/blog/feed.xml",
    "https://ai.google.dev/news.xml",
    "https://research.google/blog/rss/",
    # If Anthropic’s RSS 404s, it’s skipped gracefully:
    "https://www.anthropic.com/news/rss.xml",
]
KEYWORDS = [
    "sora", "veo", "gemini", "claude", "gpt", "realtime", "text-to-video",
    "agent", "multimodal", "model", "release", "update", "capability",
]

def fetch(url, timeout=20):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()
    except Exception:
        return b""

def parse_feed(xml_bytes):
    """Return list of (title, link, pub, desc) from RSS or Atom."""
    if not xml_bytes:
        return []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return []
    items = []
    # RSS 2.0
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = (item.findtext("description") or "").strip()
        items.append((title, link, pub, desc))
    # Atom
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = (link_el.get("href") if link_el is not None else "").strip()
        pub = (entry.findtext("{http://www.w3.org/2005/Atom}updated") or
               entry.findtext("{http://www.w3.org/2005/Atom}published") or "").strip()
        desc = (entry.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
        items.append((title, link, pub, desc))
    return items

def looks_relevant(title, desc):
    blob = f"{title} {desc}".lower()
    return any(k in blob for k in KEYWORDS)

def clean_html(text):
    t = re.sub(r"<[^>]+>", "", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def to_news_obj(t, link, pub, desc):
    summary = clean_html(desc)
    if len(summary) > 220:
        summary = summary[:217] + "…"
    return {"title": t, "date": pub or "", "summary": summary, "url": link}

def main():
    # Load current JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1) Update timestamp (UTC)
    data["timestamp"] = datetime.now(timezone.utc).strftime("%B %d, %Y – %I:%M %p UTC")

    # 2) Aggregate feeds and pick Top 5 relevant items
    pool = []
    for u in FEEDS:
        xml = fetch(u)
        time.sleep(0.5)  # polite pause
        pool.extend(parse_feed(xml))

    ranked = []
    for (title, link, pub, desc) in pool:
        if not title or not link:
            continue
        score = 1 if looks_relevant(title, desc) else 0
        ranked.append((score, title, link, pub, desc))
    ranked.sort(key=lambda x: x[0], reverse=True)

    top = []
    seen = set()
    for _, t, link, pub, desc in ranked:
        if (t, link) in seen:
            continue
        seen.add((t, link))
        top.append(to_news_obj(t, link, pub, desc))
        if len(top) >= MAX_ITEMS:
            break

    if top:  # keep existing news if nothing found
        data["news"] = top

    # 3) Save back
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
