"""Devotional pages of the Credo web app: Today, Holy Rosary, Prayers, Examination of Conscience."""
import datetime as dt
import html
import json

from . import config, devotions, liturgy

H = html.escape

CSS = """
.today-hero { text-align:center; padding:1.6rem 1rem; border-radius:14px; background:var(--view);
  border:1px solid var(--alt); margin:1rem 0 }
.today-hero h1 { margin:.3rem 0; font-variant:small-caps; letter-spacing:.04em }
.today-hero .date { color:var(--dim); text-transform:uppercase; letter-spacing:.14em; font-size:.85rem }
.tiles { display:grid; grid-template-columns:repeat(auto-fill, minmax(13rem, 1fr)); gap:.9rem; margin:1rem 0 }
.tile { display:block; padding:1rem 1.1rem; border-radius:12px; background:var(--view); border:1px solid var(--alt);
  text-decoration:none; color:var(--fg) } .tile:hover { border-color:var(--acc) }
.tile b { display:block; color:var(--acc); font-variant:small-caps; letter-spacing:.04em; font-size:1.05rem }
.tile span { color:var(--dim); font-size:.9rem }
.prayer { margin:1.1rem 0 1.6rem } .prayer h3 { font-variant:small-caps; color:var(--acc); margin:.2rem 0 .4rem;
  border-bottom:1px solid var(--alt) } .prayer p { margin:.35rem 0 }
.vr { color:var(--acc); font-weight:600 }
.toc { columns:2 16rem; margin:1rem 0 } .toc a { display:block; text-decoration:none; padding:.15rem 0 }
.beads { display:flex; flex-wrap:wrap; gap:4px; justify-content:center; margin:1rem 0 }
.bead { width:11px; height:11px; border-radius:50%; background:var(--alt); border:1px solid var(--dim) }
.bead.large { width:16px; height:16px } .bead.cross { border-radius:2px; width:12px; height:16px }
.bead.none { display:none } .bead.done { background:var(--gold) } .bead.now { background:var(--acc);
  box-shadow:0 0 0 3px color-mix(in srgb, var(--acc) 35%, transparent) }
.step { display:none } .step.on { display:block }
.step .head { text-align:center; color:var(--acc); font-variant:small-caps; letter-spacing:.05em; font-size:1.2rem }
.step .note { text-align:center; color:var(--dim); font-style:italic }
.step .cols p { font-size:1.12rem }
.rosary-nav { display:flex; justify-content:center; gap:.8rem; margin:1.2rem 0 }
.rosary-nav button { min-width:8rem } .kbd { color:var(--dim); font-size:.85rem; text-align:center }
.examen li { margin:.3rem 0 }
details.set { margin:.6rem 0 } details.set summary { cursor:pointer; color:var(--acc) }
"""

ROSARY_JS = """
(function () {
  var steps = document.querySelectorAll('.step'), beads = document.querySelectorAll('.bead');
  var i = 0, key = 'credo-rosary-' + (document.body.dataset.set || '');
  try { i = Math.min(parseInt(sessionStorage.getItem(key) || '0', 10) || 0, steps.length - 1); } catch (e) {}
  function show(n) {
    i = Math.max(0, Math.min(steps.length - 1, n));
    for (var k = 0; k < steps.length; k++) steps[k].classList.toggle('on', k === i);
    for (var k = 0; k < beads.length; k++) {
      beads[k].classList.toggle('done', k < i);
      beads[k].classList.toggle('now', k === i);
    }
    document.getElementById('count').textContent = (i + 1) + ' / ' + steps.length;
    try { sessionStorage.setItem(key, String(i)); } catch (e) {}
  }
  document.getElementById('prev').onclick = function () { show(i - 1); };
  document.getElementById('next').onclick = function () { show(i + 1); };
  document.getElementById('restart').onclick = function () { show(0); };
  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') { e.preventDefault(); show(i + 1); }
    if (e.key === 'ArrowLeft' || e.key === 'Backspace') { e.preventDefault(); show(i - 1); }
  });
  show(i);
})();
"""


