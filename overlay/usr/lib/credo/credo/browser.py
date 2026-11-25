"""Credo Browser: a full web browser for Credo OS (PySide6 + Qt WebEngine / Chromium).

Tabs, private windows, bookmarks (with a bar), history, downloads, find in page, zoom,
print to PDF, developer tools, tracker blocking, site permission prompts, session restore,
and a Catholic start page. English / Latin interface.

    credo-browser [URL ...]          open URLs (in the running window if there is one)
    credo-browser --private [URL]    private window: nothing is saved
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import time

from PySide6.QtCore import QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWebEngineCore import (QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile,
                                     QWebEngineSettings, QWebEngineUrlRequestInterceptor)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressBar,
                               QPushButton, QSizePolicy, QStackedWidget, QTabBar, QToolBar, QToolButton,
                               QVBoxLayout, QWidget)

from . import config, liturgy, palettes

APP_ID = "credo-browser"
DATA = config.DATA_DIR / "browser"
STATE = DATA / "state.json"

SEARCH = {  # key: (name, url, query parameter)
    "duckduckgo": ("DuckDuckGo", "https://duckduckgo.com/", "q"),
    "startpage": ("Startpage", "https://www.startpage.com/do/search", "query"),
    "google": ("Google", "https://www.google.com/search", "q"),
    "bing": ("Bing", "https://www.bing.com/search", "q"),
    "ecosia": ("Ecosia", "https://www.ecosia.org/search", "q"),
    "wikipedia": ("Wikipedia", "https://en.wikipedia.org/w/index.php", "search"),
}

CREDO_PAGES = [("Hodie · Today", "/today"), ("Missa Diei · Mass", "/mass"), ("Rosarium · Rosary", "/rosary"),
               ("Preces · Prayers", "/prayers"), ("Bibliotheca · Library", "/")]

DEFAULT_BOOKMARKS = [
    ("The Holy See", "https://www.vatican.va/"),
    ("New Advent (Catholic Encyclopedia, Summa, Fathers)", "https://www.newadvent.org/"),
    ("Divinum Officium (Breviary and Missal)", "https://www.divinumofficium.com/"),
    ("Douay-Rheims Bible", "https://www.drbo.org/"),
    ("Papal Encyclicals Online", "https://www.papalencyclicals.net/"),
    ("Corpus Thomisticum", "https://www.corpusthomisticum.org/"),
    ("Sancta Missa (Tridentine Mass tutorial)", "https://www.sanctamissa.org/"),
    ("Musica Sacra (chant)", "https://www.musicasacra.com/"),
    ("Latin dictionary (Whitaker's Words)", "https://archives.nd.edu/words.html"),
    ("Wikipedia", "https://en.wikipedia.org/"),
]

TRACKERS = re.compile(
    r"(^|\.)(doubleclick\.net|googlesyndication\.com|google-analytics\.com|googletagmanager\.com|"
    r"googleadservices\.com|adservice\.google\.com|facebook\.net|connect\.facebook\.net|"
    r"scorecardresearch\.com|quantserve\.com|adnxs\.com|criteo\.com|criteo\.net|taboola\.com|"
    r"outbrain\.com|hotjar\.com|amazon-adsystem\.com|moatads\.com|rubiconproject\.com|"
    r"pubmatic\.com|openx\.net|casalemedia\.com|bluekai\.com|krxd\.net|zedo\.com|yieldmo\.com|"
    r"media\.net|advertising\.com|adsrvr\.org|clarity\.ms|mixpanel\.com|segment\.io)$")

TR = {
    "back": ("Back", "Retro"), "forward": ("Forward", "Porro"), "reload": ("Reload", "Renova"),
    "stop": ("Stop", "Siste"), "home": ("Home", "Domus"), "new_tab": ("New tab", "Nova tabula"),
    "new_window": ("New window", "Nova fenestra"), "private": ("New private window", "Fenestra privata"),
    "bookmarks": ("Bookmarks", "Signacula"), "bookmark_add": ("Bookmark this page", "Signa hanc paginam"),
    "bookmarks_bar": ("Show bookmarks bar", "Ostende taeniam signaculorum"),
    "manage_bookmarks": ("Manage bookmarks…", "Signacula administra…"),
    "history": ("History", "Historia"), "downloads": ("Downloads", "Depositiones"),
    "find": ("Find in page…", "Quaere in pagina…"), "zoom_in": ("Zoom in", "Amplifica"),
    "zoom_out": ("Zoom out", "Minue"), "zoom_reset": ("Actual size", "Magnitudo vera"),
    "print": ("Save page as PDF…", "Serva ut PDF…"), "devtools": ("Developer tools", "Instrumenta"),
    "fullscreen": ("Full screen", "Plenum velum"), "settings": ("Settings…", "Optiones…"),
    "quit": ("Quit", "Exi"), "search_ph": ("Search or enter address", "Quaere vel inscribe inscriptionem"),
    "private_title": ("Private", "Privata"), "clear": ("Clear history", "Dele historiam"),
    "search_engine": ("Search engine", "Machina quaerendi"), "homepage": ("Home page", "Pagina domestica"),
    "block": ("Block trackers and ads", "Obstrue indagatores"), "restore": ("Reopen tabs from last time",
                                                                        "Tabulas priores restitue"),
    "open_folder": ("Open folder", "Aperi"), "remove": ("Remove", "Remove"), "close": ("Close", "Claude"),
    "allow": ("Allow", "Permitte"), "deny": ("Block", "Nega"),
    "reopen": ("Reopen closed tab", "Tabulam clausam restitue"),
    "cert": ("The connection to this site is not secure", "Conexio non tuta est"),
    "credo": ("Credo", "Credo"), "language": ("Interface language", "Lingua"),
}


def T(key):
    en, la = TR.get(key, (key, key))
    return la if config.language() == "la" else en


def icon(name):
    return QIcon.fromTheme(name)


# ------------------------------------------------------------------ storage
class Store:
    """Bookmarks, history and settings in ~/.local/share/credo/browser/ (JSON, small and readable)."""

    def __init__(self):
        DATA.mkdir(parents=True, exist_ok=True)
        self.bookmarks = self._load("bookmarks.json", [{"title": t, "url": u} for t, u in DEFAULT_BOOKMARKS])
        self.history = self._load("history.json", [])
        self.settings = {"search": "duckduckgo", "home": "start", "block": True, "restore": True,
                         "bookmarks_bar": False}
        self.settings.update(self._load("settings.json", {}))

    def _load(self, name, default):
        try:
            return json.loads((DATA / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    def save(self, name):
        data = {"bookmarks.json": self.bookmarks, "history.json": self.history[-5000:],
                "settings.json": self.settings}[name]
        tmp = DATA / (name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(DATA / name)

    def add_history(self, url, title):
        if not url or url.startswith(("file:", "data:", "about:", "devtools:")):
            return
        self.history.append({"url": url, "title": title or url, "t": int(time.time())})
        if len(self.history) % 20 == 0:
            self.save("history.json")

    def is_bookmarked(self, url):
        return any(b["url"] == url for b in self.bookmarks)

    def toggle_bookmark(self, url, title):
        if self.is_bookmarked(url):
            self.bookmarks = [b for b in self.bookmarks if b["url"] != url]
        else:
            self.bookmarks.append({"title": title or url, "url": url})
        self.save("bookmarks.json")


# ------------------------------------------------------------------ start page
def library_url(path="/"):
    port = config.load().getint("library", "port", fallback=8754)
    return f"http://127.0.0.1:{port}{path}"


def ensure_library_server():
    """Start the local Credo library server (Today, Mass, Rosary...) if it is not running."""
    try:
        from . import library
        p = library.port()
        if not library.running(p):
            env = dict(os.environ, PYTHONPATH=str(pathlib.Path(__file__).resolve().parent.parent))
            subprocess.Popen([sys.executable, "-m", "credo.library", "serve", "--port", str(p)], env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        pass


def start_page(store):
    """Write the start page (search, today's feast, Catholic shortcuts) and return its URL."""
    la = config.language() == "la"
    L = "la" if la else "en"
    try:
        _, p = palettes.resolve(config.load().get("appearance", "variant", fallback="monastic"))
    except Exception:
        _, p = palettes.resolve("monastic")
    d = liturgy.today()
    name, url, param = SEARCH.get(store.settings["search"], SEARCH["duckduckgo"])
    logo = config.SHARE / "logos" / f"{config.load().get('appearance', 'logo', fallback='chirho')}.svg"
    try:
        logo_svg = logo.read_text(encoding="utf-8").replace("currentColor", p["logo"])
        logo_svg = logo_svg.replace('width="512" height="512"', 'width="96" height="96"')
    except OSError:
        logo_svg = ""
    E = html.escape
    icons = pathlib.Path("/usr/share/icons/Credo/scalable/apps")

    def tile(label, path, ic):
        img = icons / f"{ic}.svg"
        pic = f'<img src="{QUrl.fromLocalFile(str(img)).toString()}" alt="">' if img.exists() else ""
        return f'<a class="tile" href="{library_url(path)}">{pic}<span>{E(label)}</span></a>'
    tiles = "".join(tile(*t) for t in (
        (("Hodie" if la else "Today"), "/today", "credo-today"),
        (("Missa diei" if la else "Mass of the Day"), "/mass", "credo-mass"),
        (("Sanctum Rosarium" if la else "Holy Rosary"), "/rosary", "credo-rosary"),
        (("Preces" if la else "Prayers"), "/prayers", "credo-prayers")))
    marks = "".join(f'<a class="mark" href="{E(b["url"])}">{E(b["title"].split(" (")[0])}</a>'
                    for b in store.bookmarks[:8])
    feast = E(d.feast(L) or d.title(L))
    gold = p["logo"]
    # The design's new-tab page: a dark green glass sheet, the gold Chi-Rho medallion, the day and
    # feast, a search pill, and four glass tiles for the daily devotions.
    page = f"""<!doctype html><html lang="{L}"><head><meta charset="utf-8"><title>{"Pagina nova" if la else "New tab"}</title>
<style>
html {{ background:#121a16 }}
body {{ margin:0; min-height:100vh; color:#ebe8df; font:15px/1.5 Inter, "Noto Sans", sans-serif; display:flex;
  flex-direction:column; align-items:center;
  background:radial-gradient(ellipse at 50% 18%, #213229 0%, #17231d 45%, #111914 100%) }}
.top {{ margin-top:11vh; text-align:center }}
.medal {{ width:84px; height:84px; margin:0 auto 1.1rem; border-radius:50%; display:grid; place-items:center;
  border:2px solid {gold}; box-shadow:0 0 0 5px {gold}22, 0 0 32px {gold}33; color:{gold} }}
.medal svg {{ width:58px; height:58px }}
.date {{ font-size:.72rem; letter-spacing:.2em; text-transform:uppercase; color:#ebe8dfa8; font-weight:600 }}
.feast {{ margin-top:.3rem; font-family:"Noto Serif", "DejaVu Serif", Georgia, serif; font-variant:small-caps;
  letter-spacing:.05em; font-size:1.6rem; color:{gold} }}
form {{ margin:1.8rem 0 1.8rem; width:min(34rem, 88vw) }}
input {{ width:100%; box-sizing:border-box; padding:.72rem 1.1rem; font:inherit; font-size:.95rem; border-radius:12px;
  border:1px solid #ffffff1f; background:#ffffff0f; color:#ebe8df; outline:none;
  box-shadow:inset 0 1px 0 #ffffff14 }}
input::placeholder {{ color:#ebe8df80 }}
input:focus {{ border-color:{gold}99; box-shadow:0 0 0 3px {gold}26 }}
.tiles {{ display:flex; gap:.8rem; flex-wrap:wrap; justify-content:center }}
.tile {{ width:8.6rem; height:5.6rem; border-radius:14px; display:flex; flex-direction:column; align-items:center;
  justify-content:center; gap:.45rem; text-decoration:none; color:#ebe8df; font-weight:600; font-size:.82rem;
  background:#ffffff12; border:1px solid #ffffff24;
  box-shadow:0 8px 22px #0000004d; transition:transform .12s, background .12s }}
.tile:hover {{ transform:translateY(-2px); background:#ffffff1c }}
.tile img {{ width:38px; height:38px }}
.marks {{ margin:2.4rem 0 2rem; display:flex; flex-wrap:wrap; gap:.4rem; justify-content:center; max-width:50rem }}
.mark {{ padding:.3rem .8rem; border-radius:999px; background:#ffffff0d; border:1px solid #ffffff17; color:#ebe8dfc0;
  text-decoration:none; font-size:.78rem }}
.mark:hover {{ color:#fff; border-color:{gold}80 }}
</style></head><body>
<div class="top"><div class="medal">{logo_svg}</div>
<div class="date">{E(d.date.strftime('%A %d %B %Y'))} · {E(d.season_name(L))}</div>
<div class="feast">{feast}</div></div>
<form action="{E(url)}" method="get"><input name="{E(param)}" autofocus placeholder="{E(T('search_ph'))}"></form>
<div class="tiles">{tiles}</div>
<div class="marks">{marks}</div>
</body></html>"""
    path = DATA / "start.html"
    path.write_text(page, encoding="utf-8")
    return QUrl.fromLocalFile(str(path))


def to_url(text, store):
    """Address bar text -> URL: an address, a local path, or a search."""
    text = text.strip()
    if not text:
        return None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", text) and not re.match(r"^[\w.-]+:\d", text):
        return QUrl(text)
    if text.startswith(("/", "~")):
        return QUrl.fromLocalFile(os.path.expanduser(text))
    if " " not in text and (re.match(r"^[\w-]+(\.[\w-]+)+(:\d+)?(/.*)?$", text)
                            or re.match(r"^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?(/.*)?$", text)):
        scheme = "http://" if text.startswith(("localhost", "127.", "[::1]")) else "https://"
        return QUrl(scheme + text)
    _, base, param = SEARCH.get(store.settings["search"], SEARCH["duckduckgo"])
    u = QUrl(base)
    from PySide6.QtCore import QUrlQuery
    q = QUrlQuery()
    q.addQueryItem(param, text)
    u.setQuery(q)
    return u


# ------------------------------------------------------------------ web engine pieces
class Interceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, store):
        super().__init__()
        self.store = store

    def interceptRequest(self, info):
        if self.store.settings.get("block") and TRACKERS.search(info.requestUrl().host()):
            info.block(True)


