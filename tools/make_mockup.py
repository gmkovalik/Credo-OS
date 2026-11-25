"""Render a mockup of the planned Credo OS desktop (macOS 26 "Liquid Glass" style) as one HTML file.

Uses the real Credo icons and logos (inlined), so what you see is what the theme will ship.

    python tools/make_mockup.py      ->  design/credo-desktop-mockup.html
"""
import base64
import datetime as dt
import html
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "overlay/usr/lib/credo"))
from credo import devotions, liturgy  # noqa: E402

ICONS = ROOT / "overlay/usr/share/icons/Credo/scalable"
LOGOS = ROOT / "overlay/usr/share/credo/logos"
OUT = ROOT / "design/credo-desktop-mockup.html"


def data_uri(svg_text):
    return "data:image/svg+xml;base64," + base64.b64encode(svg_text.encode("utf-8")).decode()


def icon(name, kind="apps"):
    return data_uri((ICONS / kind / f"{name}.svg").read_text(encoding="utf-8"))


def logo(name, color):
    return data_uri((LOGOS / f"{name}.svg").read_text(encoding="utf-8").replace("currentColor", color))


LAUNCHPAD = data_uri("""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<defs><linearGradient id="b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f2f2f7"/>
<stop offset="1" stop-color="#c7c7d1"/></linearGradient></defs>
<rect x="50" y="62" width="412" height="412" rx="94" fill="#000" fill-opacity=".22"/>
<rect x="50" y="46" width="412" height="412" rx="94" fill="url(#b)"/>
<g>""" + "".join(f'<rect x="{118 + c * 98}" y="{114 + r * 98}" width="76" height="76" rx="20" fill="{col}"/>'
                 for r, row in enumerate((("#ff5f57", "#febc2e", "#28c840"), ("#3a6fc4", "#c9a227", "#8e1d27"),
                                          ("#5b2a86", "#2bb3a3", "#e8553d")))
                 for c, col in enumerate(row)) + "</g></svg>")


