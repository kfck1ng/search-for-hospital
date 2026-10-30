#!/usr/bin/env python3
"""Щотижневий пошук можливостей для лікарні.

Читає RSS/Atom-стрічки та пошукові запити Google News з config.json,
лишає записи, що містять ключові слова про охорону здоров'я, пропускає вже
бачені (seen.json) і пише digest.md. Якщо digest.md не порожній, workflow
створює з нього Issue на GitHub, а GitHub надсилає лист.

Лише стандартна бібліотека Python, нічого встановлювати не треба.
"""
import datetime as dt
import email.utils
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
SEEN = os.path.join(HERE, "seen.json")
DIGEST = os.path.join(HERE, "digest.md")
UA = "Mozilla/5.0 (compatible; hospital-opportunities-bot/1.0)"


def norm(text):
    text = (text or "").lower()
    for ch in ("’", "ʼ", "`", "‘"):
        text = text.replace(ch, "'")
    return text


def local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child_text(node, *names):
    for ch in node:
        if local(ch.tag) in names and (ch.text or "").strip():
            return ch.text.strip()
    return ""


def parse_date(value):
    if not value:
        return None
    try:
        d = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        d = None
    if d is None:
        try:
            d = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def parse_feed(data):
    """Повертає список {title, link, date, summary} з RSS 2.0 або Atom."""
    root = ET.fromstring(data)
    out = []
    for node in root.iter():
        name = local(node.tag)
        if name not in ("item", "entry"):
            continue
        link = child_text(node, "link")
        if not link:  # Atom: <link href="..."/>
            for ch in node:
                if local(ch.tag) == "link" and ch.get("href"):
                    link = ch.get("href")
                    break
        out.append({
            "title": child_text(node, "title"),
            "link": link,
            "date": parse_date(child_text(node, "pubDate", "published", "updated", "date")),
            "summary": child_text(node, "description", "summary", "content", "encoded"),
        })
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    try:
        with open(SEEN, encoding="utf-8") as f:
            seen = list(json.load(f))
    except (OSError, ValueError):
        seen = []
    seen_set = set(seen)

    include = [norm(k) for k in cfg.get("include", [])]
    exclude = [norm(k) for k in cfg.get("exclude", [])]
    max_age = dt.timedelta(days=int(cfg.get("max_age_days", 21)))
    now = dt.datetime.now(dt.timezone.utc)

    feeds = [(f["name"], f["url"]) for f in cfg.get("feeds", [])]
    for q in cfg.get("news_queries", []):
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:21d", "hl": "uk", "gl": "UA", "ceid": "UA:uk"})
        feeds.append(("Google News: " + q, url))

    found, failed = [], []
    for name, url in feeds:
        try:
            items = parse_feed(fetch(url))
        except Exception as e:  # одна зламана стрічка не має зупиняти решту
            failed.append((name, str(e)[:120]))
            print("ПОМИЛКА", name, e, file=sys.stderr)
            continue
        print("OK", name, len(items), "записів")
        for it in items:
            key = it["link"] or it["title"]
            if not key or key in seen_set:
                continue
            seen_set.add(key)
            seen.append(key)
            if it["date"] and now - it["date"] > max_age:
                continue
            text = norm(it["title"] + " " + it["summary"])
            if include and not any(k in text for k in include):
                continue
            if any(k in text for k in exclude):
                continue
            it["source"] = name
            found.append(it)

    found.sort(key=lambda i: i["date"] or now, reverse=True)

    lines = []
    if found:
        lines.append("Нові записи, що підходять за ключовими словами (%d):\n" % len(found))
        for it in found:
            d = it["date"].strftime("%d.%m.%Y") if it["date"] else "дата невідома"
            lines.append("- **[%s](%s)**  \n  %s · %s" % (it["title"] or "Без назви", it["link"], d, it["source"]))
        lines.append("\nПеревіряйте дедлайн і умови на сторінці джерела. Цікаві записи додайте в трекер.")
    if failed:
        lines.append("\nНе вдалося прочитати стрічки:")
        for name, err in failed:
            lines.append("- %s (%s)" % (name, err))
    with open(DIGEST, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))

    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(seen[-5000:], f, ensure_ascii=False, indent=0)
    print("Знайдено:", len(found), "· збоїв:", len(failed))


if __name__ == "__main__":
    main()
