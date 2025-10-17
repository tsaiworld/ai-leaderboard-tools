#!/usr/bin/env python3
"""
Updates leaderboard.json daily:
- refreshes timestamp
- refreshes Top 6 AI news from official feeds
- recomputes category rankings from a weighted score

Scoring = 0.40*popularity + 0.25*performance + 0.10*cost +
          0.10*privacy + 0.15*innovation

Where the 5 sub-scores (0–100) come from:
- metrics_overrides.json (your manual edits win)
- otherwise: built-in sensible defaults per tool (editable below)

Safe: if a category has fewer than 3 items, it won’t crash.
"""

import json, re, time, os
from datetime import datetime, timezone
import urllib.request
import xml.etree.ElementTree as ET
from copy import deepcopy

JSON_PATH = "leaderboard.json"
OVERRIDES_PATH = "metrics_overrides.json"

# ---------- News feeds ----------
FEEDS = [
  "https://openai.com/blog/rss.xml",
  "https://deepmind.google/discover/blog/feed.xml",
  "https://ai.google.dev/news.xml",
  "https://research.google/blog/rss/",
  # Anthropic doesn't publish a stable RSS for all posts; skip if fails
  "https://www.anthropic.com/news/rss.xml",
]
MAX_NEWS = 10
KEYWORDS = [
  "sora", "veo", "gemini", "claude", "gpt", "realtime", "text-to-video",
  "agent", "multimodal", "model", "release", "update", "capabilities",
]

# ---------- Built-in defaults (0–100 per factor) ----------
# Edit anything here; or better, create/commit metrics_overrides.json
DEFAULTS = {
  # LLM / Text
  "ChatGPT (GPT-4o)":        {"popularity":95, "performance":92, "cost":70, "privacy":70, "innovation":92},
  "Claude 3 (Opus/Sonnet)":  {"popularity":85, "performance":94, "cost":75, "privacy":85, "innovation":86},
  "Gemini 1.5 (Pro/Ultra)":  {"popularity":82, "performance":88, "cost":78, "privacy":80, "innovation":88},

  # Image / Vision
  "Midjourney v6":           {"popularity":92, "performance":90, "cost":75, "privacy":75, "innovation":85},
  "DALL·E 3":                {"popularity":90, "performance":86, "cost":78, "privacy":70, "innovation":84},
  "Stable Diffusion XL":     {"popularity":88, "performance":84, "cost":95, "privacy":92, "innovation":83},

  # Video / Motion
  "Sora 2 (OpenAI)":         {"popularity":90, "performance":95, "cost":50, "privacy":72, "innovation":96},
  "Veo 2 (Google DeepMind)": {"popularity":82, "performance":92, "cost":55, "privacy":82, "innovation":90},
  "Runway Gen-3":            {"popularity":86, "performance":82, "cost":80, "privacy":70, "innovation":84},

  # Audio / Music
  "Sunō v3":                 {"popularity":84, "performance":85, "cost":82, "privacy":65, "innovation":83},
  "ElevenLabs":              {"popularity":88, "performance":88, "cost":75, "privacy":78, "innovation":82},
  "Udio AI":                 {"popularity":80, "performance":78, "cost":85, "privacy":65, "innovation":78},

  # Multi-Modal / Agentic
  "GPT-4o (OpenAI)":         {"popularity":95, "performance":92, "cost":70, "privacy":70, "innovation":92},
  "Gemini 1.5 Ultra":        {"popularity":84, "performance":88, "cost":78, "privacy":80, "innovation":88},
  "Claude 3 Opus":           {"popularity":82, "performance":94, "cost":75, "privacy":85, "innovation":86},
}

WEIGHTS = {"popularity":0.40, "performance":0.25, "cost":0.10, "privacy":0.10, "innovation":0.15}

# ---------- Utilities ----------
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

def load_overrides():
  if not os.path.exists(OVERRIDES_PATH):
    return {}
  try:
    with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return {}

def score_for(tool_name, overrides):
  # Merge DEFAULTS + overrides (tool exact name match)
  base = deepcopy(DEFAULTS.get(tool_name, {}))
  ov = overrides.get(tool_name, {})
  base.update({k:v for k,v in ov.items() if k in WEIGHTS})
  # Fill missing keys with conservative mid values
  for k in WEIGHTS:
    base.setdefault(k, 70)
  # Weighted sum
  return sum(base[k]*WEIGHTS[k] for k in WEIGHTS)

def ordinal(n):
  return {1:"1st", 2:"2nd", 3:"3rd"}.get(n, f"{n}th")

# ---------- Main ----------
def main():
  # Load leaderboard
  with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

  # 1) Update timestamp (UTC; your page prints as-is)
  data["timestamp"] = datetime.now(timezone.utc).strftime("%B %d, %Y – %I:%M %p UTC")

  # 2) Update Top 5 news (best-effort)
  pool = []
  for u in FEEDS:
    xml = fetch(u)
    time.sleep(0.5)
    pool.extend(parse_feed(xml))

  ranked = []
  for (title, link, pub, desc) in pool:
    if not title or not link:
      continue
    ranked.append((1 if looks_relevant(title, desc) else 0, title, link, pub, desc))
  ranked.sort(key=lambda x: x[0], reverse=True)

  news = []
  seen = set()
  for _, t, link, pub, desc in ranked:
    if (t, link) in seen:
      continue
    seen.add((t, link))
    news.append(to_news_obj(t, link, pub, desc))
    if len(news) >= MAX_NEWS:
      break
  if news:
    data["news"] = news

  # 3) Re-score + re-rank tools in each category
  overrides = load_overrides()
  for category in data.get("categories", []):
    rows = category.get("rows", [])
    # Compute scores
    scored = []
    for row in rows:
      tool = row.get("tool", "")
      s = score_for(tool, overrides)
      scored.append((s, row))
    # Sort high->low
    scored.sort(key=lambda x: x[0], reverse=True)
    # Re-assign rank strings to top N
    new_rows = []
    for i, (_, row) in enumerate(scored, start=1):
      row = dict(row)  # shallow copy
      row["rank"] = ordinal(i)
      new_rows.append(row)
    category["rows"] = new_rows

  # Save back
  with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
  main()