class Page(QWebEnginePage):
    def __init__(self, profile, parent):
        super().__init__(profile, parent)
        if hasattr(self, "permissionRequested"):              # Qt >= 6.8
            self.permissionRequested.connect(self._permission)
        else:
            self.featurePermissionRequested.connect(self._feature)
        self.certificateError.connect(self._certificate)
        self.fullScreenRequested.connect(self._fullscreen)

    def _ask(self, origin, what):
        r = QMessageBox.question(self.parent().window(), "Credo",
                                 f"{origin}\n\n{what}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return r == QMessageBox.Yes

    def _permission(self, permission):
        what = str(permission.permissionType()).split(".")[-1].replace("_", " ")
        permission.grant() if self._ask(permission.origin().host(), what) else permission.deny()

    def _feature(self, url, feature):
        what = str(feature).split(".")[-1]
        policy = (QWebEnginePage.PermissionPolicy.PermissionGrantedByUser if self._ask(url.host(), what)
                  else QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
        self.setFeaturePermission(url, feature, policy)

    def _certificate(self, error):
        r = QMessageBox.warning(self.parent().window(), T("cert"),
                                f"{error.url().host()}\n\n{error.description()}\n\n"
                                "Continue anyway? Only do this if you trust the network.",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        error.acceptCertificate() if r == QMessageBox.Yes else error.rejectCertificate()

    def _fullscreen(self, request):
        request.accept()
        w = self.parent().window()
        w.showFullScreen() if request.toggleOn() else w.showNormal()


class View(QWebEngineView):
    def __init__(self, window, profile):
        super().__init__()
        self.window_ = window
        self.setPage(Page(profile, self))

    def createWindow(self, kind):
        if kind == QWebEnginePage.WebWindowType.WebBrowserWindow:
            w = self.window_.app.new_window(private=self.window_.private)
            return w.add_tab(None)
        return self.window_.add_tab(None, focus=kind != QWebEnginePage.WebWindowType.WebBrowserBackgroundTab)


# ------------------------------------------------------------------ dialogs
class HistoryDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(T("history"))
        self.resize(720, 520)
        v = QVBoxLayout(self)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("…")
        self.filter.textChanged.connect(self.fill)
        v.addWidget(self.filter)
        self.list = QListWidget()
        self.list.itemActivated.connect(lambda it: (win.add_tab(QUrl(it.data(Qt.UserRole))), self.accept()))
        v.addWidget(self.list)
        row = QHBoxLayout()
        clear = QPushButton(T("clear"))
        clear.clicked.connect(self.clear)
        row.addWidget(clear)
        row.addStretch()
        close = QPushButton(T("close"))
        close.clicked.connect(self.accept)
        row.addWidget(close)
        v.addLayout(row)
        self.fill()

    def fill(self):
        q = self.filter.text().lower()
        self.list.clear()
        for h in reversed(self.win.app.store.history[-2000:]):
            if q and q not in h["url"].lower() and q not in h["title"].lower():
                continue
            when = dt.datetime.fromtimestamp(h["t"]).strftime("%d %b %H:%M")
            it = QListWidgetItem(f"{when}   {h['title']}\n        {h['url']}")
            it.setData(Qt.UserRole, h["url"])
            self.list.addItem(it)

    def clear(self):
        self.win.app.store.history = []
        self.win.app.store.save("history.json")
        self.win.app.profile.clearAllVisitedLinks()
        self.win.app.profile.clearHttpCache()
        self.fill()


class BookmarksDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle(T("bookmarks"))
        self.resize(640, 480)
        v = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.setDragDropMode(QListWidget.InternalMove)
        self.list.itemActivated.connect(lambda it: (win.add_tab(QUrl(it.data(Qt.UserRole)["url"])), self.accept()))
        for b in win.app.store.bookmarks:
            it = QListWidgetItem(f"{b['title']}\n    {b['url']}")
            it.setData(Qt.UserRole, b)
            self.list.addItem(it)
        v.addWidget(self.list)
        row = QHBoxLayout()
        rm = QPushButton(T("remove"))
        rm.clicked.connect(lambda: [self.list.takeItem(self.list.row(i)) for i in self.list.selectedItems()])
        row.addWidget(rm)
        row.addStretch()
        ok = QPushButton(T("close"))
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        v.addLayout(row)

    def accept(self):
        self.win.app.store.bookmarks = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]
        self.win.app.store.save("bookmarks.json")
        self.win.app.refresh_bookmarks()
        super().accept()


class DownloadsDialog(QDialog):
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle(T("downloads"))
        self.resize(620, 380)
        v = QVBoxLayout(self)
        self.box = QVBoxLayout()
        v.addLayout(self.box)
        v.addStretch()
        folder = QPushButton(T("open_folder"))
        folder.clicked.connect(lambda: subprocess.Popen(["xdg-open", app.download_dir()], start_new_session=True))
        v.addWidget(folder)

    def add(self, req):
        row = QWidget()
        h = QHBoxLayout(row)
        name = QLabel(req.downloadFileName())
        bar = QProgressBar()
        bar.setMaximumWidth(220)
        cancel = QToolButton()
        cancel.setIcon(icon("process-stop"))
        cancel.clicked.connect(req.cancel)
        h.addWidget(name, 1)
        h.addWidget(bar)
        h.addWidget(cancel)
        self.box.addWidget(row)

        def progress():
            total = req.totalBytes()
            bar.setRange(0, 100 if total > 0 else 0)
            if total > 0:
                bar.setValue(int(req.receivedBytes() * 100 / total))

        def done():
            if req.isFinished():
                bar.setRange(0, 100)
                bar.setValue(100)
                cancel.setIcon(icon("document-open"))
                cancel.clicked.disconnect()
                path = os.path.join(req.downloadDirectory(), req.downloadFileName())
                cancel.clicked.connect(lambda: subprocess.Popen(["xdg-open", path], start_new_session=True))
        req.receivedBytesChanged.connect(progress)
        req.isFinishedChanged.connect(done)
        self.show()
        self.raise_()


class SettingsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.store = win.app.store
        self.setWindowTitle(T("settings"))
        f = QFormLayout(self)
        self.engine = QComboBox()
        for k, (name, _, _) in SEARCH.items():
            self.engine.addItem(name, k)
        self.engine.setCurrentIndex(max(0, self.engine.findData(self.store.settings["search"])))
        self.home = QLineEdit("" if self.store.settings["home"] == "start" else self.store.settings["home"])
        self.home.setPlaceholderText("Credo")
        self.block = QCheckBox()
        self.block.setChecked(self.store.settings["block"])
        self.restore = QCheckBox()
        self.restore.setChecked(self.store.settings["restore"])
        self.lang = QComboBox()
        self.lang.addItem("English", "en")
        self.lang.addItem("Latina", "la")
        self.lang.setCurrentIndex(self.lang.findData(config.language()))
        f.addRow(T("search_engine"), self.engine)
        f.addRow(T("homepage"), self.home)
        f.addRow(T("block"), self.block)
        f.addRow(T("restore"), self.restore)
        f.addRow(T("language"), self.lang)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def accept(self):
        s = self.store.settings
        s["search"] = self.engine.currentData()
        s["home"] = self.home.text().strip() or "start"
        s["block"] = self.block.isChecked()
        s["restore"] = self.restore.isChecked()
        self.store.save("settings.json")
        if self.lang.currentData() != config.language():
            config.set_value("general", "language", self.lang.currentData())
        super().accept()


# ------------------------------------------------------------------ window
class TabStack(QWidget):
    """Pages in a stack, with a free-standing tab bar that the window puts in its tool bar
    (tabs as pills next to the address field, as in Safari and the Credo design)."""
    currentChanged = Signal(int)
    tabCloseRequested = Signal(int)

    def __init__(self):
        super().__init__()
        self.bar = QTabBar()
        self.bar.setObjectName("pills")
        self.bar.setDocumentMode(True)
        self.bar.setDrawBase(False)
        self.bar.setExpanding(False)
        self.bar.setTabsClosable(True)
        self.bar.setMovable(True)
        self.bar.setElideMode(Qt.ElideRight)
        self.bar.setUsesScrollButtons(True)
        self.stack = QStackedWidget()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.stack)
        self.bar.currentChanged.connect(self._current)
        self.bar.tabCloseRequested.connect(self.tabCloseRequested)
        self.bar.tabMoved.connect(self._moved)

    def _current(self, i):
        if 0 <= i < self.stack.count():
            self.stack.setCurrentIndex(i)
        self.currentChanged.emit(i)

    def _moved(self, a, b):
        w = self.stack.widget(a)
        self.stack.removeWidget(w)
        self.stack.insertWidget(b, w)
        self.stack.setCurrentIndex(self.bar.currentIndex())

    def insertTab(self, i, w, text):
        i = self.stack.insertWidget(i, w)
        self.bar.insertTab(i, text)
        return i

    def removeTab(self, i):
        w = self.stack.widget(i)
        self.stack.removeWidget(w)
        self.bar.removeTab(i)
        if self.bar.count():
            self.stack.setCurrentIndex(self.bar.currentIndex())

    def count(self): return self.bar.count()
    def currentIndex(self): return self.bar.currentIndex()
    def setCurrentIndex(self, i): self.bar.setCurrentIndex(i)
    def currentWidget(self): return self.stack.widget(self.bar.currentIndex())
    def widget(self, i): return self.stack.widget(i)
    def indexOf(self, w): return self.stack.indexOf(w)
    def setTabText(self, i, t): self.bar.setTabText(i, t)
    def setTabIcon(self, i, ic): self.bar.setTabIcon(i, ic)
    def setTabToolTip(self, i, t): self.bar.setTabToolTip(i, t)


class BrowserWindow(QMainWindow):
    def __init__(self, app, private=False):
        super().__init__()
        self.app, self.private = app, private
        self.profile = app.private_profile() if private else app.profile
        self.closed = []
        self.setWindowTitle("Credo Browser" + (f" — {T('private_title')}" if private else ""))
        self.setWindowIcon(icon("credo-browser"))
        self.resize(1280, 860)

        self.tabs = TabStack()
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.setCentralWidget(self.tabs)

        # Two rows on the window's glass: ‹ › ⟳ | address pill | ⌂ ★ ↓ ☰, then the tab pills below it.
        nav = QToolBar()
        nav.setObjectName("unified")
        nav.setMovable(False)
        nav.setIconSize(nav.iconSize() * 0.85)
        self.addToolBar(nav)
        self.a_back = nav.addAction(icon("go-previous"), T("back"), lambda: self.view().back())
        self.a_fwd = nav.addAction(icon("go-next"), T("forward"), lambda: self.view().forward())
        self.a_reload = nav.addAction(icon("view-refresh"), T("reload"), self.reload_or_stop)
        self.address = QLineEdit()
        self.address.setObjectName("address")
        self.address.setPlaceholderText(T("search_ph"))
        self.address.setClearButtonEnabled(True)
        self.address.setMinimumWidth(260)
        self.address.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.address.returnPressed.connect(self.navigate)
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.address.setCompleter(self.completer)
        nav.addWidget(self.address)
        nav.addAction(icon("go-home"), T("home"), lambda: self.view().setUrl(self.home_url()))
        self.a_star = nav.addAction(icon("bookmark-new"), T("bookmark_add"), self.toggle_bookmark)
        nav.addAction(icon("download"), T("downloads"), self.app.show_downloads)
        menu_btn = QToolButton()
        menu_btn.setIcon(icon("application-menu"))
        menu_btn.setPopupMode(QToolButton.InstantPopup)
        menu_btn.setMenu(self.build_menu())
        self.build_menubar()
        nav.addWidget(menu_btn)

        # Tab strip under the address bar.
        strip = QToolBar()
        strip.setObjectName("tabstrip")
        strip.setMovable(False)
        self.addToolBarBreak()
        self.addToolBar(strip)
        self.tabs.bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        strip.addWidget(self.tabs.bar)
        plus = QToolButton()
        plus.setIcon(icon("list-add"))
        plus.setToolTip(T("new_tab"))
        plus.setAutoRaise(True)
        plus.clicked.connect(lambda: self.add_tab(None))
        strip.addWidget(plus)

        self.progress = QProgressBar()
        self.progress.setMaximumHeight(3)
        self.progress.setTextVisible(False)
        self.progress.hide()

        self.bmbar = QToolBar()
        self.bmbar.setMovable(False)
        self.addToolBarBreak()
        self.addToolBar(self.bmbar)
        self.bmbar.setVisible(self.app.store.settings["bookmarks_bar"])

        self.findbar = QToolBar()
        self.findbar.setMovable(False)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText(T("find"))
        self.find_edit.textChanged.connect(lambda t: self.view().findText(t))
        self.find_edit.returnPressed.connect(lambda: self.view().findText(self.find_edit.text()))
        self.findbar.addWidget(self.find_edit)
        self.findbar.addAction(icon("go-up"), "↑", lambda: self.view().findText(
            self.find_edit.text(), QWebEnginePage.FindFlag.FindBackward))
        self.findbar.addAction(icon("go-down"), "↓", lambda: self.view().findText(self.find_edit.text()))
        self.findbar.addAction(icon("window-close"), T("close"), self.close_find)
        self.addToolBar(Qt.BottomToolBarArea, self.findbar)
        self.findbar.hide()

        self.statusBar().addPermanentWidget(self.progress, 1)
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().hide()

        for keys, fn in (("Ctrl+T", lambda: self.add_tab(None)), ("Ctrl+W", lambda: self.close_tab(self.tabs.currentIndex())),
                         ("Ctrl+Shift+T", self.reopen_tab), ("Ctrl+L", self.focus_address), ("F6", self.focus_address),
                         ("Alt+D", self.focus_address), ("Ctrl+Tab", lambda: self.cycle(1)),
                         ("Ctrl+Shift+Tab", lambda: self.cycle(-1)), ("Ctrl+PgDown", lambda: self.cycle(1)),
                         ("Ctrl+PgUp", lambda: self.cycle(-1)), ("Alt+Left", lambda: self.view().back()),
                         ("Alt+Right", lambda: self.view().forward()), ("F5", lambda: self.view().reload()),
                         ("Ctrl+R", lambda: self.view().reload()), ("Ctrl+F5", lambda: self.view().triggerPageAction(
                             QWebEnginePage.WebAction.ReloadAndBypassCache)),
                         ("Escape", self.on_escape), ("Ctrl+F", self.open_find), ("F3", lambda: self.view().findText(
                             self.find_edit.text())), ("Ctrl+D", self.toggle_bookmark),
                         ("Ctrl+H", lambda: HistoryDialog(self).exec()), ("Ctrl+J", self.app.show_downloads),
                         ("Ctrl+Shift+B", self.toggle_bmbar), ("Ctrl+N", lambda: self.app.new_window()),
                         ("Ctrl+Shift+N", lambda: self.app.new_window(private=True)), ("F11", self.toggle_fullscreen),
                         ("F12", self.devtools), ("Ctrl+Shift+I", self.devtools), ("Ctrl+P", self.print_pdf),
                         ("Ctrl+=", lambda: self.zoom(0.1)), ("Ctrl++", lambda: self.zoom(0.1)),
                         ("Ctrl+-", lambda: self.zoom(-0.1)), ("Ctrl+0", lambda: self.zoom(0)),
                         ("Alt+Home", lambda: self.view().setUrl(self.home_url())), ("Ctrl+Q", self.app.quit_all)):
            QShortcut(QKeySequence(keys), self, fn)
        for n in range(1, 10):
            QShortcut(QKeySequence(f"Ctrl+{n}"), self,
                      lambda n=n: self.tabs.setCurrentIndex(self.tabs.count() - 1 if n == 9 else n - 1))
        self.refresh_bookmarks()

    # ---- menu
    def build_menu(self):
        m = QMenu(self)
        m.addAction(icon("tab-new"), T("new_tab"), lambda: self.add_tab(None), QKeySequence("Ctrl+T"))
        m.addAction(icon("window-new"), T("new_window"), lambda: self.app.new_window(), QKeySequence("Ctrl+N"))
        m.addAction(icon("view-private"), T("private"), lambda: self.app.new_window(private=True),
                    QKeySequence("Ctrl+Shift+N"))
        m.addAction(icon("edit-undo"), T("reopen"), self.reopen_tab, QKeySequence("Ctrl+Shift+T"))
        m.addSeparator()
        credo = m.addMenu(icon("credo"), "Credo")
        for title, path in CREDO_PAGES:
            credo.addAction(title, lambda p=path: self.add_tab(QUrl(library_url(p))))
        self.bm_menu = m.addMenu(icon("bookmarks"), T("bookmarks"))
        m.addAction(icon("view-history"), T("history"), lambda: HistoryDialog(self).exec(), QKeySequence("Ctrl+H"))
        m.addAction(icon("download"), T("downloads"), self.app.show_downloads, QKeySequence("Ctrl+J"))
        m.addSeparator()
        m.addAction(icon("edit-find"), T("find"), self.open_find, QKeySequence("Ctrl+F"))
        m.addAction(icon("zoom-in"), T("zoom_in"), lambda: self.zoom(0.1), QKeySequence("Ctrl++"))
        m.addAction(icon("zoom-out"), T("zoom_out"), lambda: self.zoom(-0.1), QKeySequence("Ctrl+-"))
        m.addAction(icon("zoom-original"), T("zoom_reset"), lambda: self.zoom(0), QKeySequence("Ctrl+0"))
        m.addAction(icon("view-fullscreen"), T("fullscreen"), self.toggle_fullscreen, QKeySequence("F11"))
        m.addAction(icon("document-save-as"), T("print"), self.print_pdf, QKeySequence("Ctrl+P"))
        m.addAction(icon("tools"), T("devtools"), self.devtools, QKeySequence("F12"))
        m.addSeparator()
        m.addAction(icon("configure"), T("settings"), lambda: SettingsDialog(self).exec())
        m.addAction(icon("application-exit"), T("quit"), self.app.quit_all, QKeySequence("Ctrl+Q"))
        return m

    def build_menubar(self):
        """macOS-style application menus. Plasma shows them in the top bar (global menu), so the
        window itself stays clean. Shortcuts are handled by the window, so none are set here."""
        la = config.language() == "la"
        mb = self.menuBar()
        f = mb.addMenu("Fasciculus" if la else "File")
        f.addAction(T("new_tab"), lambda: self.add_tab(None))
        f.addAction(T("new_window"), lambda: self.app.new_window())
        f.addAction(T("private"), lambda: self.app.new_window(private=True))
        f.addAction(T("reopen"), self.reopen_tab)
        f.addSeparator()
        f.addAction(T("print"), self.print_pdf)
        f.addSeparator()
        f.addAction(T("quit"), self.app.quit_all)
        e = mb.addMenu("Recensio" if la else "Edit")
        e.addAction(T("find"), self.open_find)
        e.addAction(T("settings"), lambda: SettingsDialog(self).exec())
        v = mb.addMenu("Aspectus" if la else "View")
        v.addAction(T("zoom_in"), lambda: self.zoom(0.1))
        v.addAction(T("zoom_out"), lambda: self.zoom(-0.1))
        v.addAction(T("zoom_reset"), lambda: self.zoom(0))
        v.addSeparator()
        v.addAction(T("fullscreen"), self.toggle_fullscreen)
        v.addAction(T("devtools"), self.devtools)
        h = mb.addMenu(T("history"))
        h.addAction(T("history") + "…", lambda: HistoryDialog(self).exec())
        h.addAction(T("downloads"), self.app.show_downloads)
        mb.addMenu(self.bm_menu)
        c = mb.addMenu("Credo")
        for title, path in CREDO_PAGES:
            c.addAction(title, lambda p=path: self.add_tab(QUrl(library_url(p))))
        w = mb.addMenu("Fenestra" if la else "Window")
        w.addAction("Minue" if la else "Minimize", self.showMinimized)
        w.addAction(T("new_window"), lambda: self.app.new_window())
        hp = mb.addMenu("Auxilium" if la else "Help")
        hp.addAction("Credo Center", lambda: subprocess.Popen(["credo-center"], start_new_session=True))

    def refresh_bookmarks(self):
        store = self.app.store
        self.bmbar.clear()
        self.bm_menu.clear()
        self.bm_menu.addAction(icon("bookmark-new"), T("bookmark_add"), self.toggle_bookmark, QKeySequence("Ctrl+D"))
        a = self.bm_menu.addAction(T("bookmarks_bar"), self.toggle_bmbar)
        a.setCheckable(True)
        a.setChecked(store.settings["bookmarks_bar"])
        self.bm_menu.addAction(T("manage_bookmarks"), lambda: BookmarksDialog(self).exec())
        self.bm_menu.addSeparator()
        for b in store.bookmarks:
            title = b["title"] if len(b["title"]) < 48 else b["title"][:46] + "…"
            self.bm_menu.addAction(title, lambda u=b["url"]: self.add_tab(QUrl(u)))
            short = re.sub(r"\s*\(.*\)$", "", b["title"])
            short = short if len(short) < 24 else short[:22] + "…"
            self.bmbar.addAction(short, lambda u=b["url"]: self.view().setUrl(QUrl(u)))
        urls = {b["url"] for b in store.bookmarks} | {h["url"] for h in store.history[-1500:]}
        self.completer.model().setStringList(sorted(urls))      # QCompleter(list) uses a QStringListModel
        self.update_star()

    # ---- tabs
    def view(self):
        return self.tabs.currentWidget()

    def home_url(self):
        h = self.app.store.settings["home"]
        return start_page(self.app.store) if h == "start" else to_url(h, self.app.store)

    def add_tab(self, url, focus=True):
        v = View(self, self.profile)
        v.titleChanged.connect(lambda t, v=v: self.title_changed(v, t))
        v.iconChanged.connect(lambda i, v=v: self.tabs.setTabIcon(self.tabs.indexOf(v), i))
        v.urlChanged.connect(lambda u, v=v: self.url_changed(v, u))
        v.loadStarted.connect(lambda v=v: self.load_state(v, True))
        v.loadProgress.connect(lambda p, v=v: self.load_progress(v, p))
        v.loadFinished.connect(lambda ok, v=v: self.load_finished(v))
        v.page().linkHovered.connect(lambda link: (self.statusBar().showMessage(link) if link
                                                  else self.statusBar().clearMessage()))
        idx = self.tabs.insertTab(self.tabs.currentIndex() + 1 if self.tabs.count() else 0, v, "…")
        if url is not None:
            v.setUrl(url)
        if focus:
            self.tabs.setCurrentIndex(idx)
            if url is None or url.isLocalFile():
                QTimer.singleShot(0, self.focus_address)
        return v

    def close_tab(self, i):
        v = self.tabs.widget(i)
        if v is None:
            return
        if not v.url().isEmpty():
            self.closed.append(v.url())
        self.tabs.removeTab(i)
        v.deleteLater()
        if self.tabs.count() == 0:
            self.close()

    def reopen_tab(self):
        if self.closed:
            self.add_tab(self.closed.pop())

    def cycle(self, d):
        if self.tabs.count():
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + d) % self.tabs.count())

    def tab_changed(self, _i):
        v = self.view()
        if v is None:
            return
        self.show_url(v.url())
        self.setWindowTitle((v.title() or "Credo Browser") + (f" — {T('private_title')}" if self.private else ""))
        self.update_nav()

    def title_changed(self, v, t):
        i = self.tabs.indexOf(v)
        self.tabs.setTabText(i, (t[:28] + "…") if len(t) > 29 else (t or "…"))
        self.tabs.setTabToolTip(i, t)
        if v is self.view():
            self.setWindowTitle(t + (f" — {T('private_title')}" if self.private else ""))

    def url_changed(self, v, u):
        if v is self.view():
            self.show_url(u)
            self.update_nav()

    def show_url(self, u):
        if u.isLocalFile() and u.toLocalFile().endswith("start.html"):
            self.address.clear()
        elif not self.address.hasFocus():
            self.address.setText(u.toString())
            self.address.setCursorPosition(0)
        self.update_star()

    def load_state(self, v, loading):
        if v is self.view():
            self.a_reload.setIcon(icon("process-stop" if loading else "view-refresh"))
            self.a_reload.setText(T("stop" if loading else "reload"))

    def load_progress(self, v, p):
        if v is self.view():
            self.statusBar().show()
            self.progress.show()
            self.progress.setValue(p)

    def load_finished(self, v):
        self.load_state(v, False)
        if v is self.view():
            self.progress.hide()
            self.statusBar().hide()
        if not self.private:
            self.app.store.add_history(v.url().toString(), v.title())
        self.update_nav()

    def update_nav(self):
        v = self.view()
        if v:
            self.a_back.setEnabled(v.history().canGoBack())
            self.a_fwd.setEnabled(v.history().canGoForward())

    def reload_or_stop(self):
        v = self.view()
        if self.a_reload.text() == T("stop"):
            v.stop()
        else:
            v.reload()

    # ---- address, bookmarks, find
    def focus_address(self):
        self.address.setFocus()
        self.address.selectAll()

    def navigate(self):
        u = to_url(self.address.text(), self.app.store)
        if u:
            self.view().setUrl(u)
            self.view().setFocus()

    def update_star(self):
        v = self.view()
        on = bool(v) and self.app.store.is_bookmarked(v.url().toString())
        self.a_star.setIcon(icon("bookmarks" if on else "bookmark-new"))

    def toggle_bookmark(self):
        v = self.view()
        if v and not v.url().isLocalFile():
            self.app.store.toggle_bookmark(v.url().toString(), v.title())
            self.app.refresh_bookmarks()

    def toggle_bmbar(self):
        s = self.app.store.settings
        s["bookmarks_bar"] = not s["bookmarks_bar"]
        self.app.store.save("settings.json")
        for w in self.app.windows:
            w.bmbar.setVisible(s["bookmarks_bar"])

    def open_find(self):
        self.findbar.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def close_find(self):
        self.findbar.hide()
        self.view().findText("")
        self.view().setFocus()

    def on_escape(self):
        if self.findbar.isVisible():
            self.close_find()
        elif self.address.hasFocus():
            self.show_url(self.view().url())
            self.view().setFocus()
        else:
            self.view().stop()

    # ---- page tools
    def zoom(self, d):
        v = self.view()
        v.setZoomFactor(1.0 if d == 0 else max(0.3, min(4.0, v.zoomFactor() + d)))

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def devtools(self):
        v = self.view()
        dev = QWebEngineView()
        dev.setWindowTitle(f"{T('devtools')} — {v.title()}")
        dev.resize(1000, 700)
        v.page().setDevToolsPage(dev.page())
        dev.show()
        self.app.keep.append(dev)

    def print_pdf(self):
        v = self.view()
        name = re.sub(r"[^\w .-]", "", v.title() or "page").strip() or "page"
        path, _ = QFileDialog.getSaveFileName(self, T("print"), os.path.join(self.app.download_dir(), name + ".pdf"),
                                              "PDF (*.pdf)")
        if path:
            v.page().printToPdf(path)

    def closeEvent(self, e):
        if not self.private:
            self.app.save_session(self)
        self.app.windows.remove(self) if self in self.app.windows else None
        super().closeEvent(e)


