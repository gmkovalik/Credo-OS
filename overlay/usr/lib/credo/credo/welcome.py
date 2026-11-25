"""Credo Welcome: the first-run tour of Credo OS (replaces KDE's Welcome Center).

Six short pages: welcome and language, light or dark look, prayer, your apps, safety, done.
Nothing here rebuilds the desktop: the look is changed with the colour scheme, icons and
window style only (the wallpaper, panels and widgets are left as they are).

    credo-welcome              open the tour
    credo-welcome --first-run  open it only if it has not been finished yet (used at login)
"""
import shutil
import subprocess
import sys

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QStackedWidget, QToolButton, QVBoxLayout, QWidget)

from . import config, palettes

LOGO = "/usr/share/credo/logos/chirho-ring.svg"


def T(en, la):
    return la if config.language() == "la" else en


def run(*cmd):
    if shutil.which(cmd[0]):
        subprocess.Popen(list(cmd), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def logo_pixmap(size, color="#ffffff"):
    try:
        svg = open(LOGO, encoding="utf-8").read().replace("currentColor", color)
    except OSError:
        return QPixmap()
    pm = QPixmap()
    pm.loadFromData(QByteArray(svg.encode()), "SVG")
    return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


# ------------------------------------------------------------------ actions
def set_language(lang):
    from .center import set_desktop_language
    config.set_value("general", "language", lang)
    set_desktop_language(lang)


def set_look(dark):
    """Light or dark: colour scheme, icons, window buttons and GTK apps (not wallpaper or panels)."""
    from . import theme
    variant = "monastic" if dark else "ivory"
    name, pal = palettes.resolve(variant)
    try:
        d = config.HOME / ".local/share/color-schemes"
        theme.write_scheme(name, pal, d)
    except Exception:
        pass
    kw = shutil.which("kwriteconfig6") or shutil.which("kwriteconfig5")
    icons, deco = ("Credo", "Credo") if dark else ("Credo-Light", "Credo-Light")
    # a different scheme first: plasma-apply-colorscheme ignores the one already set
    subprocess.run(["plasma-apply-colorscheme", "BreezeLight" if dark else "BreezeDark"], capture_output=True)
    subprocess.run(["plasma-apply-colorscheme", f"Credo{name}"], capture_output=True)
    if kw:
        subprocess.run([kw, "--file", "kdeglobals", "--group", "Icons", "--key", "Theme", icons])
        subprocess.run([kw, "--file", "kwinrc", "--group", "org.kde.kdecoration2", "--key", "theme",
                        f"__aurorae__svg__{deco}"])
    if shutil.which("/usr/libexec/plasma-changeicons"):
        subprocess.run(["/usr/libexec/plasma-changeicons", icons], capture_output=True)
    subprocess.run(["dbus-send", "--session", "--type=method_call", "--dest=org.kde.KWin", "/KWin",
                    "org.kde.KWin.reconfigure"], capture_output=True)
    if shutil.which("gsettings"):
        for k, v in (("gtk-theme", icons), ("icon-theme", icons),
                     ("color-scheme", "prefer-dark" if dark else "prefer-light")):
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", k, v], capture_output=True)
    config.set_value("appearance", "variant", variant)


def angelus(on):
    subprocess.run(["systemctl", "--user", "enable" if on else "disable", "--now", "credo-angelus.timer"],
                   capture_output=True)


def angelus_on():
    r = subprocess.run(["systemctl", "--user", "is-enabled", "credo-angelus.timer"], capture_output=True, text=True)
    return r.stdout.strip() == "enabled"


# ------------------------------------------------------------------ pieces
CSS = """
QMainWindow { background: palette(window); }
QLabel#title { font-size: 26px; font-weight: 600; }
QLabel#lead { font-size: 14px; color: palette(placeholder-text); }
QToolButton[class="card"] {
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px;
  padding: 14px; font-size: 13px; font-weight: 600; }
QToolButton[class="card"]:hover { background: rgba(255,255,255,0.11); }
QToolButton[class="card"]:checked { border: 2px solid #c9a85a; background: rgba(201,168,90,0.14); }
QPushButton#next { background: #c9a85a; color: #17211c; border: none; border-radius: 9px; padding: 8px 22px;
  font-weight: 700; }
QPushButton#back { border-radius: 9px; padding: 8px 18px; }
QLabel[class="dot"] { color: rgba(255,255,255,0.25); font-size: 18px; }
QLabel[class="dot"][on="true"] { color: #c9a85a; }
"""


def card(text, icon, slot, checkable=False, size=56):
    b = QToolButton()
    b.setProperty("class", "card")
    b.setText(text)
    b.setIcon(QIcon.fromTheme(icon))
    b.setIconSize(QSize(size, size))
    b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
    b.setCheckable(checkable)
    b.setMinimumSize(150, 120)
    b.clicked.connect(slot)
    return b


def page(title, lead, body=None, logo=False):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(56, 40, 56, 12)
    v.setSpacing(14)
    if logo:
        lg = QLabel()
        lg.setPixmap(logo_pixmap(120, "#c9a85a"))
        lg.setAlignment(Qt.AlignHCenter)
        v.addWidget(lg)
    t = QLabel(title)
    t.setObjectName("title")
    t.setAlignment(Qt.AlignHCenter)
    t.setWordWrap(True)
    v.addWidget(t)
    ld = QLabel(lead)
    ld.setObjectName("lead")
    ld.setAlignment(Qt.AlignHCenter)
    ld.setWordWrap(True)
    v.addWidget(ld)
    v.addSpacing(10)
    if body is not None:
        v.addWidget(body, 1)
    v.addStretch()
    return w


def grid(cards, cols=3):
    w = QWidget()
    g = QGridLayout(w)
    g.setSpacing(14)
    for i, c in enumerate(cards):
        g.addWidget(c, i // cols, i % cols)
    return w


# ------------------------------------------------------------------ window
class Welcome(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Welcome to Credo OS", "Salve in Credo OS"))
        self.setWindowIcon(QIcon.fromTheme("credo"))
        self.resize(860, 620)
        self.stack = QStackedWidget()
        self.build()
        nav = QHBoxLayout()
        nav.setContentsMargins(56, 8, 56, 28)
        self.back = QPushButton(T("Back", "Retro"))
        self.back.setObjectName("back")
        self.back.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
        self.dots = []
        nav.addWidget(self.back)
        nav.addStretch()
        for _ in range(self.stack.count()):
            d = QLabel("●")
            d.setProperty("class", "dot")
            self.dots.append(d)
            nav.addWidget(d)
        nav.addStretch()
        self.next = QPushButton()
        self.next.setObjectName("next")
        self.next.clicked.connect(self.forward)
        nav.addWidget(self.next)
        root = QWidget()
        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.stack, 1)
        v.addLayout(nav)
        self.setCentralWidget(root)
        self.setStyleSheet(CSS)
        self.go(0)

    def build(self):
        la = config.language() == "la"
        # 1. Welcome + language
        en_b = card("English", "preferences-desktop-locale", lambda: self.lang("en"), True, 40)
        la_b = card("Latina", "preferences-desktop-locale", lambda: self.lang("la"), True, 40)
        (la_b if la else en_b).setChecked(True)
        self.lang_buttons = {"en": en_b, "la": la_b}
        self.stack.addWidget(page(T("Pax tibi. Welcome to Credo OS", "Pax tibi. Salve in Credo OS"),
                                  T("A calm, Catholic computer: the liturgy, prayer and the Church's library, "
                                    "with everything you need for work and study. Choose your language:",
                                    "Computatrum tranquillum et catholicum. Linguam elige:"),
                                  grid([en_b, la_b], 2), logo=True))
        # 2. Look
        dark = config.load().get("appearance", "variant", fallback="monastic") != "ivory"
        d_b = card(T("Dark", "Obscurum"), "weather-clear-night", lambda: self.look(True), True)
        l_b = card(T("Light", "Clarum"), "weather-clear", lambda: self.look(False), True)
        (d_b if dark else l_b).setChecked(True)
        self.look_buttons = (d_b, l_b)
        self.stack.addWidget(page(T("Light or dark?", "Clarum an obscurum?"),
                                  T("Dark green glass, or warm ivory. Your wallpaper, dock and widgets stay as "
                                    "they are; you can change this later in Credo Center.",
                                    "Postea in Credo Center mutari potest."),
                                  grid([d_b, l_b], 2)))
        # 3. Prayer
        ang = card(T("Angelus reminder", "Monitio Angeli"), "preferences-desktop-notification-bell",
                   lambda c: angelus(c), True)
        ang.setChecked(angelus_on())
        self.stack.addWidget(page(T("Pray with the Church", "Ora cum Ecclesia"),
                                  T("Today shows the feast, the saint's life and the propers of the Mass "
                                    "(1954 Missal). The Rosary guides you bead by bead.",
                                    "Hodie: festum, vita Sancti, proprium Missae."),
                                  grid([card(T("Today", "Hodie"), "credo-today", lambda: run("credo-library", "open", "/today")),
                                        card(T("Mass of the Day", "Missa diei"), "credo-mass", lambda: run("credo-library", "open", "/mass")),
                                        card(T("Holy Rosary", "Rosarium"), "credo-rosary", lambda: run("credo-library", "open", "/rosary")),
                                        card(T("Prayers", "Preces"), "credo-prayers", lambda: run("credo-library", "open", "/prayers")),
                                        ang]
                                       + ([card("FSSP", "credo-fssp", lambda: run("credo-fssp"))]
                                          if shutil.which("credo-fssp") else []))))
        # 4. Apps
        self.stack.addWidget(page(T("Your apps", "Applicationes tuae"),
                                  T("Everything is in the dock and in the app grid (second dock icon). "
                                    "More apps are one click away in Software.",
                                    "Omnia in navali et in indice applicationum."),
                                  grid([card(T("Web Browser", "Navigator"), "credo-browser", lambda: run("credo-browser")),
                                        card(T("Bible", "Biblia"), "credo-bible", lambda: run("xiphos")),
                                        card(T("Catholic Library", "Bibliotheca"), "credo-library", lambda: run("credo-library", "open", "/")),
                                        card(T("Files", "Fasciculi"), "system-file-manager", lambda: run("dolphin")),
                                        card(T("Software", "Programmata"), "plasmadiscover", lambda: run("plasma-discover")),
                                        card(T("Windows && Mac apps", "Applicationes Windows/Mac"), "credo-winapps",
                                             lambda: run("credo-center", "--winapps"))])))
        # 5. Safety
        self.stack.addWidget(page(T("Safe and private", "Tutum et privatum"),
                                  T("No tracking, no accounts. Run the Security Check now and then: it checks the "
                                    "firewall, encryption and updates and tells you how to fix anything.",
                                    "Nulla vestigatio. Inspectionem securitatis interdum exsequere."),
                                  grid([card(T("Security Check", "Inspectio securitatis"), "security-high",
                                             lambda: run("credo-security-check")),
                                        card(T("Updates", "Renovationes"), "system-software-update",
                                             lambda: run("plasma-discover", "--mode", "update")),
                                        card("Credo Center", "credo-center", lambda: run("credo-center"))])))
        # 6. Done
        self.again = QCheckBox(T("Show this welcome at login", "Hanc salutationem in initio ostende"))
        self.again.setChecked(False)
        w = QWidget()
        h = QHBoxLayout(w)
        h.addStretch()
        h.addWidget(self.again)
        h.addStretch()
        self.stack.addWidget(page(T("All set. Deo gratias!", "Omnia parata. Deo gratias!"),
                                  T("Ad maiorem Dei gloriam. You can open this tour again from the app grid "
                                    "(Welcome) or from the Credo menu.",
                                    "Ad maiorem Dei gloriam."), w, logo=True))

    def lang(self, code):
        for k, b in self.lang_buttons.items():
            b.setChecked(k == code)
        set_language(code)

    def look(self, dark):
        self.look_buttons[0].setChecked(dark)
        self.look_buttons[1].setChecked(not dark)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            set_look(dark)
        finally:
            QApplication.restoreOverrideCursor()

    def go(self, i):
        i = max(0, min(i, self.stack.count() - 1))
        self.stack.setCurrentIndex(i)
        self.back.setVisible(i > 0)
        last = i == self.stack.count() - 1
        self.next.setText(T("Finish", "Fini") if last else T("Next", "Porro"))
        for k, d in enumerate(self.dots):
            d.setProperty("on", "true" if k == i else "false")
            d.style().unpolish(d)
            d.style().polish(d)

    def forward(self):
        if self.stack.currentIndex() == self.stack.count() - 1:
            config.set_value("general", "welcome_done", "no" if self.again.isChecked() else "yes")
            self.close()
        else:
            self.go(self.stack.currentIndex() + 1)


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--first-run" in argv and config.load().get("general", "welcome_done", fallback="no") == "yes":
        return 0
    app = QApplication(argv)
    app.setApplicationName("Credo Welcome")
    app.setDesktopFileName("credo-welcome")
    w = Welcome()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
