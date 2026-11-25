"""The Roman Catechism (Catechism of the Council of Trent) from the Internet Archive.

English: McHugh & Callan (1923) or Donovan (1829) translations; Latin: Catechismus
Romanus. The best-matching public-domain scan with an OCR text layer is chosen; pass
an explicit archive.org identifier to override (credo-library fetch catechism --id X).
"""
import json
import urllib.parse

from . import db, netutil

SEARCH = "https://archive.org/advancedsearch.php"
QUERIES = {
    "en": 'title:("catechism of the council of trent") AND mediatype:texts AND date:[1800-01-01 TO 1962-12-31]',
    "la": 'title:("catechismus romanus" OR "catechismus ex decreto concilii tridentini") AND mediatype:texts',
}


def candidates(lang, rows=15):
    q = urllib.parse.urlencode({"q": QUERIES[lang], "fl[]": ["identifier", "title", "date", "downloads"],
                                "sort[]": "downloads desc", "rows": rows, "output": "json"}, doseq=True)
    data = json.loads(netutil.fetch_text(f"{SEARCH}?{q}"))
    return data.get("response", {}).get("docs", [])


def text_file(identifier):
    meta = json.loads(netutil.fetch_text(f"https://archive.org/metadata/{identifier}"))
    for f in meta.get("files", []):
        if f.get("name", "").endswith("_djvu.txt"):
            return meta.get("metadata", {}), f["name"]
    return meta.get("metadata", {}), None


def fetch_one(conn, identifier, lang, log=print):
    md, name = text_file(identifier)
    if not name:
        return False
    url = f"https://archive.org/download/{identifier}/{urllib.parse.quote(name)}"
    if db.has_source(conn, url):
        log(f"  already have {identifier}")
        return True
    text = netutil.fetch(url, delay=1.0).decode("utf-8", errors="replace")
    title = md.get("title") or identifier
    if isinstance(title, list):
        title = title[0]
    date = md.get("date")
    db.upsert(conn, collection="catechism", author="Council of Trent", title=title,
              date=str(date)[:10] if date else None, lang=lang, ref=f"ia:{identifier}",
              source=url, body_html=netutil.plaintext_to_html(text), body_text=text)
    conn.commit()
    log(f"  {lang}: {title} ({identifier})")
    return True


def run(conn, identifier=None, log=print):
    log("Roman Catechism")
    if identifier:
        return int(fetch_one(conn, identifier, "en", log))
    total = 0
    for lang in ("en", "la"):
        for c in candidates(lang):
            try:
                if fetch_one(conn, c["identifier"], lang, log):
                    total += 1
                    break
            except Exception as e:
                log(f"  skipped {c['identifier']}: {e}")
    return total