# ------------------------------------------------------------------ application
class Browser:
    def __init__(self, qapp):
        self.qapp = qapp
        self.store = Store()
        self.windows, self.keep = [], []
        self.downloads = None
        DATA.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile("credo", qapp)
        self.profile.setPersistentStoragePath(str(DATA / "profile"))
        self.profile.setCachePath(str(DATA / "cache"))
        self.profile.setHttpUserAgent(self.profile.httpUserAgent().replace("QtWebEngine", "CredoBrowser QtWebEngine"))
        self._setup(self.profile)
        self._private = None

    def _setup(self, profile):
        self.interceptor = getattr(self, "interceptor", None) or Interceptor(self.store)
        profile.setUrlRequestInterceptor(self.interceptor)
        profile.downloadRequested.connect(self.download)
        s = profile.settings()
        for attr in ("FullScreenSupportEnabled", "PdfViewerEnabled", "ScrollAnimatorEnabled",
                     "DnsPrefetchEnabled", "LocalContentCanAccessRemoteUrls"):
            if hasattr(QWebEngineSettings.WebAttribute, attr):
                s.setAttribute(getattr(QWebEngineSettings.WebAttribute, attr), True)

    def private_profile(self):
        if self._private is None:
            self._private = QWebEngineProfile(self.qapp)          # off the record: nothing on disk
            self._setup(self._private)
        return self._private

    def download_dir(self):
        return QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or str(pathlib.Path.home())

    def download(self, req):
        if req.state() != QWebEngineDownloadRequest.DownloadState.DownloadRequested:
            return
        path, _ = QFileDialog.getSaveFileName(None, T("downloads"),
                                              os.path.join(self.download_dir(), req.downloadFileName()))
        if not path:
            req.cancel()
            return
        req.setDownloadDirectory(os.path.dirname(path))
        req.setDownloadFileName(os.path.basename(path))
        req.accept()
        self.show_downloads().add(req)

    def show_downloads(self):
        if self.downloads is None:
            self.downloads = DownloadsDialog(self)
        self.downloads.show()
        self.downloads.raise_()
        return self.downloads

    def new_window(self, urls=(), private=False):
        w = BrowserWindow(self, private)
        self.windows.append(w)
        if urls:
            for u in urls:
                w.add_tab(u)
        else:
            w.add_tab(w.home_url())
        w.show()
        return w

    def refresh_bookmarks(self):
        for w in self.windows:
            w.refresh_bookmarks()

    def open_urls(self, args, private=False):
        urls = [to_url(a, self.store) for a in args if a]
        urls = [u for u in urls if u]
        normal = [w for w in self.windows if not w.private]
        if urls and normal and not private:
            w = normal[-1]
            for u in urls:
                w.add_tab(u)
            w.show()
            w.raise_()
            w.activateWindow()
        else:
            self.new_window(urls, private)

    def save_session(self, w):
        tabs = [w.tabs.widget(i).url().toString() for i in range(w.tabs.count())]
        tabs = [t for t in tabs if t and not t.endswith("start.html")]
        STATE.write_text(json.dumps({"tabs": tabs}), encoding="utf-8")

    def restore_urls(self):
        if not self.store.settings.get("restore"):
            return []
        try:
            return [QUrl(u) for u in json.loads(STATE.read_text(encoding="utf-8")).get("tabs", [])]
        except (OSError, ValueError):
            return []

    def quit_all(self):
        for w in list(self.windows):
            w.close()
        self.store.save("history.json")
        self.qapp.quit()