def prayer_html(key, lang_first="la", title=True):
    en_t, la_t, en, la, _ = devotions.PRAYERS[key]

    def paras(text):
        out = []
        for p in text.split("|"):
            p = H(p)
            for sym in ("℣.", "℟."):
                p = p.replace(sym, f'<span class="vr">{sym}</span>')
            out.append(f"<p>{p}</p>")
        return "".join(out)

    head = ""
    if title:
        head = f'<h3 id="{key}">{H(la_t)} · {H(en_t)}</h3>' if la else f'<h3 id="{key}">{H(en_t)}</h3>'
    if not la:
        return f'<div class="prayer">{head}{paras(en)}</div>'
    cols = [paras(la), paras(en)] if lang_first == "la" else [paras(en), paras(la)]
    return f'<div class="prayer">{head}<div class="cols"><div>{cols[0]}</div><div>{cols[1]}</div></div></div>'


def saint_of_day(conn, day, L):
    """Title of today's Mass in the Proper of the Saints, if the Missal is downloaded."""
    try:
        r = conn.execute("SELECT title FROM docs WHERE collection='missal' AND ref=? AND lang=?",
                         (f"Sancti/{day.month:02d}-{day.day:02d}", L)).fetchone()
        if r:
            return r["title"]
    except Exception:
        pass
    return liturgy.sanctorale(day, L)


def today(handler):
    L = handler.lang()
    la = L == "la"
    d = liturgy.today()
    title = d.feast(L) or d.title(L)
    sub = d.title(L) if d.feast(L) else ""
    saint = saint_of_day(handler.conn, d.date, L)
    myst = devotions.mysteries_for(d.date)
    mset = devotions.MYSTERIES[myst]
    antiphon = devotions.marian_antiphon_key(d.date)
    notes = []
    if "Friday abstinence" in d.notes:
        notes.append("Feria VI: abstinentia a carnibus" if la else "Friday: abstinence from meat")
    if "Ember Day" in d.notes:
        notes.append("Quattuor Tempora: ieiunium et abstinentia" if la else "Ember Day: fast and abstinence")
    date_txt = d.date.strftime("%A, %d %B %Y")
    hero = (f'<div class="today-hero" style="border-top:6px solid {d.color_hex}">'
            f'<div class="date">{H(date_txt)}</div><h1>{H(title)}</h1>'
            + (f'<div class="muted">{H(sub)}</div>' if sub else "")
            + (f'<div>{H(saint)}</div>' if saint and saint != title else "")
            + f'<p><span class="dot" style="background:{d.color_hex}"></span> {H(d.season_name(L))} · {H(d.color)}'
            + (f' · <b>{H(" · ".join(notes))}</b>' if notes else "") + "</p></div>")
    tiles = [
        ("/mass", "Missa Diei" if la else "Mass of the Day", d.feast(L) or d.title(L)),
        ("/rosary", "Rosarium" if la else "Holy Rosary", mset[1] if la else mset[0]),
        (f"/prayers#{antiphon}", devotions.PRAYERS[antiphon][1 if la else 0],
         "Mane, meridie, vespere" if la else "Morning, noon and evening"),
        ("/prayers", "Preces" if la else "Prayers", "Latine et Anglice" if la else "Latin and English"),
        ("/examen", "Examen conscientiæ" if la else "Examination of Conscience",
         "Ante Confessionem" if la else "Before Confession"),
        ("/calendar", "Calendarium" if la else "Calendar", "Anni liturgici 1954" if la else "1954 liturgical year"),
        ("/ordo", "Ordo Missæ" if la else "Ordinary of the Mass", "Latine et Anglice" if la else "Latin and English"),
        ("/", "Bibliotheca" if la else "Catholic Library",
         "Pontifices, Sancti, Catechismus" if la else "Popes, saints, catechism"),
    ]
    grid = "".join(f'<a class="tile" href="{u}"><b>{H(a)}</b><span>{H(b)}</span></a>' for u, a, b in tiles)
    # The next feasts.
    rows, day = [], d.date
    for _ in range(45):
        day += dt.timedelta(days=1)
        i = liturgy.day_info(day)
        if i.feast_en or day.weekday() == 6:
            rows.append(f'<tr><td>{day:%a %d %b}</td><td><span class="dot" style="background:{i.color_hex}"></span>'
                        f'</td><td><a href="/mass?date={day}">{H(i.feast(L) or i.title(L))}</a></td></tr>')
        if len(rows) >= 7:
            break
    upcoming = f'<h2>{"Proxime" if la else "Coming up"}</h2><table>{"".join(rows)}</table>'
    saint_html = saint_sections(handler, d.date, L)
    handler.page("Hodie" if la else "Today",
                 f"<style>{CSS}</style>{hero}{saint_html}<div class='tiles'>{grid}</div>{upcoming}")