def main():
    d = liturgy.day_info(dt.date(2026, 11, 24))
    myst = devotions.MYSTERIES[devotions.mysteries_for(d.date)]
    gold = "#e9c46a"
    dock = [("Files", icon("system-file-manager")), ("Launchpad", LAUNCHPAD),
            ("Credo Browser", icon("credo-browser")), ("Today", icon("credo-today")),
            ("Holy Mass", icon("credo-mass")), ("Holy Rosary", icon("credo-rosary")),
            ("Prayers", icon("credo-prayers")), ("Library", icon("credo-library")),
            ("Bible", icon("xiphos")), ("Music", icon("org.kde.elisa")), ("Photos", icon("org.kde.gwenview")),
            ("Credo Console", icon("credo-console")), ("Credo Center", icon("credo-center"))]
    running = {"Files", "Credo Browser", "Credo Console", "Holy Rosary"}
    dock_html = "".join(
        f'<div class="di" title="{n}"><img src="{src}" alt=""><span class="tip">{n}</span>'
        f'{"<i></i>" if n in running else ""}</div>' for n, src in dock)
    dock_html += (f'<div class="sep"></div><div class="di"><img src="{icon("folder-download", "places")}" alt="">'
                  f'</div><div class="di"><img src="{icon("user-trash-full", "places")}" alt=""></div>')
    folders = [("Desktop", "user-desktop"), ("Documents", "folder-documents"), ("Downloads", "folder-download"),
               ("Pictures", "folder-pictures"), ("Music", "folder-music"), ("Videos", "folder-videos"),
               ("Missale 1954", "folder"), ("Encyclicals", "folder"), ("Summa Theologiae", "folder")]
    grid = "".join(f'<div class="fi"><img src="{icon(i, "places")}" alt=""><span>{n}</span></div>'
                   for n, i in folders)
    E = html.escape
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Credo OS — desktop mockup</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0 }}
html, body {{ width:1600px; height:1000px; overflow:hidden; background:#000;
  font:13px/1.35 Inter, "SF Pro Text", "Noto Sans", "Segoe UI", sans-serif; color:#fff; -webkit-font-smoothing:antialiased }}
.screen {{ position:relative; width:1600px; height:1000px; overflow:hidden;
  background:
    radial-gradient(1200px 700px at 78% 8%, #3f7f5a 0%, transparent 60%),
    radial-gradient(900px 600px at 10% 90%, #1b4d3c 0%, transparent 60%),
    radial-gradient(700px 500px at 50% 55%, #6b5a2a 0%, transparent 65%),
    linear-gradient(160deg, #0f2a22 0%, #123a2c 45%, #0a1712 100%) }}
.wave {{ position:absolute; border-radius:50%; filter:blur(60px); opacity:.55 }}
.watermark {{ position:absolute; left:50%; top:45%; width:430px; height:430px; transform:translate(-50%,-50%);
  opacity:.16; filter:drop-shadow(0 0 40px rgba(233,196,106,.6)) }}
/* Liquid Glass */
.glass {{ background:linear-gradient(180deg, rgba(255,255,255,.20), rgba(255,255,255,.08));
  backdrop-filter:blur(28px) saturate(170%); -webkit-backdrop-filter:blur(28px) saturate(170%);
  border:1px solid rgba(255,255,255,.28); box-shadow:inset 0 1px 0 rgba(255,255,255,.45),
  inset 0 -1px 0 rgba(255,255,255,.08), 0 18px 50px rgba(0,0,0,.35) }}
.dark-glass {{ background:linear-gradient(180deg, rgba(40,36,30,.72), rgba(24,22,18,.66));
  backdrop-filter:blur(30px) saturate(150%); -webkit-backdrop-filter:blur(30px) saturate(150%);
  border:1px solid rgba(255,255,255,.14); box-shadow:inset 0 1px 0 rgba(255,255,255,.16), 0 30px 80px rgba(0,0,0,.55) }}
/* menu bar: fully transparent, like Tahoe */
.menubar {{ position:absolute; top:0; left:0; right:0; height:32px; display:flex; align-items:center;
  padding:0 16px; gap:20px; font-weight:500; text-shadow:0 1px 3px rgba(0,0,0,.45) }}
.menubar img.l {{ width:18px; height:18px }}
.menubar b {{ font-weight:700 }}
.menubar .right {{ margin-left:auto; display:flex; gap:16px; align-items:center }}
.pill {{ display:flex; align-items:center; gap:7px; padding:3px 10px; border-radius:99px; font-size:12.5px }}
.dot {{ width:9px; height:9px; border-radius:50%; background:{d.color_hex}; box-shadow:0 0 0 2px rgba(255,255,255,.35) }}
.sym {{ width:17px; height:17px; opacity:.95 }}
/* dock */
.dock {{ position:absolute; bottom:12px; left:50%; transform:translateX(-50%); display:flex; align-items:flex-end;
  gap:6px; padding:9px 12px 10px; border-radius:30px }}
.di {{ position:relative; width:62px; height:62px; transition:.15s }}
.di img {{ width:100%; height:100%; filter:drop-shadow(0 4px 6px rgba(0,0,0,.35)) }}
.di i {{ position:absolute; left:50%; bottom:-7px; width:5px; height:5px; margin-left:-2.5px; border-radius:50%;
  background:rgba(255,255,255,.85) }}
.di.big {{ width:78px; height:78px; margin-top:-16px }} .di.mid {{ width:70px; height:70px }}
.tip {{ display:none }}
.di.big .tip {{ display:block; position:absolute; bottom:94px; left:50%; transform:translateX(-50%);
  white-space:nowrap; padding:4px 11px; border-radius:9px; font-size:12px; background:rgba(30,28,25,.75);
  border:1px solid rgba(255,255,255,.2) }}
.sep {{ width:1px; height:54px; background:rgba(255,255,255,.35); margin:0 6px 4px }}
/* windows */
.win {{ position:absolute; border-radius:22px; overflow:hidden }}
.tl {{ display:flex; gap:8px; padding:0 2px }} .tl span {{ width:13px; height:13px; border-radius:50%;
  box-shadow:inset 0 0 0 .5px rgba(0,0,0,.25) }}
.tl .r {{ background:#ff5f57 }} .tl .y {{ background:#febc2e }} .tl .g {{ background:#28c840 }}
/* Files (Finder-like) */
.files {{ left:150px; top:120px; width:760px; height:470px; display:flex }}
.side {{ width:200px; padding:16px 12px; display:flex; flex-direction:column; gap:3px; margin:8px;
  border-radius:16px; font-size:13px }}
.side h6 {{ font-size:11px; color:rgba(255,255,255,.55); margin:12px 8px 4px; font-weight:600 }}
.side a {{ display:flex; gap:9px; align-items:center; padding:5px 8px; border-radius:8px; color:#f3efe6 }}
.side a.on {{ background:rgba(255,255,255,.16) }} .side a img {{ width:18px; height:18px }}
.main {{ flex:1; display:flex; flex-direction:column }}
.tb {{ height:52px; display:flex; align-items:center; gap:14px; padding:0 18px; font-weight:700; font-size:15px }}
.tb .seg {{ margin-left:auto; display:flex; gap:2px; padding:3px; border-radius:99px; background:rgba(255,255,255,.1) }}
.tb .seg span {{ width:30px; height:22px; border-radius:99px }} .tb .seg span.on {{ background:rgba(255,255,255,.22) }}
.tb .search {{ width:170px; height:28px; border-radius:99px; background:rgba(255,255,255,.1); font-weight:400;
  font-size:12.5px; color:rgba(255,255,255,.55); display:flex; align-items:center; padding:0 12px }}
.fgrid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:18px 10px; padding:14px 22px }}
.fi {{ display:flex; flex-direction:column; align-items:center; gap:6px; font-size:12.5px }}
.fi img {{ width:78px; height:78px }}
/* Browser */
.browser {{ left:560px; top:250px; width:900px; height:600px; display:flex; flex-direction:column }}
.btop {{ height:50px; display:flex; align-items:center; gap:14px; padding:0 16px }}
.tabs {{ display:flex; gap:6px }} .tab {{ padding:6px 14px; border-radius:99px; font-size:12px; color:rgba(255,255,255,.75) }}
.tab.on {{ background:rgba(255,255,255,.16); color:#fff }}
.addr {{ flex:1; height:30px; border-radius:99px; background:rgba(255,255,255,.1); display:flex; align-items:center;
  justify-content:center; font-size:12.5px; color:rgba(255,255,255,.8); gap:6px }}
.page {{ flex:1; margin:0 8px 8px; border-radius:16px; overflow:hidden; position:relative;
  background:radial-gradient(circle at 50% 25%, #1f4a26, #0b140c); display:flex; flex-direction:column; align-items:center }}
.page img.medal {{ width:84px; margin-top:34px }}
.page .date {{ letter-spacing:.16em; font-size:11px; opacity:.75; margin-top:10px }}
.page .feast {{ font-family:"Noto Serif", Georgia, serif; font-variant:small-caps; font-size:22px; color:{gold}; letter-spacing:.04em }}
.page .q {{ margin-top:18px; width:520px; height:44px; border-radius:16px; display:flex; align-items:center; padding:0 18px;
  color:rgba(255,255,255,.55) }}
.tiles {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; width:640px; margin-top:22px }}
.tile {{ display:flex; flex-direction:column; align-items:center; gap:6px; padding:12px 6px; border-radius:16px; font-size:12px }}
.tile img {{ width:46px }}
/* Console */
.console {{ left:1030px; top:150px; width:520px; height:250px }}
.cbar {{ height:38px; display:flex; align-items:center; padding:0 14px; gap:10px; font-size:12px; color:rgba(255,255,255,.6) }}
.cbar .t {{ flex:1; text-align:center; margin-right:60px }}
pre {{ font:12.5px/1.55 "JetBrains Mono", "Noto Sans Mono", Consolas, monospace; padding:4px 16px; color:#e8e0d0 }}
.gold {{ color:{gold}; font-weight:700 }} .dim {{ opacity:.6 }} .grn {{ color:#7fd08a }} .blu {{ color:#81a8db }}
/* widgets */
.widget {{ position:absolute; border-radius:24px; padding:16px 18px }}
.w-today {{ left:40px; top:620px; width:300px; height:170px }}
.w-today .k {{ font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:rgba(255,255,255,.7) }}
.w-today .f {{ font-family:"Noto Serif", Georgia, serif; font-size:19px; margin:6px 0; line-height:1.25 }}
.w-today .s {{ display:flex; gap:8px; align-items:center; font-size:12.5px; color:rgba(255,255,255,.85) }}
.w-ros {{ left:356px; top:620px; width:170px; height:170px; display:flex; flex-direction:column; align-items:center;
  justify-content:center; gap:8px; text-align:center }}
.w-ros img {{ width:64px }} .w-ros b {{ font-size:13px }} .w-ros span {{ font-size:11.5px; opacity:.75 }}
/* notification */
.notif {{ position:absolute; right:18px; top:44px; width:340px; border-radius:22px; padding:12px 14px; display:flex; gap:12px }}
.notif img {{ width:38px; height:38px }} .notif b {{ display:block; font-size:13px }}
.notif p {{ font-size:12.5px; opacity:.85 }} .notif .t {{ margin-left:auto; font-size:11px; opacity:.6 }}
.caption {{ position:absolute; left:18px; bottom:16px; font-size:11px; opacity:.45 }}
</style></head><body><div class="screen">
<div class="wave" style="left:900px;top:-120px;width:900px;height:520px;background:#4f9a6c"></div>
<div class="wave" style="left:-200px;top:560px;width:900px;height:520px;background:#24604a"></div>
<div class="wave" style="left:520px;top:420px;width:700px;height:380px;background:#8a7130;opacity:.35"></div>
<img class="watermark" src="{logo('chirho', gold)}" alt="">

<div class="menubar">
  <img class="l" src="{logo('chirho', '#ffffff')}" alt=""><b>Credo Browser</b>
  <span>File</span><span>Edit</span><span>View</span><span>History</span><span>Bookmarks</span><span>Window</span><span>Help</span>
  <div class="right">
    <div class="pill glass"><span class="dot"></span>{E(d.title('en'))}</div>
    <svg class="sym" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M2 9a15 15 0 0 1 20 0M5.5 12.5a10 10 0 0 1 13 0M9 16a5 5 0 0 1 6 0"/><circle cx="12" cy="19.5" r="1" fill="#fff"/></svg>
    <svg class="sym" viewBox="0 0 28 24" fill="none" stroke="#fff" stroke-width="1.8"><rect x="2" y="6" width="21" height="12" rx="3.5"/><rect x="4.5" y="8.5" width="13" height="7" rx="1.5" fill="#fff" stroke="none"/><path d="M25 10v4" stroke-linecap="round"/></svg>
    <svg class="sym" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><rect x="3" y="5" width="18" height="5" rx="2.5"/><rect x="3" y="14" width="18" height="5" rx="2.5"/><circle cx="8" cy="7.5" r="1.5" fill="#fff"/><circle cx="16" cy="16.5" r="1.5" fill="#fff"/></svg>
    <span>Tue 24 Nov&nbsp;&nbsp;12:41</span>
  </div>
</div>

<div class="notif glass"><img src="{icon('credo-prayers')}" alt="">
  <div><b>The Angelus</b><p>℣. The Angel of the Lord declared unto Mary. ℟. And she conceived of the Holy Ghost.</p></div>
  <span class="t">now</span></div>

<div class="win dark-glass files">
  <div class="side glass">
    <div class="tl" style="margin:2px 4px 10px"><span class="r"></span><span class="y"></span><span class="g"></span></div>
    <h6>Favorites</h6>
    <a class="on"><img src="{icon('user-home', 'places')}">Home</a>
    <a><img src="{icon('user-desktop', 'places')}">Desktop</a>
    <a><img src="{icon('folder-documents', 'places')}">Documents</a>
    <a><img src="{icon('folder-download', 'places')}">Downloads</a>
    <h6>Credo</h6>
    <a><img src="{icon('credo-library')}">Catholic Library</a>
    <a><img src="{icon('xiphos')}">Holy Bible</a>
    <h6>Locations</h6>
    <a><img src="{icon('user-trash', 'places')}">Trash</a>
  </div>
  <div class="main">
    <div class="tb">Home<div class="seg"><span class="on"></span><span></span><span></span></div>
      <div class="search">⌕&nbsp; Search</div></div>
    <div class="fgrid">{grid}</div>
  </div>
</div>

<div class="win dark-glass browser">
  <div class="btop"><div class="tl"><span class="r"></span><span class="y"></span><span class="g"></span></div>
    <div class="tabs"><div class="tab on">New tab</div><div class="tab">Divinum Officium</div><div class="tab">New Advent</div></div>
    <div class="addr">🔒 Search or enter address · DuckDuckGo</div></div>
  <div class="page">
    <img class="medal" src="{logo('chirho', gold)}" alt="">
    <div class="date">TUESDAY 24 NOVEMBER 2026 · TIME AFTER PENTECOST</div>
    <div class="feast">St. John of the Cross</div>
    <div class="q glass">Search or enter address</div>
    <div class="tiles">
      <div class="tile glass"><img src="{icon('credo-today')}">Today</div>
      <div class="tile glass"><img src="{icon('credo-mass')}">Mass of the Day</div>
      <div class="tile glass"><img src="{icon('credo-rosary')}">Holy Rosary</div>
      <div class="tile glass"><img src="{icon('credo-prayers')}">Prayers</div>
    </div>
  </div>
</div>

<div class="win dark-glass console">
  <div class="cbar"><div class="tl"><span class="r"></span><span class="y"></span><span class="g"></span></div>
    <div class="t">~ — Credo Console</div></div>
<pre><span class="gold">✠ {E(d.title('en'))}</span>
<span class="dim">● Tuesday 24 November 2026 · Time after Pentecost · Rosary: {E(myst[0])}</span>

<span class="grn">credo@x1</span>:<span class="blu">~</span>$ credo-liturgy --lang la
2026-11-24  Feria III infra Hebdomadam XXIV post Pentecosten
  Tempus:   Tempus post Pentecosten · viridis
<span class="grn">credo@x1</span>:<span class="blu">~</span>$ █</pre>
</div>

<div class="widget glass w-today">
  <div class="k">Hodie · Today</div>
  <div class="f">St. John of the Cross,<br>Confessor and Doctor</div>
  <div class="s"><span class="dot"></span>Time after Pentecost · green</div>
  <div class="s" style="margin-top:6px">Next: <b>&nbsp;Advent Sunday, 29 Nov</b></div>
</div>
<div class="widget glass w-ros"><img src="{icon('credo-rosary')}"><b>{E(myst[0].replace('The ', ''))}</b><span>Tap to pray</span></div>

<div class="dock glass">{dock_html}</div>
<div class="caption">Credo OS · design mockup (not a screenshot) · icons and logos are the real theme files</div>
</div>
<script>
  // magnify the dock around "Holy Rosary", as macOS does under the pointer
  const items = [...document.querySelectorAll('.dock .di')];
  const i = items.findIndex(e => e.title === 'Holy Rosary');
  if (i >= 0) {{ items[i].classList.add('big'); [i-1, i+1].forEach(k => items[k] && items[k].classList.add('mid')); }}
</script>
</body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
