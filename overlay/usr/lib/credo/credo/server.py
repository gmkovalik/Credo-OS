"""Local web UI for the Credo library (http://127.0.0.1:8754, localhost only)."""
import datetime as dt
import html
import http.cookies
import http.server
import re
import threading
import urllib.parse

from . import config, db, i18n, liturgy, pages, palettes

PAGE_SIZE = 25
H = html.escape


def css():
    try:
        variant = config.load().get("appearance", "variant")
        _, p = palettes.resolve(variant)
    except Exception:
        _, p = palettes.resolve("monastic")
    return f"""
:root {{ --bg:{p['bg']}; --alt:{p['bg_alt']}; --view:{p['view']}; --fg:{p['fg']}; --dim:{p['fg_dim']};
        --acc:{p['accent']}; --gold:{p['logo']}; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:17px/1.6 "Noto Serif", "DejaVu Serif", Georgia, serif }}
a {{ color:var(--acc) }} a:hover {{ color:var(--gold) }}
header {{ display:flex; gap:1rem; align-items:center; padding:.7rem 1.4rem; background:var(--alt);
         border-bottom:3px solid var(--acc); flex-wrap:wrap }}
header .brand {{ font-size:1.25rem; letter-spacing:.08em; text-decoration:none; color:var(--fg); font-variant:small-caps;
                display:flex; align-items:center; gap:.5rem }}
header .brand .logo {{ width:30px; height:30px }}
header nav a {{ margin-right:1rem; text-decoration:none }}
header .lang {{ margin-left:auto }}
main {{ max-width:60rem; margin:0 auto; padding:1.4rem }}
form.search {{ display:flex; gap:.5rem; flex-wrap:wrap; margin:1rem 0 }}
input[type=search] {{ flex:1; min-width:14rem; padding:.6rem .8rem; font:inherit; border:1px solid var(--dim);
                      background:var(--view); color:var(--fg); border-radius:6px }}
select, button {{ font:inherit; padding:.5rem; border-radius:6px; border:1px solid var(--dim); background:var(--view); color:var(--fg) }}
button {{ background:var(--acc); color:#fff; border:none; padding:.5rem 1.1rem; cursor:pointer }}
.card {{ background:var(--view); border:1px solid var(--alt); border-left:5px solid var(--acc); border-radius:8px;
         padding:1rem 1.2rem; margin:1rem 0 }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(15rem, 1fr)); gap:1rem }}
.grid a.card {{ display:block; text-decoration:none; color:var(--fg); margin:0 }}
.muted {{ color:var(--dim); font-size:.9rem }}
.dot {{ display:inline-block; width:.8em; height:.8em; border-radius:50%; border:1px solid var(--dim); vertical-align:middle }}
.hit {{ margin:1.1rem 0 }} .hit mark {{ background:var(--gold); color:#000; padding:0 .1em }}
article p {{ text-align:justify }} article h1 {{ font-variant:small-caps; letter-spacing:.04em }}
.cols {{ display:grid; grid-template-columns:1fr 1fr; gap:1.6rem }}
@media (max-width:900px) {{ .cols {{ grid-template-columns:1fr }} }}
.mass-part h3 {{ color:var(--acc); font-variant:small-caps; margin:1.2rem 0 .3rem; border-bottom:1px solid var(--alt) }}
.cit {{ font-style:italic; color:var(--dim); font-size:.9rem }} .macro {{ font-style:italic }}
.vr {{ margin:.2rem 0 }}
.rubric {{ font-style:italic; color:#a11; font-size:.9rem }}
table {{ border-collapse:collapse; width:100% }} td, th {{ padding:.35rem .5rem; border-bottom:1px solid var(--alt); text-align:left }}
.pager {{ display:flex; gap:1rem; margin:1.5rem 0 }}
"""


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CredoLibrary/1.0"

    # ---------------------------------------------------------- plumbing
    def log_message(self, fmt, *args):
        pass

    @property
    def conn(self):
        local = self.server.local
        if not hasattr(local, "conn"):
            local.conn = db.connect()
        return local.conn

    def lang(self):
        c = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        if "credo_lang" in c and c["credo_lang"].value in ("en", "la"):
            return c["credo_lang"].value
        return config.language()

    def t(self, key):
        return i18n.t(key, self.lang())

    def send(self, body, status=200, ctype="text/html; charset=utf-8", headers=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def page(self, title, body, body_attrs=""):
        L = self.lang()
        other = "la" if L == "en" else "en"
        back = urllib.parse.quote(self.path, safe="")
        nav = "".join(f'<a href="{u}">{self.t(k)}</a>' for u, k in (
            ("/today", "today"), ("/mass", "mass_day"), ("/rosary", "rosary"), ("/prayers", "prayers"),
            ("/", "library"), ("/calendar", "calendar"), ("/examen", "examen")))
        logo = H(config.load().get("appearance", "logo", fallback="chirho"))
        return self.send(f"""<!doctype html><html lang="{L}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="/static/logo/{logo}.svg">
<title>{H(title)} · Credo</title><style>{css()}</style></head><body {body_attrs}>
<header><a class="brand" href="/today"><img src="/static/logo/{logo}.svg" alt="" class="logo"> Credo</a><nav>{nav}</nav>
<a class="lang" href="/lang?set={other}&back={back}">{'Latine' if other == 'la' else 'English'}</a></header>
<main>{body}</main></body></html>""")

    def search_form(self, q="", coll="", dlang=""):
        opts = f'<option value="">{self.t("all")}</option>' + "".join(
            f'<option value="{k}"{" selected" if k == coll else ""}>{H(v[1 if self.lang() == "la" else 0])}</option>'
            for k, v in db.COLLECTIONS.items())
        lopts = "".join(f'<option value="{k}"{" selected" if k == dlang else ""}>{H(n)}</option>'
                        for k, n in (("", self.t("any_lang")), ("en", self.t("english")), ("la", self.t("latin"))))
        return (f'<form class="search" action="/search"><input type="search" name="q" value="{H(q)}" '
                f'placeholder="{H(self.t("search_ph"))}" autofocus><select name="c">{opts}</select>'
                f'<select name="l">{lopts}</select><button>{self.t("search")}</button></form>')

    # ---------------------------------------------------------- routes
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        qs = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self.home()
            if u.path == "/search":
                return self.search(qs)
            if u.path.startswith("/c/"):
                return self.collection(u.path[3:], qs)
            m = re.fullmatch(r"/d/(\d+)", u.path)
            if m:
                return self.document(int(m.group(1)))
            if u.path == "/mass":
                return self.mass(qs)
            if u.path == "/ordo":
                return self.ordo()
            if u.path == "/calendar":
                return self.calendar(qs)
            if u.path == "/today":
                return pages.today(self)
            if u.path == "/rosary":
                return pages.rosary(self, qs)
            if u.path == "/prayers":
                return pages.prayers(self)
            if u.path == "/examen":
                return pages.examen(self)
            if u.path == "/static/rosary.js":
                return self.send(pages.ROSARY_JS, ctype="text/javascript; charset=utf-8")
            m = re.fullmatch(r"/static/logo/([a-z]+)\.svg", u.path)
            if m and m.group(1) in palettes.LOGOS:
                return self.logo(m.group(1))
            if u.path == "/lang":
                lang = qs.get("set", "en")
                back = qs.get("back", "/")
                if not back.startswith("/") or back.startswith("//"):
                    back = "/"
                lang = lang if lang in ("en", "la") else "en"
                return self.send("", 303, headers={"Location": back,
                                                   "Set-Cookie": f"credo_lang={lang}; Path=/; SameSite=Strict"})
            if u.path == "/health":
                return self.send("ok", ctype="text/plain")
            self.page("404", "<h1>404</h1>")
        except BrokenPipeError:
            pass

    def logo(self, name):
        try:
            variant = config.load().get("appearance", "variant")
            _, p = palettes.resolve(variant)
        except Exception:
            _, p = palettes.resolve("monastic")
        svg = (config.SHARE / "logos" / f"{name}.svg").read_text(encoding="utf-8")
        self.send(svg.replace("currentColor", p["accent"]), ctype="image/svg+xml",
                  headers={"Cache-Control": "max-age=300"})

    def today_card(self):
        L = self.lang()
        d = liturgy.today()
        feast = d.feast(L)
        title = feast or d.title(L)
        extra = f'<div class="muted">{H(d.title(L))}</div>' if feast else ""
        notes = f' · {H(", ".join(d.notes))}' if d.notes else ""
        return (f'<div class="card"><div class="muted">{self.t("today")} · {d.date.isoformat()}</div>'
                f'<h2 style="margin:.2rem 0">{H(title)}</h2>{extra}'
                f'<div><span class="dot" style="background:{d.color_hex}"></span> {H(d.season_name(L))} · '
                f'{H(d.color)}{notes}</div><p><a href="/mass">{self.t("mass_day")} →</a></p></div>')

    def home(self):
        L = self.lang()
        st = db.stats(self.conn)
        cards = []
        for k, (en, la) in db.COLLECTIONS.items():
            n = sum(st.get(k, {}).values())
            if n or k != "imported":
                cards.append(f'<a class="card" href="/c/{k}"><strong>{H(la if L == "la" else en)}</strong>'
                             f'<div class="muted">{n} {self.t("documents")}</div></a>')
        empty = "" if st else f'<div class="card">{H(self.t("empty"))}</div>'
        self.page(self.t("library"), f"""{self.search_form()}{self.today_card()}{empty}
<h2>{self.t('collections')}</h2><div class="grid">{''.join(cards)}</div>""")

    def search(self, qs):
        q = qs.get("q", "").strip()
        coll, dlang = qs.get("c", ""), qs.get("l", "")
        page = max(1, int(qs.get("p", "1") or 1))
        body = self.search_form(q, coll, dlang)
        if not q:
            return self.page(self.t("search"), body)
        # Treat user input as plain terms (quote each) so FTS syntax errors are impossible.
        terms = [w for w in re.findall(r"\w+", q, re.UNICODE)]
        if not terms:
            return self.page(self.t("search"), body)
        match = " ".join(f'"{w}"' for w in terms)
        where, args = ["docs_fts MATCH ?"], [match]
        if coll:
            where.append("d.collection = ?"); args.append(coll)
        if dlang:
            where.append("d.lang = ?"); args.append(dlang)
        sql_where = " AND ".join(where)
        total = self.conn.execute(f"SELECT COUNT(*) FROM docs_fts JOIN docs d ON d.id = docs_fts.rowid "
                                  f"WHERE {sql_where}", args).fetchone()[0]
        rows = self.conn.execute(
            f"""SELECT d.id, d.title, d.author, d.date, d.lang, d.collection,
                       snippet(docs_fts, 2, '\x01', '\x02', ' … ', 28) AS snip
                FROM docs_fts JOIN docs d ON d.id = docs_fts.rowid
                WHERE {sql_where} ORDER BY bm25(docs_fts, 8.0, 3.0, 1.0) LIMIT ? OFFSET ?""",
            args + [PAGE_SIZE, (page - 1) * PAGE_SIZE]).fetchall()
        items = []
        for r in rows:
            snip = H(r["snip"] or "").replace("\x01", "<mark>").replace("\x02", "</mark>")
            meta = " · ".join(H(x) for x in (r["author"], r["date"], (r["lang"] or "").upper()) if x)
            items.append(f'<div class="hit"><a href="/d/{r["id"]}"><strong>{H(r["title"])}</strong></a>'
                         f'<div class="muted">{meta}</div><div>{snip}</div></div>')
        body += f'<p class="muted">{total} {self.t("results")}</p>' + ("".join(items) or f"<p>{self.t('no_results')}</p>")
        body += self.pager(page, total, {"q": q, "c": coll, "l": dlang}, "/search")
        self.page(q, body)

    def pager(self, page, total, params, base):
        out = []
        if page > 1:
            out.append(f'<a href="{base}?{urllib.parse.urlencode({**params, "p": page - 1})}">← {self.t("prev")}</a>')
        if page * PAGE_SIZE < total:
            out.append(f'<a href="{base}?{urllib.parse.urlencode({**params, "p": page + 1})}">{self.t("next")} →</a>')
        return f'<div class="pager">{"".join(out)}</div>'

    def collection(self, key, qs):
        if key not in db.COLLECTIONS:
            return self.page("404", "<h1>404</h1>")
        L = self.lang()
        name = db.COLLECTIONS[key][1 if L == "la" else 0]
        author = qs.get("a")
        page = max(1, int(qs.get("p", "1") or 1))
        if not author:
            rows = self.conn.execute("SELECT author, COUNT(*) n, MIN(date) first FROM docs WHERE collection=? "
                                     "GROUP BY author ORDER BY first, author", (key,)).fetchall()
            if len(rows) > 1:
                items = "".join(
                    f'<a class="card" href="/c/{key}?{urllib.parse.urlencode({"a": r["author"] or ""})}">'
                    f'<strong>{H(r["author"] or "—")}</strong><div class="muted">{r["n"]} {self.t("documents")}</div></a>'
                    for r in rows)
                return self.page(name, f'<h1>{H(name)}</h1>{self.search_form(coll=key)}<div class="grid">{items}</div>')
        args = [key]
        where = "collection=?"
        if author is not None:
            where += " AND IFNULL(author,'')=?"; args.append(author)
        total = self.conn.execute(f"SELECT COUNT(*) FROM docs WHERE {where}", args).fetchone()[0]
        order = "ref, lang" if key == "missal" else "date, title"
        rows = self.conn.execute(f"SELECT id, title, date, lang FROM docs WHERE {where} ORDER BY {order} "
                                 f"LIMIT ? OFFSET ?", args + [PAGE_SIZE * 4, (page - 1) * PAGE_SIZE * 4]).fetchall()
        trs = "".join(f'<tr><td>{H(r["date"] or "")}</td><td><a href="/d/{r["id"]}">{H(r["title"])}</a></td>'
                      f'<td>{H((r["lang"] or "").upper())}</td></tr>' for r in rows)
        params = {"a": author} if author is not None else {}
        nav = []
        if page > 1:
            nav.append(f'<a href="/c/{key}?{urllib.parse.urlencode({**params, "p": page - 1})}">← {self.t("prev")}</a>')
        if page * PAGE_SIZE * 4 < total:
            nav.append(f'<a href="/c/{key}?{urllib.parse.urlencode({**params, "p": page + 1})}">{self.t("next")} →</a>')
        heading = H(author) if author else H(name)
        self.page(name, f'<h1>{heading}</h1><p class="muted"><a href="/c/{key}">{H(name)}</a> · {total} '
                        f'{self.t("documents")}</p><table>{trs}</table><div class="pager">{"".join(nav)}</div>')

    def document(self, doc_id):
        r = self.conn.execute("SELECT * FROM docs WHERE id=?", (doc_id,)).fetchone()
        if not r:
            return self.page("404", "<h1>404</h1>")
        other = ""
        if r["ref"]:
            o = self.conn.execute("SELECT id, lang FROM docs WHERE ref=? AND lang!=? LIMIT 1",
                                  (r["ref"], r["lang"])).fetchone()
            if o:
                other = f' · <a href="/d/{o["id"]}">{self.t("other_lang")} ({H(o["lang"].upper())})</a>'
        src = r["source"]
        src_link = f'<a href="{H(src)}">{self.t("source")}</a>' if src.startswith("http") else H(src)
        meta = " · ".join(H(x) for x in (r["author"], r["date"], (r["lang"] or "").upper()) if x)
        self.page(r["title"], f'<article><h1>{H(r["title"])}</h1><p class="muted">{meta}{other} · {src_link}</p>'
                              f'{r["body_html"] or ""}</article>')

    def _mass_html(self, ref, lang):
        r = self.conn.execute("SELECT id, title, body_html FROM docs WHERE collection='missal' AND ref=? AND lang=?",
                              (ref, lang)).fetchone()
        if not r:
            return None, None
        return r["title"], r["body_html"]

    def mass(self, qs):
        L = self.lang()
        try:
            d = dt.date.fromisoformat(qs.get("date", "")) if qs.get("date") else dt.date.today()
        except ValueError:
            d = dt.date.today()
        info = liturgy.day_info(d)
        prev_d, next_d = d - dt.timedelta(days=1), d + dt.timedelta(days=1)
        nav = (f'<div class="pager"><a href="/mass?date={prev_d}">← {prev_d}</a>'
               f'<form action="/mass"><input type="date" name="date" value="{d}"> <button>→</button></form>'
               f'<a href="/mass?date={next_d}">{next_d} →</a></div>')
        body = nav + f'<div class="card"><h1 style="margin:.2rem 0">{H(info.feast(L) or info.title(L))}</h1>' \
                     f'<div><span class="dot" style="background:{info.color_hex}"></span> {H(info.season_name(L))}</div></div>'
        groups = []
        if info.temporal:
            # A feria without its own Mass takes the Mass of the preceding Sunday.
            groups.append((self.t("temporal"), [info.temporal, info.temporal.rsplit("-", 1)[0] + "-0"]))
        groups.insert(0 if info.feast_first else len(groups), (self.t("sanctoral"), [info.sanctoral]))
        shown = 0
        for label, candidates in groups:
            for ref in candidates:
                la_t, la_b = self._mass_html(ref, "la")
                en_t, en_b = self._mass_html(ref, "en")
                if la_b or en_b:
                    shown += 1
                    body += (f'<h2>{H(label)}: {H(la_t or en_t)}</h2><div class="cols">'
                             f'<div><h3 class="muted">Latine</h3>{la_b or ""}</div>'
                             f'<div><h3 class="muted">English</h3>{en_b or ""}</div></div>')
                    break
        if not shown:
            body += f'<div class="card">{H(self.t("missing_mass"))}</div>'
        self.page(self.t("mass_day"), body)

    def ordo(self):
        L = self.lang()
        la_t, la_b = self._mass_html("Ordo/Ordo", "la")
        en_t, en_b = self._mass_html("Ordo/Ordo", "en")
        if not la_b:
            return self.page(self.t("ordinary"), f'<div class="card">{H(self.t("missing_mass"))}</div>')
        self.page(self.t("ordinary"), f'<h1>{self.t("ordinary")}</h1><div class="cols"><div>{la_b}</div>'
                                      f'<div>{en_b or ""}</div></div>')

    def calendar(self, qs):
        L = self.lang()
        try:
            year = int(qs.get("y", dt.date.today().year))
        except ValueError:
            year = dt.date.today().year
        rows = []
        for info in liturgy.year_overview(year):
            name = info.feast(L) or info.title(L)
            rows.append(f'<tr><td>{info.date.strftime("%a %d %b")}</td>'
                        f'<td><span class="dot" style="background:{info.color_hex}"></span></td>'
                        f'<td><a href="/mass?date={info.date}">{H(name)}</a></td>'
                        f'<td class="muted">{H(info.season_name(L))}</td></tr>')
        e = liturgy.easter(year)
        self.page(f"{self.t('calendar')} {year}",
                  f'<div class="pager"><a href="/calendar?y={year - 1}">← {year - 1}</a>'
                  f'<strong>{self.t("calendar")} {year} · Pascha {e:%d %b}</strong>'
                  f'<a href="/calendar?y={year + 1}">{year + 1} →</a></div><table>{"".join(rows)}</table>')


def serve(port=8754):
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.local = threading.local()
    db.connect().close()   # create schema / copy seed once
    print(f"Credo Library on http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
