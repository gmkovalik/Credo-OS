"""Papal documents before the Second Vatican Council, from vatican.va (English + Latin).

Covers Leo XIII through John XXIII up to 11 October 1962 (opening of the Council),
plus whatever vatican.va holds for Pius IX. Documents are fetched once and stored
locally for personal offline study.
"""
import re

from . import db, netutil

BASE = "https://www.vatican.va"
POPES = [
    ("pius-ix", "Pius IX"),
    ("leo-xiii", "Leo XIII"),
    ("pius-x", "Pius X"),
    ("benedict-xv", "Benedict XV"),
    ("pius-xi", "Pius XI"),
    ("pius-xii", "Pius XII"),
    ("john-xxiii", "John XXIII"),
]
CATEGORIES = ["encyclicals", "apost_constitutions", "apost_exhortations", "apost_letters",
              "motu_proprio", "bulls", "briefs", "letters", "messages", "speeches",
              "homilies", "prayers", "documents"]
CUTOFF = "19621011"
LANGS = ["en", "la"]
NOISE = re.compile(r"copyright|libreria editrice vaticana|dicastero per la comunicazione|"
                   r"©|top of page|^\s*\[?(english|italiano|latine|français|deutsch|español|português)\]?\s*$",
                   re.I)


def _date_from_name(name):
    m = re.search(r"_(\d{8})_", name)
    if not m:
        return None
    s = m.group(1)
    # vatican.va uses both ddmmyyyy and yyyymmdd in file names
    if s[:2] in ("18", "19", "20") and int(s[4:6]) <= 12:
        y, mo, d = s[:4], s[4:6], s[6:]
    else:
        d, mo, y = s[:2], s[2:4], s[4:]
    return f"{y}-{mo}-{d}"


def index_links(slug, lang, cat, log=print):
    links, seen = [], set()
    pat = re.compile(rf'href="((?:https?://www\.vatican\.va)?/content/{re.escape(slug)}/{lang}/'
                     rf'{re.escape(cat)}/documents/[^"#?]+\.html)"')
    for n in range(1, 80):
        url = f"{BASE}/content/{slug}/{lang}/{cat}.index.html" if n == 1 else \
              f"{BASE}/content/{slug}/{lang}/{cat}.index.{n}.html"
        page = netutil.fetch_text(url)
        if page is None:
            break
        new = 0
        for href in pat.findall(page):
            href = href if href.startswith("http") else BASE + href
            if href not in seen:
                seen.add(href)
                links.append(href)
                new += 1
        if new == 0:
            break
    if links:
        log(f"  {slug}/{lang}/{cat}: {len(links)} documents")
    return links


def fetch_doc(conn, url, pope, lang):
    if db.has_source(conn, url):
        return False
    page = netutil.fetch_text(url)
    if not page:
        return False
    title, blocks = netutil.extract(page)
    blocks = [(t, x) for t, x in blocks if not NOISE.search(x)]
    body_text = "\n\n".join(x for _, x in blocks)
    if len(body_text) < 300:
        return False
    name = url.rsplit("/", 1)[-1]
    date = _date_from_name(name)
    title = re.sub(r"\s*\|\s*.*$", "", title).strip() or name
    db.upsert(conn, collection="papal", author=pope, title=title, date=date, lang=lang,
              ref="vat:" + name, source=url, body_html=netutil.blocks_to_html(blocks),
              body_text=body_text)
    return True


def run(conn, popes=None, langs=None, log=print):
    total = 0
    for slug, name in POPES:
        if popes and slug not in popes:
            continue
        log(f"Papal documents: {name}")
        for lang in langs or LANGS:
            for cat in CATEGORIES:
                for url in index_links(slug, lang, cat, log):
                    d = _date_from_name(url.rsplit("/", 1)[-1]) or ""
                    if d and d.replace("-", "") >= CUTOFF:
                        continue
                    try:
                        if fetch_doc(conn, url, name, lang):
                            total += 1
                            if total % 25 == 0:
                                conn.commit()
                                log(f"    {total} new documents")
                    except Exception as e:  # keep going on individual failures
                        log(f"    skipped {url}: {e}")
        conn.commit()
    log(f"Papal documents: {total} new")
    return total
