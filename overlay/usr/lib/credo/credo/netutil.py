"""Polite HTTP fetching and HTML-to-paragraph extraction (stdlib only)."""
import html
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

USER_AGENT = "CredoOS-Library/1.0 (personal offline library; polite crawler)"
_last = {}


def fetch(url, delay=1.0, timeout=60, retries=3):
    """GET url; returns bytes, or None on 404. Waits `delay` seconds between hits per host."""
    host = urllib.parse.urlparse(url).netloc
    wait = delay - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            _last[host] = time.time()
            return data
        except urllib.error.HTTPError as e:
            _last[host] = time.time()
            if e.code in (403, 404, 410):
                return None
            if attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries - 1:
                raise
        time.sleep(3 * (attempt + 1))
    return None


def fetch_text(url, **kw):
    data = fetch(url, **kw)
    if data is None:
        return None
    m = re.search(rb'charset=["\']?([\w-]+)', data[:2000])
    enc = m.group(1).decode() if m else "utf-8"
    try:
        return data.decode(enc, errors="replace")
    except LookupError:
        return data.decode("utf-8", errors="replace")


class ParagraphExtractor(HTMLParser):
    """Collects text of block elements, skipping navigation, scripts and styles."""
    BLOCKS = {"p", "h1", "h2", "h3", "h4", "h5", "blockquote", "li", "td"}
    SKIP = {"script", "style", "nav", "header", "footer", "noscript", "form", "select", "button"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.title = ""
        self._skip = 0
        self._cur = None
        self._buf = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCKS and not self._skip:
            self._flush()
            self._cur = tag
        elif tag == "br" and self._cur:
            self._buf.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == self._cur:
            self._flush()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._cur and not self._skip:
            self._buf.append(data)

    def _flush(self):
        if self._cur:
            text = re.sub(r"[ \t\r\f\v]+", " ", "".join(self._buf)).strip()
            if text:
                self.blocks.append((self._cur, text))
        self._cur, self._buf = None, []

    def close(self):
        super().close()
        self._flush()


def extract(html_text):
    p = ParagraphExtractor()
    p.feed(html_text)
    p.close()
    return p.title.strip(), p.blocks


def blocks_to_html(blocks):
    out = []
    for tag, text in blocks:
        t = "p" if tag in ("li", "td", "blockquote") else tag
        body = html.escape(text).replace("\n", "<br>")
        out.append(f"<{t}>{body}</{t}>")
    return "\n".join(out)


def plaintext_to_html(text):
    """Turn hard-wrapped plain text into paragraphs."""
    paras = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        lines = [l.strip() for l in p.split("\n")]
        short = len(lines) > 1 and max(len(l) for l in lines) < 50   # verse / headings
        joined = "<br>".join(html.escape(l) for l in lines) if short else html.escape(" ".join(lines))
        if len(lines) == 1 and len(p) < 70 and (p.isupper() or re.match(r"^(CHAPTER|BOOK|PART|ARTICLE|QUESTION)\b", p, re.I)):
            out.append(f"<h3>{joined}</h3>")
        else:
            out.append(f"<p>{joined}</p>")
    return "\n".join(out)
