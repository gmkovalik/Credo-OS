"""Credo Apps: all applications on one full-screen glass page (the app grid).

A blurred copy of the wallpaper, a glass search pill, and a grid of every installed app.
Type to search, Enter or click to launch, Esc or a click on empty space to close.
Running it again while it is open closes it (it toggles).

    credo-launchpad
"""
import configparser
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QSize, Qt, QUrl, Slot, QObject, Property, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QIcon, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

from . import config

SOCKET = f"credo-launchpad-{os.getuid() if hasattr(os, 'getuid') else 0}"


# ------------------------------------------------------------------ applications
def app_dirs():
    data_home = os.environ.get("XDG_DATA_HOME") or str(pathlib.Path.home() / ".local/share")
    dirs = [data_home] + (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    dirs += ["/var/lib/flatpak/exports/share", str(pathlib.Path.home() / ".local/share/flatpak/exports/share")]
    seen, out = set(), []
    for d in dirs:
        p = pathlib.Path(d) / "applications"
        if p.is_dir() and str(p) not in seen:
            seen.add(str(p))
            out.append(p)
    return out


def localized(entry, key, lang):
    for k in (f"{key}[{lang}]", key):
        if k in entry and entry[k]:
            return entry[k]
    return ""


def load_apps():
    lang = config.language()
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or "KDE").split(":")
    apps, ids = [], set()
    for d in app_dirs():
        for f in sorted(d.rglob("*.desktop")):
            app_id = str(f.relative_to(d)).replace("/", "-")
            if app_id in ids:
                continue                      # earlier directories win (user overrides system)
            ids.add(app_id)
            cp = configparser.RawConfigParser(strict=False, interpolation=None)
            cp.optionxform = str
            try:
                cp.read(f, encoding="utf-8")
                e = cp["Desktop Entry"]
            except Exception:
                continue
            if e.get("Type") != "Application" or e.get("NoDisplay") == "true" or e.get("Hidden") == "true":
                continue
            only = [x for x in e.get("OnlyShowIn", "").split(";") if x]
            never = [x for x in e.get("NotShowIn", "").split(";") if x]
            if (only and not set(only) & set(desktop)) or set(never) & set(desktop):
                continue
            name = localized(e, "Name", lang)
            if not name or not e.get("Exec"):
                continue
            apps.append({"id": app_id, "name": name, "icon": e.get("Icon", "application-x-executable"),
                         "keywords": " ".join((localized(e, "GenericName", lang), localized(e, "Comment", lang),
                                               localized(e, "Keywords", lang), app_id)).lower(),
                         "path": str(f), "exec": e.get("Exec", ""), "terminal": e.get("Terminal") == "true"})
    apps.sort(key=lambda a: a["name"].lower())
    return apps


def launch(app):
    for cmd in (["kioclient", "exec", app["path"]], ["gio", "launch", app["path"]],
                ["gtk-launch", app["id"].removesuffix(".desktop")]):
        if shutil.which(cmd[0]):
            subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
    args = [a for a in shlex.split(app["exec"]) if not re.fullmatch(r"%[a-zA-Z]", a)]
    if args:
        subprocess.Popen(args, start_new_session=True)


class AppModel(QAbstractListModel):
    NameRole, IconRole, IndexRole = Qt.UserRole + 1, Qt.UserRole + 2, Qt.UserRole + 3

    def __init__(self, apps):
        super().__init__()
        self.all = apps
        self.shown = list(range(len(apps)))

    def rowCount(self, parent=QModelIndex()):
        return len(self.shown)

    def data(self, index, role):
        a = self.all[self.shown[index.row()]]
        if role == self.NameRole:
            return a["name"]
        if role == self.IconRole:
            return a["icon"]
        if role == self.IndexRole:
            return self.shown[index.row()]
        return None

    def roleNames(self):
        return {self.NameRole: QByteArray(b"name"), self.IconRole: QByteArray(b"iconName"),
                self.IndexRole: QByteArray(b"appIndex")}

    def filter(self, text):
        t = text.strip().lower()
        self.beginResetModel()
        if not t:
            self.shown = list(range(len(self.all)))
        else:
            starts = [i for i, a in enumerate(self.all) if a["name"].lower().startswith(t)]
            other = [i for i, a in enumerate(self.all)
                     if i not in starts and (t in a["name"].lower() or t in a["keywords"])]
            self.shown = starts + other
        self.endResetModel()


class Backend(QObject):
    countChanged = Signal()

    def __init__(self, model, app):
        super().__init__()
        self.model, self.app = model, app

    @Slot(str)
    def search(self, text):
        self.model.filter(text)
        self.countChanged.emit()

    @Slot(int)
    def launch(self, app_index):
        launch(self.model.all[app_index])
        self.app.quit()

    @Slot()
    def launchFirst(self):
        if self.model.shown:
            self.launch(self.model.shown[0])

    @Slot()
    def close(self):
        self.app.quit()

    def _count(self):
        return len(self.model.shown)
    count = Property(int, _count, notify=countChanged)


