"""Writings of the saints (and the Douay-Rheims Bible) from Project Gutenberg.

Uses Gutenberg's official catalog (pg_catalog.csv.gz) and selects every English or
Latin text whose author is listed as a Saint, a pre-Conciliar Pope, or a short list
of classic Catholic authors, keeping only authors who died before 1966.
All of these texts are public domain in the USA.
"""
import csv
import gzip
import io
import re

from . import config, db, netutil

CATALOG = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv.gz"
TEXT_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
EXTRA_AUTHORS = re.compile(r"Thomas, à Kempis|Kempis, Thomas|Challoner, Richard|Faber, Frederick William|"
                           r"Scupoli, Lorenzo|Garrigou-Lagrange|Chesterton, G\. K\.|Pius ", re.I)
SAINT = re.compile(r",\s*Saint\b|\bSaint,|,\s*Blessed\b")
POPE = re.compile(r",\s*Pope\b")
SCRIPTURE_TITLE = re.compile(r"Douay|Rheims|Vulgate|Biblia Sacra", re.I)


def _years(authors):
    return [int(y) for y in re.findall(r"\b(1\d{3}|[2-9]\d{2})\b", authors)]


def select(rows):
    for r in rows:
        if r.get("Type") != "Text":
            continue
        langs = set((r.get("Language") or "").split("; "))
        if not langs & {"en", "la"}:
            continue
        a, t = r.get("Authors") or "", r.get("Title") or ""
        if SCRIPTURE_TITLE.search(t) and ("Bible" in t or "Biblia" in t):
            yield r, "scripture"
            continue
        if not (SAINT.search(a) or POPE.search(a) or EXTRA_AUTHORS.search(a)):
            continue
        ys = _years(a)
        if ys and max(ys) > 1965:
            continue
        coll = "papal" if POPE.search(a) and not SAINT.search(a) else "saints"
        yield r, coll


def strip_boilerplate(text):
    s = re.search(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I | re.S)
    e = re.search(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG", text, re.I)
    if s:
        text = text[s.end():e.start() if e else None]
    return text.strip()


def clean_author(a):
    first = a.split(";")[0]
    first = re.sub(r",?\s*(approximately\s+)?\d{3,4}\??-\d{0,4}\??", "", first)
    first = re.sub(r"\s*\[.*?\]", "", first)
    return first.strip(" ,")


def run(conn, limit=None, log=print):
    log("Saints: downloading the Project Gutenberg catalog")
    raw = netutil.fetch(CATALOG, delay=0)
    rows = csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8"))
    picks = list(select(rows))
    log(f"Saints: {len(picks)} matching books")
    total = 0
    for r, coll in picks[:limit] if limit else picks:
        num = r["Text#"]
        url = TEXT_URL.format(id=num)
        if db.has_source(conn, url):
            continue
        try:
            data = netutil.fetch(url, delay=2.0)
        except Exception as e:
            log(f"  skipped #{num}: {e}")
            continue
        if not data:
            continue
        text = strip_boilerplate(data.decode("utf-8", errors="replace"))
        lang = "la" if "la" in r["Language"].split("; ") and "en" not in r["Language"] else "en"
        db.upsert(conn, collection=coll, author=clean_author(r["Authors"]),
                  title=r["Title"].replace("\n", " "), date=None, lang=lang,
                  ref=f"pg:{num}", source=url, body_html=netutil.plaintext_to_html(text),
                  body_text=text)
        total += 1
        log(f"  [{total}] {clean_author(r['Authors'])}: {r['Title'][:70]}")
        if total % 10 == 0:
            conn.commit()
    conn.commit()
    log(f"Saints: {total} new books")
    return total
