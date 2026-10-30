#!/usr/bin/env python3
"""Щоденний пошук можливостей для лікарні.

Джерела (усе задається в config.json):
  feeds         RSS/Atom-стрічки сайтів
  news_queries  пошукові запити Google News
  pages         звичайні сторінки установ і донорів: скрипт шукає на них нові посилання
  telegram      публічні Telegram-канали (читаються через t.me/s/<назва>)

Запис потрапляє в результат, лише якщо в ньому є І медична тема (topic),
І ознака можливості (kind: грант, конкурс, навчання, партнерство, обладнання тощо)
і немає слів із exclude. Уже бачені записи (seen.json) пропускаються.

Результати:
  digest.md       текст листа (порожній, якщо нового немає)
  docs/data.json  історія знахідок
  docs/index.html дашборд (публікується через GitHub Pages)

Лише стандартна бібліотека Python.
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import build_dashboard

try:
    from zoneinfo import ZoneInfo
    KYIV = ZoneInfo("Europe/Kyiv")
except Exception:  # старі системи без бази часових поясів
    KYIV = dt.timezone(dt.timedelta(hours=2))

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "config.json")
SEEN = os.path.join(HERE, "seen.json")
DIGEST = os.path.join(HERE, "digest.md")
DOCS = os.path.join(HERE, "docs")
DATA = os.path.join(DOCS, "data.json")
INDEX = os.path.join(DOCS, "index.html")
UA = "Mozilla/5.0 (compatible; hospital-opportunities-bot/3.0)"

CATEGORIES = {
    "eu": "Horizon Europe та програми ЄС",
    "partnership": "Партнерства й консорціуми",
    "training": "Навчання, стажування, курси",
    "grant": "Гранти й конкурси",
    "aid": "Допомога організацій",
    "other": "Інше",
}
CATEGORY_WORDS = [
    ("eu", ["horizon", "eu4health", "erasmus", "горизонт європ", "eit health", "євросоюз", "european commission", "єврокомісі", "creative europe"]),
    ("partnership", ["partner search", "partnership", "пошук партнер", "партнерств", "consortium", "консорціум", "twinning", "побратим", "expression of interest"]),
    ("training", ["навчан", "курс", "тренінг", "майстер", "стажу", "internship", "fellowship", "masterclass", "master class", "course", "training", "webinar", "вебінар", "стипенд", "scholarship"]),
    ("grant", ["грант", "конкурс", "call for", "funding", "фінансув", "grant", "заявк"]),
    ("aid", ["передал", "передав", "гуманітарн", "donat", "humanitarian", "допомог"]),
]


def norm(text):
    text = (text or "").lower()
    for ch in ("’", "ʼ", "`", "‘"):
        text = text.replace(ch, "'")
    return text


def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


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


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


# ---------- парсери джерел ----------

def parse_feed(data):
    """RSS 2.0 або Atom -> [{title, link, date, summary}]"""
    root = ET.fromstring(data)
    out = []
    for node in root.iter():
        if local(node.tag) not in ("item", "entry"):
            continue
        link = child_text(node, "link")
        if not link:
            for ch in node:
                if local(ch.tag) == "link" and ch.get("href"):
                    link = ch.get("href")
                    break
        out.append({
            "title": strip_tags(child_text(node, "title")),
            "link": link,
            "date": parse_date(child_text(node, "pubDate", "published", "updated", "date")),
            "summary": strip_tags(child_text(node, "description", "summary", "content", "encoded")),
        })
    return out


class LinkParser(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.links, self._href, self._buf = base, [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._buf = []

    def handle_data(self, data):
        if self._href is not None:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text and not self._href.startswith(("#", "javascript:", "mailto:", "tel:")):
                self.links.append((urllib.parse.urljoin(self.base, self._href), text))
            self._href = None


def parse_page(data, url):
    """Звичайна HTML-сторінка -> посилання з достатньо довгим текстом."""
    p = LinkParser(url)
    p.feed(data.decode("utf-8", "replace"))
    seen, out = set(), []
    for link, text in p.links:
        if len(text) < 20 or link in seen:
            continue
        seen.add(link)
        out.append({"title": text, "link": link, "date": None, "summary": ""})
    return out


def parse_telegram(data, channel):
    """Публічний канал t.me/s/<назва> -> повідомлення."""
    page = data.decode("utf-8", "replace")
    out = []
    for block in page.split("tgme_widget_message_wrap")[1:]:
        m_link = re.search(r'class="tgme_widget_message_date"\s+href="([^"]+)"', block)
        m_text = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        m_time = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        if not m_link or not m_text:
            continue
        text = strip_tags(m_text.group(1))
        out.append({
            "title": text[:140] + ("…" if len(text) > 140 else ""),
            "link": html.unescape(m_link.group(1)),
            "date": parse_date(m_time.group(1)) if m_time else None,
            "summary": text,
        })
    return out


# ---------- фільтр і категорії ----------

def make_filter(cfg):
    topic = [norm(k) for k in cfg.get("topic", [])]
    kind = [norm(k) for k in cfg.get("kind", [])]
    excl = [norm(k) for k in cfg.get("exclude", [])]

    def ok(item):
        text = norm(item["title"] + " " + item["summary"])
        if topic and not any(k in text for k in topic):
            return False
        if kind and not any(k in text for k in kind):
            return False
        return not any(k in text for k in excl)
    return ok


def categorize(item):
    text = norm(item["title"] + " " + item["summary"])
    # слово має починатися з ключової основи (щоб «курс» не знаходився всередині «конкурс»)
    for cat, words in CATEGORY_WORDS:
        for w in words:
            if re.search(r"(?<![а-яіїєґa-z0-9])" + re.escape(w), text):
                return cat
    return "other"


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def main():
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    seen = list(load_json(SEEN, []))
    seen_set = set(seen)

    ok = make_filter(cfg)
    max_age = dt.timedelta(days=int(cfg.get("max_age_days", 21)))
    now = dt.datetime.now(dt.timezone.utc)
    now_kyiv = now.astimezone(KYIV)
    today = now_kyiv.date().isoformat()

    sources = []  # (назва, url, парсер)
    for f_ in cfg.get("feeds", []):
        sources.append((f_["name"], f_["url"], parse_feed))
    for q in cfg.get("news_queries", []):
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:21d", "hl": "uk", "gl": "UA", "ceid": "UA:uk"})
        sources.append(("Новини: " + q, url, parse_feed))
    for p in cfg.get("pages", []):
        sources.append((p["name"], p["url"], lambda d, u=p["url"]: parse_page(d, u)))
    for ch in cfg.get("telegram", []):
        ch = ch.lstrip("@")
        sources.append(("Telegram: @" + ch, "https://t.me/s/" + ch, lambda d, c=ch: parse_telegram(d, c)))

    found, failed = [], []
    for name, url, parser in sources:
        try:
            items = parser(fetch(url))
        except Exception as e:  # одна зламана стрічка не має зупиняти решту
            failed.append({"name": name, "error": str(e)[:120]})
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
            if not ok(it):
                continue
            it["source"] = name
            it["category"] = categorize(it)
            found.append(it)

    found.sort(key=lambda i: i["date"] or now, reverse=True)

    # --- лист ---
    lines = []
    if found:
        lines.append("Нові записи, що підходять (%d):\n" % len(found))
        for it in found:
            d = it["date"].strftime("%d.%m.%Y") if it["date"] else "дата невідома"
            snippet = it["summary"][:180] + ("…" if len(it["summary"]) > 180 else "") if it["summary"] and it["summary"] != it["title"] else ""
            lines.append("- **[%s](%s)**  \n  %s · %s · %s%s" % (
                it["title"] or "Без назви", it["link"], CATEGORIES[it["category"]], d, it["source"], ("  \n  " + snippet) if snippet else ""))
        lines.append("\nПеревіряйте дедлайн, умови й те, чи може ваш заклад бути заявником.")
    with open(DIGEST, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))

    # --- історія й дашборд ---
    data = load_json(DATA, {})
    items = data.get("items", [])
    for it in found:
        items.append({
            "title": it["title"], "link": it["link"], "source": it["source"], "category": it["category"],
            "date": it["date"].date().isoformat() if it["date"] else "", "first_seen": today,
            "snippet": it["summary"][:200] if it["summary"] and it["summary"] != it["title"] else "",
        })
    items.sort(key=lambda i: (i["first_seen"], i.get("date", "")), reverse=True)
    data = {
        "updated": now_kyiv.strftime("%d.%m.%Y %H:%M") + " за Києвом",
        "today": today,
        "categories": CATEGORIES,
        "items": items[:1500],
        "failed": failed,
    }
    os.makedirs(DOCS, exist_ok=True)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(build_dashboard.build(data))

    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(seen[-8000:], f, ensure_ascii=False, indent=0)
    print("Знайдено:", len(found), "· збоїв:", len(failed))


if __name__ == "__main__":
    main()