def icon_index():
    """name -> icon file, from the Credo, Breeze and hicolor themes and pixmaps (Credo wins, then
    scalable, then the biggest size). Built once in Python: a QML image provider written in Python
    deadlocked Launchpad (Qt's image loader thread waited on Python while Python waited on Qt)."""
    bases = [pathlib.Path(d) for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")]
    bases = [pathlib.Path.home() / ".local/share", pathlib.Path("/var/lib/flatpak/exports/share"),
             pathlib.Path.home() / ".local/share/flatpak/exports/share"] + bases
    best = {}

    def rank(theme, path):
        size = 4096 if "scalable" in path.parts else max([int(x) for x in re.findall(r"(\d+)", str(path.parent))] or [0])
        return ({"Credo": 3, "breeze-dark": 2, "breeze": 2, "hicolor": 1}.get(theme, 0), size)
    for base in bases:
        for theme in ("Credo", "breeze-dark", "breeze", "hicolor"):
            d = base / "icons" / theme
            if not d.is_dir():
                continue
            for p in d.rglob("*"):
                if p.suffix not in (".svg", ".png") or "apps" not in p.parts and "places" not in p.parts:
                    continue
                r = rank(theme, p)
                if p.stem not in best or r > best[p.stem][0]:
                    best[p.stem] = (r, str(p))
        pix = base / "pixmaps"
        if pix.is_dir():
            for p in pix.glob("*.*"):
                if p.suffix in (".svg", ".png") and p.stem not in best:
                    best[p.stem] = ((0, 0), str(p))
    return {k: v[1] for k, v in best.items()}


def icon_url(name, index):
    if name.startswith("/") and pathlib.Path(name).is_file():
        return QUrl.fromLocalFile(name).toString()
    p = index.get(name) or index.get(name.removesuffix(".png").removesuffix(".svg")) \
        or index.get("application-x-executable")
    return QUrl.fromLocalFile(p).toString() if p else ""


class IconProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Pixmap)

    @staticmethod
    def find_file(name):
        """Fallback when the icon theme lookup fails: look in the Credo, hicolor and pixmap folders."""
        for base in [pathlib.Path(d) for d in (os.environ.get("XDG_DATA_DIRS") or "/usr/share").split(":")] \
                + [pathlib.Path.home() / ".local/share"]:
            for sub in ("icons/Credo/scalable/apps", "icons/hicolor/scalable/apps", "icons/hicolor/256x256/apps",
                        "icons/hicolor/128x128/apps", "icons/hicolor/48x48/apps", "pixmaps"):
                for ext in (".svg", ".png"):
                    p = base / sub / f"{name}{ext}"
                    if p.is_file():
                        return str(p)
        return None

    def requestPixmap(self, name, size, requested):
        s = requested.width() if requested.width() > 0 else 128
        icon = QIcon(name) if name.startswith("/") else QIcon.fromTheme(name)
        if icon.isNull() and not name.startswith("/"):
            f = self.find_file(name)
            icon = QIcon(f) if f else QIcon.fromTheme("application-x-executable")
        pm = icon.pixmap(QSize(s, s))
        if size is not None:
            size.setWidth(pm.width())
            size.setHeight(pm.height())
        return pm


def wallpaper():
    """The wallpaper currently on the desktop (for the blurred backdrop)."""
    rc = pathlib.Path.home() / ".config/plasma-org.kde.plasma.desktop-appletsrc"
    try:
        m = re.findall(r"^Image=(?:file://)?(.+)$", rc.read_text(encoding="utf-8"), re.M)
        for p in m:
            if pathlib.Path(p).is_file():
                return p
    except OSError:
        pass
    for p in sorted((config.DATA_DIR / "theme").glob("wallpaper-*.png")):
        return str(p)
    return "/usr/share/wallpapers/Credo/contents/images/2880x1800.png"