def saint_life(day):
    """The saint's life as read at Matins (Breviary, 2nd nocturn), {'la': [...], 'en': [...]}."""
    try:
        table = json.loads((config.SHARE / "saint-lives.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return table.get(f"{day.month:02d}-{day.day:02d}", {})


def saint_sections(handler, day, L):
    """Today's saint: the biography (Matins lessons) and the propers of the saint's Mass."""
    la = L == "la"
    out = []
    life = saint_life(day)
    if life:
        en, lat = life.get("en") or [], life.get("la") or []

        def paras(ps):
            return "".join(f"<p>{H(p)}</p>" for p in ps)
        cols = ([paras(lat), paras(en)] if la else [paras(en), paras(lat)])
        heads = (["Latine", "English"] if la else ["English", "Latine"])
        body = (f'<div class="cols"><div><h3 class="muted">{heads[0]}</h3>{cols[0]}</div>'
                f'<div><h3 class="muted">{heads[1]}</h3>{cols[1]}</div></div>') if en and lat else paras(en or lat)
        out.append(f'<details class="saint" open><summary><h2>{"Vita Sancti" if la else "Life of the Saint"}</h2>'
                   f'<span class="muted">{"Ex Breviario Romano, lectiones II Nocturni" if la else "From the Roman Breviary: the lessons of Matins (2nd nocturn)"}'
                   f'</span></summary>{body}</details>')
    ref = f"Sancti/{day.month:02d}-{day.day:02d}"
    la_t, la_b = handler._mass_html(ref, "la")
    en_t, en_b = handler._mass_html(ref, "en")
    if la_b or en_b:
        first = (la_b, en_b) if la else (en_b, la_b)
        second = ("Latine", "English") if la else ("English", "Latine")
        out.append(f'<details class="saint"><summary><h2>{"Proprium Sancti" if la else "Propers of the Saint"}'
                   f'</h2><span class="muted">{H(la_t if la else (en_t or la_t))}</span></summary>'
                   f'<div class="cols"><div><h3 class="muted">{second[0]}</h3>{first[0] or ""}</div>'
                   f'<div><h3 class="muted">{second[1]}</h3>{first[1] or ""}</div></div></details>')
    elif life:
        out.append(f'<p class="muted">{"Proprium Sancti: Missale in Credo Center › Bibliotheca adde." if la else "Propers of the Saint: download the Missal in Credo Center › Library to see them here."}'
                   f' <a href="/mass">{"Missa Diei" if la else "Mass of the Day"} →</a></p>')
    if not out:
        return ""
    style = ("<style>details.saint{margin:1.2rem 0;padding:.4rem 1.1rem;border:1px solid var(--alt);border-radius:12px;"
             "background:var(--view)}details.saint summary{cursor:pointer;list-style:none}"
             "details.saint summary h2{display:inline;margin-right:.6rem}details.saint summary::-webkit-details-marker"
             "{display:none}</style>")
    return style + "".join(out)


def rosary(handler, qs):
    L = handler.lang()
    la = L == "la"
    key = qs.get("set") if qs.get("set") in devotions.MYSTERIES else devotions.mysteries_for()
    name_en, name_la, items = devotions.MYSTERIES[key]
    steps = devotions.rosary_steps(key)
    beads = "".join(f'<span class="bead {k}"></span>' for k, *_ in steps)
    secs = []
    for n, (kind, pkey, h_en, h_la, n_en, n_la) in enumerate(steps):
        p = devotions.PRAYERS[pkey]
        head = (h_la if la else h_en) or (p[1] if la else p[0])
        note = n_la if la else n_en
        secs.append(f'<section class="step"><div class="head">{H(head)}</div>'
                    + (f'<div class="note">{H(note)}</div>' if note else "")
                    + prayer_html(pkey, "la" if la else "en", title=False) + "</section>")
    switch = " · ".join(
        (f"<b>{H(v[1] if la else v[0])}</b>" if k == key else
         f'<a href="/rosary?set={k}">{H(v[1] if la else v[0])}</a>') for k, v in devotions.MYSTERIES.items())
    listing = "".join(f"<li><b>{H(it[1] if la else it[0])}</b> — "
                      f"<span class='muted'>{H(it[3] if la else it[2])} · {H(it[4])}</span></li>" for it in items)
    body = (f"<style>{CSS}</style><h1>{'Sanctissimum Rosarium' if la else 'The Holy Rosary'}</h1>"
            f'<p class="muted">{switch}</p>'
            f'<details class="set"><summary>{H(name_la if la else name_en)}</summary><ol>{listing}</ol></details>'
            f'<div class="beads">{beads}</div>{"".join(secs)}'
            f'<div class="rosary-nav"><button id="prev">← {"Retro" if la else "Back"}</button>'
            f'<span id="count" class="muted" style="align-self:center"></span>'
            f'<button id="next">{"Porro" if la else "Next"} →</button></div>'
            f'<div class="kbd">{"Spatium vel → : porro · ← : retro" if la else "Space or → next · ← back"} · '
            f'<a href="#" id="restart">{"Ab initio" if la else "Start over"}</a></div>'
            f'<script src="/static/rosary.js"></script>')
    handler.page("Rosarium" if la else "Holy Rosary", body, body_attrs=f'data-set="{key}"')


def prayers(handler):
    L = handler.lang()
    la = L == "la"
    toc, sections = [], []
    for cat, en, la_name in devotions.CATEGORIES:
        keys = [k for k, v in devotions.PRAYERS.items() if v[4] == cat]
        sections.append(f"<h2>{H(la_name if la else en)}</h2>" + "".join(prayer_html(k, L) for k in keys))
        toc += [f'<a href="#{k}">{H(devotions.PRAYERS[k][1] if la else devotions.PRAYERS[k][0])}</a>' for k in keys]
    handler.page("Preces" if la else "Prayers",
                 f"<style>{CSS}</style><h1>{'Preces' if la else 'Prayers'}</h1>"
                 f'<div class="toc">{"".join(toc)}</div>{"".join(sections)}')


def examen(handler):
    L = handler.lang()
    la = L == "la"
    parts = []
    for en, la_head, questions in devotions.EXAMEN:
        parts.append(f"<h3>{H(en)}</h3><p class='muted'><i>{H(la_head)}</i></p>"
                     f"<ul class='examen'>{''.join(f'<li>{H(q)}</li>' for q in questions)}</ul>")
    handler.page("Examen conscientiæ" if la else "Examination of Conscience",
                 f"<style>{CSS}</style><h1>{'Examen conscientiæ' if la else 'Examination of Conscience'}</h1>"
                 f"<p>{'Ante examen:' if la else 'Before you begin:'}</p>{prayer_html('veni_sancte', L)}"
                 + "".join(parts)
                 + f"<h2>{'Quomodo confiteri' if la else 'How to go to Confession'}</h2>"
                   f"<p>{H(devotions.CONFESSION_GUIDE)}</p>{prayer_html('contritio', L)}")
