#!/usr/bin/env python3
import json, time, re
from datetime import datetime, timezone
import urllib.request
import xml.etree.ElementTree as ET

# ----- CONFIG -----
JSON_PATH = "leaderboard.json"
MAX_ITEMS = 5
FEEDS = [
  # Official sources with stable RSS/Atom
  "https://openai.com/blog/rss.xml",
  "https://deepmind.google/discover/blog/feed.xml",
  "https://www.anthropic.com/news/rss.xml",          # if this 404s, we skip
  "https://ai.google.dev/news.xml",                   # Gemini / Google AI updates
  "https://research.google/blog/rss/"                 # fallback Google Research
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
  if not xml_bytes:
    return []
  try:
    root = ET.fromstring(xml_bytes)
  except Exception:
    return []
  # Support RSS and Atom
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

def to_news_obj(t, link, pub, desc):
  # Try to format pub date nicely
  try:
    # Best effort: many feeds use RFC-822; we’ll leave as-is if parsing fails.
    d = pub
  except Exception:
    d = pub or ""
  # Shorten long descriptions
  clean = re.sub(r"<[^>]+>", "", desc or "")
  clean = re.sub(r"\s+", " ", clean).strip()
  if len(clean) > 220:
    clean = clean[:217] + "…"
  return {"title": t, "date": d or "", "summary": clean, "url": link}

def main():
  # Load current JSON
  with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

  # Update timestamp (UTC; your site shows this as-is)
  now_utc = datetime.now(timezone.utc).strftime("%B %d, %Y – %I:%M %p UTC")
  data["timestamp"] = now_utc

  # Aggregate feeds
  pool = []
  for u in FEEDS:
    xml = fetch(u)
    time.sleep(0.5)  # be polite
    pool.extend(parse_feed(xml))

  # Simple scoring: relevance first, then recency by feed order
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

  # If no items found, keep existing news
  if top:
    data["news"] = top

  # Save back
  with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
  main()