QML = r"""
import QtQuick
import QtQuick.Effects
import QtQuick.Window

Window {
    id: win
    visible: false                           // shown full screen from Python once loaded
    color: "transparent"
    flags: Qt.FramelessWindowHint
    title: "Apps"

    readonly property int cell: Math.max(128, Math.min(170, width / 9))

    Image {                                  // blurred wallpaper
        id: wall
        anchors.fill: parent
        source: wallpaperUrl
        fillMode: Image.PreserveAspectCrop
        visible: false
    }
    MultiEffect {
        anchors.fill: parent
        source: wall
        blurEnabled: true
        blur: 1.0
        blurMax: 64
        saturation: 0.15
        brightness: -0.12
    }
    Rectangle { anchors.fill: parent; color: Qt.rgba(0.05, 0.06, 0.05, 0.35) }

    MouseArea { anchors.fill: parent; onClicked: backend.close() }   // click on empty space closes

    // ---- glass search pill
    Rectangle {
        id: pill
        anchors.horizontalCenter: parent.horizontalCenter
        y: 56
        width: 360; height: 40; radius: 20
        color: Qt.rgba(1, 1, 1, 0.16)   // flat glass, no gradient
        border.color: Qt.rgba(1, 1, 1, 0.32)
        Text { x: 16; anchors.verticalCenter: parent.verticalCenter; text: "⌕"; color: Qt.rgba(1,1,1,0.7); font.pixelSize: 20 }
        TextInput {
            id: search
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 42; rightMargin: 16 }
            color: "white"
            font.pixelSize: 16
            focus: true
            selectByMouse: true
            onTextChanged: backend.search(text)
            Keys.onReturnPressed: backend.launchFirst()
            Keys.onEnterPressed: backend.launchFirst()
            Keys.onEscapePressed: text.length ? text = "" : backend.close()
            Text {
                anchors.fill: parent
                verticalAlignment: Text.AlignVCenter
                text: placeholder
                color: Qt.rgba(1, 1, 1, 0.5)
                font.pixelSize: 16
                visible: !search.text.length
            }
        }
    }

    // ---- app grid
    GridView {
        id: grid
        anchors { top: pill.bottom; topMargin: 40; bottom: parent.bottom; bottomMargin: 40
                  horizontalCenter: parent.horizontalCenter }
        width: Math.floor((parent.width - 160) / win.cell) * win.cell
        cellWidth: win.cell
        cellHeight: win.cell
        clip: true
        model: appModel
        boundsBehavior: Flickable.StopAtBounds
        delegate: Item {
            width: win.cell; height: win.cell
            Column {
                anchors.centerIn: parent
                spacing: 8
                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Math.round(win.cell * 0.52); height: width
                    sourceSize: Qt.size(width * 2, width * 2)
                    source: iconName
                    asynchronous: true
                    scale: hover.hovered ? 1.08 : 1.0
                    Behavior on scale { NumberAnimation { duration: 120 } }
                }
                Text {
                    width: win.cell - 16
                    horizontalAlignment: Text.AlignHCenter
                    text: name
                    color: "white"
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    style: Text.Raised; styleColor: Qt.rgba(0, 0, 0, 0.35)
                }
            }
            HoverHandler { id: hover }
            TapHandler { onTapped: backend.launch(appIndex) }
        }
        Text {
            anchors.centerIn: parent
            visible: backend.count === 0
            text: nothing
            color: Qt.rgba(1, 1, 1, 0.7)
            font.pixelSize: 16
        }
    }

    Shortcut { sequence: "Escape"; onActivated: backend.close() }
    Component.onCompleted: { requestActivate(); search.forceActiveFocus() }
}
"""


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QGuiApplication(argv)
    app.setApplicationName("Credo Apps")
    app.setDesktopFileName("credo-launchpad")

    # Toggle: if Launchpad is open, ask it to close and exit.
    # A running Launchpad answers "bye" and closes. One that does not answer is stuck: end it and
    # open a fresh one (before this, a stuck copy made every dock click silently do nothing).
    pidfile = pathlib.Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp") / f"{SOCKET}.pid"
    s = QLocalSocket()
    s.connectToServer(SOCKET)
    if s.waitForConnected(300):
        s.write(b"close")
        s.waitForBytesWritten(500)
        if s.waitForReadyRead(1200):
            return 0
        try:
            os.kill(int(pidfile.read_text()), 9)
        except (OSError, ValueError):
            pass
    server = QLocalServer()
    QLocalServer.removeServer(SOCKET)
    server.listen(SOCKET)

    def answer():
        c = server.nextPendingConnection()
        if c:
            c.write(b"bye")
            c.flush()
            c.waitForBytesWritten(300)
        app.quit()
    server.newConnection.connect(answer)
    try:
        pidfile.write_text(str(os.getpid()))
    except OSError:
        pass

    apps = load_apps()
    index = icon_index()
    for a in apps:
        a["icon"] = icon_url(a["icon"], index)
    model = AppModel(apps)
    backend = Backend(model, app)
    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    la = config.language() == "la"
    ctx.setContextProperty("appModel", model)
    ctx.setContextProperty("backend", backend)
    ctx.setContextProperty("wallpaperUrl", QUrl.fromLocalFile(wallpaper()))
    ctx.setContextProperty("placeholder", "Quaere applicationes" if la else "Search")
    ctx.setContextProperty("nothing", "Nihil inventum" if la else "No results")
    engine.loadData(QML.encode("utf-8"))
    if not engine.rootObjects():
        return 1
    # Show it explicitly: on Wayland a QML Window declared "visible + FullScreen" could stay unmapped
    # (Launchpad ran but nothing appeared). Cover the screen the pointer is on.
    win = engine.rootObjects()[0]
    screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
    if screen:
        win.setScreen(screen)
        win.setGeometry(screen.geometry())
    win.showFullScreen()
    win.raise_()
    win.requestActivate()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