def stylesheet():
    try:
        _, p = palettes.resolve(config.load().get("appearance", "variant", fallback="monastic"))
    except Exception:
        return ""
    # Tabs as pills and a pill address field on the window's glass (see the Credo design).
    fg = p["fg"]
    return (f"QToolBar#unified {{ border:none; background:transparent; spacing:6px; padding:5px 10px 3px; }}"
            f"QToolBar#tabstrip {{ border:none; background:transparent; spacing:4px; padding:0 10px 5px; }}"
            f"QToolBar#unified QToolButton, QToolBar#tabstrip QToolButton {{ background:transparent; border:none;"
            f" border-radius:7px; padding:3px; }}"
            f"QToolBar#unified QToolButton:hover, QToolBar#tabstrip QToolButton:hover"
            f" {{ background:rgba(255,255,255,0.08); }}"
            f"QToolBar#unified QToolButton::menu-indicator {{ image:none; width:0; }}"
            f"QLineEdit {{ border-radius:9px; padding:4px 12px; border:1px solid rgba(255,255,255,0.10); }}"
            f"QLineEdit#address {{ background:rgba(255,255,255,0.07); color:{fg}; min-height:20px; }}"
            f"QLineEdit:focus {{ border:1px solid {p['logo']}; }}"
            f"QProgressBar {{ border:none; background:transparent; }}"
            f"QProgressBar::chunk {{ background:{p['logo']}; }}"
            f"QTabBar#pills {{ background:transparent; }}"
            f"QTabBar#pills::tab {{ background:transparent; color:{p['fg_dim']}; border:none; border-radius:9px;"
            f" padding:4px 10px; margin:2px 2px; min-width:120px; max-width:220px; }}"
            f"QTabBar#pills::tab:hover {{ background:rgba(255,255,255,0.06); color:{fg}; }}"
            f"QTabBar#pills::tab:selected {{ background:rgba(255,255,255,0.14); color:{fg}; font-weight:600; }}")


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    private = "--private" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    sock_name = f"{APP_ID}-{os.getuid() if hasattr(os, 'getuid') else 0}"

    qapp = QApplication(argv)
    # One browser process: hand the URLs to a running window.
    s = QLocalSocket()
    s.connectToServer(sock_name)
    if s.waitForConnected(300):
        s.write(json.dumps({"urls": args, "private": private}).encode())
        s.waitForBytesWritten(1000)
        s.disconnectFromServer()
        return 0

    qapp.setApplicationName("Credo Browser")
    qapp.setDesktopFileName(APP_ID)
    qapp.setWindowIcon(icon("credo-browser"))
    qapp.setStyleSheet(stylesheet())
    ensure_library_server()
    browser = Browser(qapp)

    server = QLocalServer()
    QLocalServer.removeServer(sock_name)
    server.listen(sock_name)

    def incoming():
        c = server.nextPendingConnection()
        c.waitForReadyRead(1000)
        try:
            msg = json.loads(bytes(c.readAll()).decode() or "{}")
        except ValueError:
            msg = {}
        browser.open_urls(msg.get("urls", []), msg.get("private", False))
    server.newConnection.connect(incoming)

    if args or private:
        browser.open_urls(args, private)
    else:
        restored = browser.restore_urls()
        browser.new_window(restored)
    qapp.aboutToQuit.connect(lambda: browser.store.save("history.json"))
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
