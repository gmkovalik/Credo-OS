"""Credo Center: one place for Credo OS settings (PySide6 / Qt 6)."""
import shutil
import subprocess
import sys

from PySide6.QtCore import QByteArray, QProcess, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox,
                               QStackedWidget, QVBoxLayout, QWidget, QLineEdit, QFileDialog)

from . import config, db, liturgy, palettes, theme, thinkpad

HELPER = ["pkexec", "/usr/libexec/credo/credo-helper"]

TR = {
    "title": ("Credo Center", "Centrum Credo"),
    "welcome": ("Welcome", "Salve"),
    "appearance": ("Appearance", "Species"),
    "thinkpad": ("ThinkPad", "ThinkPad"),
    "library": ("Library", "Bibliotheca"),
    "liturgy": ("Liturgy", "Liturgia"),
    "system": ("System", "Systema"),
    "language": ("Interface language", "Lingua"),
    "variant": ("Theme", "Thema"),
    "logo": ("Logo", "Signum"),
    "panel_pos": ("Taskbar position", "Locus taeniae"),
    "panel_h": ("Taskbar height", "Altitudo taeniae"),
    "floating": ("Floating taskbar", "Taenia fluitans"),
    "wallpaper": ("Credo wallpaper", "Imago parietis Credo"),
    "motto": ("Latin motto on wallpaper", "Sententia Latina"),
    "apply": ("Apply", "Adhibe"),
    "boot": ("Apply to boot splash and login screen", "Adhibe ad initium et ingressum"),
    "applied": ("Applied.", "Adhibitum."),
    "applying": ("Applying…", "Adhibetur…"),
    "relogin": ("The whole desktop switches language the next time you log in. Credo apps switch now.",
                "Tota mensa linguam mutabit cum iterum inieris. Applicationes Credo statim mutant."),
    "layout": ("Layout", "Dispositio"),
    "devotions": ("Devotions", "Devotiones"),
    "mysteries_today": ("Mysteries of the Rosary today", "Mysteria Rosarii hodie"),
    "today": ("Today", "Hodie"),
    "rosary": ("Holy Rosary", "Sanctissimum Rosarium"),
    "prayers": ("Prayers", "Preces"),
    "examen": ("Examination of Conscience", "Examen conscientiae"),
    "ordo": ("Ordinary of the Mass", "Ordo Missae"),
    "angelus": ("Angelus reminder at 6:00, 12:00 and 18:00", "Monitum Angelus horis VI, XII, XVIII"),
    "angelus_now": ("Pray the Angelus now", "Ora nunc Angelus"),
    "study": ("Study", "Studium"),
    "bible": ("Holy Bible", "Biblia Sacra"),
    "bible_desc": ("Download the Douay-Rheims (Challoner) and the Latin Vulgate for Xiphos and BibleTime.",
                   "Depone Douay-Rheims et Vulgatam pro Xiphos et BibleTime."),
    "bible_install": ("Download Douay-Rheims and Vulgate", "Depone Douay-Rheims et Vulgatam"),
    "install": ("Install", "Institue"),
    "open": ("Open", "Aperi"),
    "open_web": ("Open in browser", "Aperi in navigatore"),
    "macapps": ("Mac apps", "Applicationes Mac"),
    "macapps_desc": ("Mac programs don't run on Linux directly. Type the name of a Mac app (or choose its "
                     ".dmg file) to install its Linux version or the closest equivalent.",
                     "Programmata Mac in Linux directe non currunt. Inscribe nomen applicationis Mac ut "
                     "versionem Linux vel aequivalentem instituas."),
    "macapps_ph": ("e.g. Pages, Zoom, Photoshop, Verbum…", "e.g. Pages, Zoom, Photoshop, Verbum…"),
    "macapps_file": ("Choose a .dmg or .app…", "Elige .dmg vel .app…"),
    "macapps_none": ("No match yet. Try Discover (System page), which searches Fedora and Flathub.",
                     "Nihil inventum. Tempta Discover."),
    "darling": ("Run Mac programs directly (experimental)", "Programmata Mac directe (experimentale)"),
    "darling_install": ("Build and install Darling…", "Darling institue…"),
    "winapps": ("Windows apps", "Applicationes Windows"),
    "winapps_desc": ("Everyday Windows programs run with <b>Bottles</b>: just double-click their installer "
                     "(.exe or .msi). Big professional software such as <b>SolidWorks</b>, Adobe Creative Cloud "
                     "or AutoCAD needs real Windows: <b>WinBoat</b> runs it in a background virtual machine and "
                     "shows its programs as normal Credo windows. Type a program's name to see the best way.",
                     "Programmata Windows cotidiana cum <b>Bottles</b> currunt: installatorem (.exe, .msi) bis "
                     "preme. Magna programmata (SolidWorks, Adobe, AutoCAD) Windows verum requirunt: "
                     "<b>WinBoat</b> id in machina virtuali exsequitur."),
    "winapps_ph": ("e.g. SolidWorks, Notepad++, Photoshop, Logos…", "e.g. SolidWorks, Notepad++, Photoshop…"),
    "winapps_file": ("Run a .exe or .msi…", "Exsequere .exe vel .msi…"),
    "winapps_none": ("Not in the list: try its installer with Bottles first; if it fails, use WinBoat.",
                     "Non in indice: primum Bottles tempta, deinde WinBoat."),
    "bottles": ("Everyday Windows programs (Bottles)", "Programmata cotidiana (Bottles)"),
    "bottles_install": ("Install Bottles…", "Bottles institue…"),
    "bottles_open": ("Open Bottles", "Aperi Bottles"),
    "winboat": ("Real Windows for SolidWorks, Adobe, AutoCAD… (WinBoat)", "Windows verum (WinBoat)"),
    "winboat_install": ("Install WinBoat…", "WinBoat institue…"),
    "winboat_open": ("Open WinBoat", "Aperi WinBoat"),
    "battery": ("Battery", "Pila"),
    "thresholds": ("Limit charging to protect the battery", "Onerationem limita"),
    "start": ("Start charging below", "Incipe infra"),
    "stop": ("Stop charging at", "Desine ad"),
    "profile": ("Power profile", "Modus potentiae"),
    "status": ("Status", "Status"),
    "fan": ("Fan", "Ventilabrum"),
    "temps": ("Temperatures", "Temperaturae"),
    "firmware": ("Check for BIOS / firmware updates", "Quaere renovationes firmware"),
    "fingerprint": ("Set up fingerprint login", "Digitum signa"),
    "touchpad": ("TrackPoint and touchpad", "TrackPoint et tactile"),
    "keyboard": ("Keyboard and Fn keys", "Claviatura"),
    "display": ("Display and scaling", "Ostentatio"),
    "open_lib": ("Open Library", "Aperi Bibliothecam"),
    "fetch": ("Download / update", "Depone / renova"),
    "import": ("Import a folder…", "Importa folder…"),
    "mass": ("Mass of the Day", "Missa Diei"),
    "calendar": ("Calendar", "Calendarium"),
    "updates": ("Software updates", "Renovationes"),
    "store": ("Get more apps (Discover)", "Plures applicationes"),
    "rpmfusion": ("Enable RPM Fusion (codecs, extra drivers)", "RPM Fusion adhibe"),
    "flathub": ("Enable Flathub", "Flathub adhibe"),
    "network": ("Wi-Fi and network", "Rete"),
    "sound": ("Sound", "Sonus"),
    "bluetooth": ("Bluetooth", "Bluetooth"),
    "users": ("Users", "Usores"),
    "allset": ("All KDE settings", "Omnia KDE"),
    "backup": ("Disk usage", "Usus disci"),
}


def T(key):
    en, la = TR.get(key, (key, key))
    return la if config.language() == "la" else en


def run_detached(*cmd):
    if shutil.which(cmd[0]):
        subprocess.Popen(list(cmd), start_new_session=True)
        return True
    return False


def in_terminal(*cmd):
    return run_detached("konsole", "--hold", "-e", *cmd)


def kcm(name):
    return run_detached("systemsettings", name)


def set_desktop_language(lang):
    """Make the whole Plasma session Latin (la_VA locale + Latin catalogs, English fallback) or English.
    Takes effect at the next login."""
    kw = shutil.which("kwriteconfig6") or shutil.which("kwriteconfig5")
    if not kw:
        return
    if lang == "la":
        fmt, langs = "la_VA.UTF-8", "la:en_US"
    else:
        fmt, langs = "en_US.UTF-8", "en_US"
    subprocess.run([kw, "--file", "plasma-localerc", "--group", "Formats", "--key", "LANG", fmt])
    subprocess.run([kw, "--file", "plasma-localerc", "--group", "Translations", "--key", "LANGUAGE", langs])


def svg_pixmap(svg_text, size=96):
    pm = QPixmap()
    pm.loadFromData(QByteArray(svg_text.encode("utf-8")), "SVG")
    return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def button(text, slot):
    b = QPushButton(text)
    b.clicked.connect(slot)
    return b


# ------------------------------------------------------------------ pages
class WelcomePage(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        logo = QLabel()
        _, pal = palettes.resolve("papal")
        logo.setPixmap(svg_pixmap(theme.logo_svg("chirho", pal["logo"]), 120))
        logo.setAlignment(Qt.AlignCenter)
        v.addWidget(logo)
        la = config.language() == "la"
        head = QLabel("<h1>Credo OS</h1><p><i>Credo in unum Deum</i></p>")
        head.setAlignment(Qt.AlignCenter)
        v.addWidget(head)
        d = liturgy.today()
        txt = QLabel(
            f"<p style='font-size:14pt'>{d.feast('la' if la else 'en') or d.title('la' if la else 'en')}</p>"
            f"<p>{d.season_name('la' if la else 'en')} · {d.color}</p>")
        txt.setAlignment(Qt.AlignCenter)
        v.addWidget(txt)
        grid = QGridLayout()
        for i, k in enumerate(("devotions", "library", "study", "appearance", "thinkpad", "system")):
            b = QPushButton(T(k))
            b.setMinimumHeight(48)
            b.clicked.connect(lambda _=False, key=k: self.window().go_key(key))
            grid.addWidget(b, i // 2, i % 2)
        v.addLayout(grid)
        v.addStretch()


class AppearancePage(QWidget):
    def __init__(self):
        super().__init__()
        s = theme.current_settings()
        lang = 1 if config.language() == "la" else 0
        v = QVBoxLayout(self)
        form = QFormLayout()

        self.variant = QComboBox()
        for k, names in palettes.VARIANTS.items():
            self.variant.addItem(names[lang], k)
        self.variant.setCurrentIndex(max(0, self.variant.findData(s["variant"])))

        self.logo = QComboBox()
        for k, names in palettes.LOGOS.items():
            self.logo.addItem(names[lang], k)
        self.logo.setCurrentIndex(max(0, self.logo.findData(s["logo"])))

        self.layout_box = QComboBox()
        for k, names in theme.LAYOUTS.items():
            self.layout_box.addItem(names[lang], k)
        self.layout_box.setCurrentIndex(max(0, self.layout_box.findData(s["layout"])))

        self.position = QComboBox()
        for k, en, la in (("bottom", "Bottom", "Infra"), ("top", "Top", "Supra"),
                          ("left", "Left", "Sinistra"), ("right", "Right", "Dextra")):
            self.position.addItem(la if lang else en, k)
        self.position.setCurrentIndex(max(0, self.position.findData(s["panel_position"])))

        self.height = QSpinBox()
        self.height.setRange(28, 96)
        self.height.setValue(s["panel_height"])
        self.floating = QCheckBox(); self.floating.setChecked(s["panel_floating"])
        self.wall = QCheckBox(); self.wall.setChecked(s["wallpaper"])
        self.motto = QCheckBox(); self.motto.setChecked(s["motto"])

        form.addRow(T("variant"), self.variant)
        form.addRow(T("logo"), self.logo)
        form.addRow(T("layout"), self.layout_box)
        form.addRow(T("panel_pos"), self.position)
        form.addRow(T("panel_h"), self.height)
        form.addRow(T("floating"), self.floating)
        form.addRow(T("wallpaper"), self.wall)
        form.addRow(T("motto"), self.motto)
        v.addLayout(form)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(260)
        v.addWidget(self.preview)
        for w in (self.variant, self.logo):
            w.currentIndexChanged.connect(self.update_preview)
        self.motto.toggled.connect(self.update_preview)
        self.update_preview()

        row = QHBoxLayout()
        self.apply_btn = button(T("apply"), self.apply)
        row.addWidget(self.apply_btn)
        row.addWidget(button(T("boot"), self.apply_boot))
        row.addStretch()
        v.addLayout(row)
        self.msg = QLabel()
        v.addWidget(self.msg)
        v.addStretch()

    def update_preview(self):
        _, pal = palettes.resolve(self.variant.currentData())
        svg = theme.wallpaper_svg(pal, self.logo.currentData(), self.motto.isChecked(), 960, 600)
        pm = QPixmap()
        pm.loadFromData(QByteArray(svg.encode("utf-8")), "SVG")
        self.preview.setPixmap(pm.scaled(480, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def apply(self):
        cp = config.load()
        a = cp["appearance"]
        a["variant"] = self.variant.currentData()
        a["logo"] = self.logo.currentData()
        a["layout"] = self.layout_box.currentData()
        a["panel_position"] = self.position.currentData()
        a["panel_height"] = str(self.height.value())
        a["panel_floating"] = str(self.floating.isChecked()).lower()
        a["wallpaper"] = str(self.wall.isChecked()).lower()
        a["motto"] = str(self.motto.isChecked()).lower()
        config.save(cp)
        # Drawing the 2.8K wallpaper takes a few seconds: do it in a separate process so the
        # window stays responsive.
        self.msg.setText(T("applying"))
        self.apply_btn.setEnabled(False)
        self.proc = QProcess(self)
        self.proc.finished.connect(self._applied)
        self.proc.start("credo-theme", ["--quiet"])

    def _applied(self, code, _status=None):
        self.apply_btn.setEnabled(True)
        err = bytes(self.proc.readAllStandardError()).decode(errors="replace").strip()
        self.msg.setText(T("applied") if code == 0 else err[-300:])

    def apply_boot(self):
        r = subprocess.run(HELPER + ["boot-theme", self.logo.currentData(), self.variant.currentData()],
                           capture_output=True, text=True)
        self.msg.setText(T("applied") if r.returncode == 0 else r.stderr.strip()[:300])


class ThinkPadPage(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"<b>{thinkpad.product() or 'ThinkPad'}</b>"))

        box = QGroupBox(T("battery"))
        bl = QFormLayout(box)
        self.bat_status = QLabel()
        bl.addRow(T("status"), self.bat_status)
        enabled, start, stop = thinkpad.configured_thresholds()
        self.limit = QCheckBox(T("thresholds")); self.limit.setChecked(enabled)
        self.start = QSlider(Qt.Horizontal); self.start.setRange(20, 95); self.start.setValue(start)
        self.stop = QSlider(Qt.Horizontal); self.stop.setRange(50, 100); self.stop.setValue(stop)
        self.start_l, self.stop_l = QLabel(), QLabel()
        self.start.valueChanged.connect(self._sync); self.stop.valueChanged.connect(self._sync)
        bl.addRow(self.limit)
        r1 = QHBoxLayout(); r1.addWidget(self.start); r1.addWidget(self.start_l)
        r2 = QHBoxLayout(); r2.addWidget(self.stop); r2.addWidget(self.stop_l)
        bl.addRow(T("start"), r1)
        bl.addRow(T("stop"), r2)
        presets = QHBoxLayout()
        for label, a, b in (("Max lifespan 40–60%", 40, 60), ("Balanced 75–90%", 75, 90), ("Full 100%", 95, 100)):
            presets.addWidget(button(label, lambda _=False, a=a, b=b: (self.start.setValue(a), self.stop.setValue(b))))
        bl.addRow(presets)
        bl.addRow(button(T("apply"), self.apply_battery))
        self._sync()
        v.addWidget(box)

        pbox = QGroupBox(T("profile"))
        pl = QHBoxLayout(pbox)
        self.profile = QComboBox()
        for k, label in (("power-saver", "Power saver"), ("balanced", "Balanced"), ("performance", "Performance")):
            self.profile.addItem(label, k)
        cur = thinkpad.power_profile()
        if cur:
            self.profile.setCurrentIndex(max(0, self.profile.findData(cur)))
        self.profile.currentIndexChanged.connect(lambda: thinkpad.set_power_profile(self.profile.currentData()))
        pl.addWidget(self.profile)
        v.addWidget(pbox)

        self.sensors = QLabel()
        self.sensors.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.sensors)

        tools = QGridLayout()
        for i, (k, fn) in enumerate((
                ("firmware", lambda: in_terminal("sh", "-c", "fwupdmgr refresh; fwupdmgr get-updates && fwupdmgr update")),
                ("fingerprint", lambda: kcm("kcm_users")),
                ("touchpad", lambda: kcm("kcm_touchpad") or kcm("kcm_mouse")),
                ("keyboard", lambda: kcm("kcm_keyboard")),
                ("display", lambda: kcm("kcm_kscreen")),
                ("backup", lambda: run_detached("filelight")))):
            tools.addWidget(button(T(k), fn), i // 2, i % 2)
        v.addLayout(tools)
        v.addStretch()
        self.msg = QLabel(); v.addWidget(self.msg)

        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def _sync(self):
        if self.start.value() >= self.stop.value():
            self.start.setValue(self.stop.value() - 5)
        self.start_l.setText(f"{self.start.value()}%")
        self.stop_l.setText(f"{self.stop.value()}%")

    def refresh(self):
        b = thinkpad.battery()
        if b:
            parts = [f"{b['capacity']}% · {b['status']}"]
            if b["health"]:
                parts.append(f"health {b['health']}%")
            if b["cycles"]:
                parts.append(f"{b['cycles']} cycles")
            if b["start"] and b["stop"]:
                parts.append(f"limits {b['start']}–{b['stop']}%")
            self.bat_status.setText(" · ".join(parts))
            self.limit.setEnabled(b["thresholds_supported"])
        else:
            self.bat_status.setText("No battery found")
        f = thinkpad.fan()
        temps = thinkpad.temperatures()[:8]
        lines = []
        if f:
            lines.append(f"<b>{T('fan')}:</b> {f.get('speed', '?')} RPM ({f.get('level', '?')})")
        if temps:
            lines.append(f"<b>{T('temps')}:</b> " + ", ".join(f"{n} {t:.0f}°C" for n, t in temps))
        self.sensors.setText("<br>".join(lines))

    def apply_battery(self):
        args = ["battery", str(self.start.value()), str(self.stop.value())] if self.limit.isChecked() \
            else ["battery", "off"]
        r = subprocess.run(HELPER + args, capture_output=True, text=True)
        self.msg.setText(T("applied") if r.returncode == 0 else r.stderr.strip()[:300])
        self.refresh()


class LibraryPage(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "<p>Papal documents before Vatican II (vatican.va, English and Latin), writings of the saints "
            "(Project Gutenberg), the Roman Missal with 1954 rubrics (Divinum Officium), and the Roman "
            "Catechism (Internet Archive). Everything is stored on this computer and works offline.</p>"))
        v.itemAt(0).widget().setWordWrap(True)
        self.stats = QLabel()
        v.addWidget(self.stats)
        row = QHBoxLayout()
        row.addWidget(button(T("open_lib"), lambda: run_detached("credo-library", "open", "/")))
        row.addWidget(button(T("mass"), lambda: run_detached("credo-library", "open", "/mass")))
        row.addWidget(button(T("calendar"), lambda: run_detached("credo-library", "open", "/calendar")))
        v.addLayout(row)

        box = QGroupBox(T("fetch"))
        g = QGridLayout(box)
        for i, (key, label) in enumerate((("all", "Everything (several hours)"), ("missal", "Missal 1954"),
                                          ("catechism", "Roman Catechism"), ("papal", "Papal documents"),
                                          ("saints", "Writings of the saints"))):
            g.addWidget(button(label, lambda _=False, k=key: in_terminal("credo-library", "fetch", k)), i // 3, i % 3)
        v.addWidget(box)

        ibox = QGroupBox(T("import"))
        il = QHBoxLayout(ibox)
        self.coll = QComboBox()
        for k, (en, la) in db.COLLECTIONS.items():
            self.coll.addItem(la if config.language() == "la" else en, k)
        self.coll.setCurrentIndex(self.coll.findData("imported"))
        il.addWidget(self.coll)
        il.addWidget(button(T("import"), self.do_import))
        v.addWidget(ibox)
        v.addWidget(QLabel("Bible: Xiphos (install the DRC Douay-Rheims or Vulgate module) · "
                           "Wikipedia and other offline sites: Kiwix"))
        row2 = QHBoxLayout()
        row2.addWidget(button("Xiphos", lambda: run_detached("xiphos")))
        row2.addWidget(button("Kiwix", lambda: run_detached("kiwix-desktop")))
        row2.addStretch()
        v.addLayout(row2)
        v.addStretch()
        self.refresh()

    def refresh(self):
        try:
            st = db.stats(db.connect())
        except Exception as e:
            self.stats.setText(str(e)); return
        if not st:
            self.stats.setText("<i>The library is empty. Choose what to download below.</i>")
            return
        rows = "".join(f"<tr><td>{db.COLLECTIONS.get(k, (k,))[0]}</td><td>"
                       + ", ".join(f"{l.upper()}: {n}" for l, n in sorted(v.items())) + "</td></tr>"
                       for k, v in st.items())
        self.stats.setText(f"<table cellpadding=4>{rows}</table>")

    def do_import(self):
        d = QFileDialog.getExistingDirectory(self, T("import"))
        if d:
            in_terminal("credo-library", "import", d, "--collection", self.coll.currentData())


class LiturgyPage(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        la = config.language() == "la"
        L = "la" if la else "en"
        d = liturgy.today()
        v.addWidget(QLabel(f"<h2>{d.feast(L) or d.title(L)}</h2>"
                           f"<p>{d.date:%A %d %B %Y}</p>"
                           f"<p><span style='background:{d.color_hex}'>&nbsp;&nbsp;&nbsp;&nbsp;</span> "
                           f"{d.season_name(L)} · {d.color}"
                           f"{' · ' + ', '.join(d.notes) if d.notes else ''}</p>"))
        upcoming = []
        import datetime as dt
        day = d.date
        for _ in range(60):
            day += dt.timedelta(days=1)
            i = liturgy.day_info(day)
            if i.feast_en or (day.weekday() == 6):
                upcoming.append(f"<tr><td>{day:%a %d %b}</td><td>{i.feast(L) or i.title(L)}</td>"
                                f"<td style='color:{i.color_hex}'>●</td></tr>")
            if len(upcoming) >= 10:
                break
        v.addWidget(QLabel(f"<table cellpadding=3>{''.join(upcoming)}</table>"))
        row = QHBoxLayout()
        row.addWidget(button(T("mass"), lambda: run_detached("credo-library", "open", "/mass")))
        row.addWidget(button(T("calendar"), lambda: run_detached("credo-library", "open", "/calendar")))
        row.addStretch()
        v.addLayout(row)
        v.addStretch()


class DevotionsPage(QWidget):
    def __init__(self):
        super().__init__()
        from . import devotions
        la = config.language() == "la"
        v = QVBoxLayout(self)
        myst = devotions.MYSTERIES[devotions.mysteries_for()]
        v.addWidget(QLabel(f"<h2>{T('devotions')}</h2><p>{T('mysteries_today')}: <b>{myst[1] if la else myst[0]}</b></p>"))
        g = QGridLayout()
        for i, (k, path) in enumerate((("today", "/today"), ("rosary", "/rosary"), ("prayers", "/prayers"),
                                       ("examen", "/examen"), ("mass", "/mass"), ("ordo", "/ordo"))):
            b = button(T(k), lambda _=False, p=path: run_detached("credo-library", "open", p))
            b.setMinimumHeight(44)
            g.addWidget(b, i // 2, i % 2)
        v.addLayout(g)
        self.angelus = QCheckBox(T("angelus"))
        self.angelus.setChecked(self._timer_enabled())
        self.angelus.toggled.connect(self._toggle)
        v.addWidget(self.angelus)
        v.addWidget(button(T("angelus_now"), lambda: run_detached("credo-liturgy", "--angelus")))
        v.addStretch()

    def _timer_enabled(self):
        r = subprocess.run(["systemctl", "--user", "is-enabled", "credo-angelus.timer"],
                           capture_output=True, text=True) if shutil.which("systemctl") else None
        return bool(r) and r.stdout.strip() == "enabled"

    def _toggle(self, on):
        if shutil.which("systemctl"):
            subprocess.run(["systemctl", "--user", "enable" if on else "disable", "--now", "credo-angelus.timer"],
                           capture_output=True)


# (label, command to launch, package or flatpak id, description)
STUDY_APPS = [
    ("Xiphos", "xiphos", "xiphos", "Bible study (SWORD): Douay-Rheims, Vulgate, commentaries"),
    ("BibleTime", "bibletime", "bibletime", "Bible study with parallel texts and lexicons"),
    ("Kiwix", "kiwix-desktop", "kiwix-desktop", "Offline Wikipedia, Wiktionary (Latin) and other libraries"),
    ("Calibre", "calibre", "calibre", "E-book library: organize and convert the Fathers and spiritual classics"),
    ("Foliate", "foliate", "foliate", "Comfortable e-book reader"),
    ("GoldenDict", "goldendict", "goldendict-ng", "Dictionaries, including Latin–English"),
    ("Anki", "flatpak run net.ankiweb.Anki", "flatpak:net.ankiweb.Anki",
     "Flashcards for Latin vocabulary and the catechism"),
    ("Zotero", "flatpak run org.zotero.Zotero", "flatpak:org.zotero.Zotero", "Research and citations"),
    ("Xournal++", "xournalpp", "xournalpp", "Handwritten notes and PDF annotation"),
    ("Zim", "zim", "Zim", "Desktop wiki for study notes"),
    ("MuseScore", "musescore", "musescore", "Sacred music scores"),
    ("Frescobaldi", "frescobaldi", "frescobaldi", "Engrave chant and polyphony with LilyPond"),
    ("Audacity", "audacity", "audacity", "Record and edit audio (choir practice, talks)"),
]

BIBLE_MODULES = ("set -e; export LANG=C; yes yes | installmgr -init >/dev/null; yes yes | installmgr -sc; "
                 "installmgr -r CrossWire; for m in DRC Vulgate VulgClementine; do "
                 "yes yes | installmgr -ri CrossWire $m || echo \"($m not available)\"; done; "
                 "echo; echo 'Done. Open Xiphos or BibleTime.'")


class StudyPage(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"<h2>{T('study')}</h2>"))
        bible = QGroupBox(T("bible"))
        bl = QVBoxLayout(bible)
        bl.addWidget(QLabel(T("bible_desc")))
        bl.addWidget(button(T("bible_install"), lambda: in_terminal("sh", "-c", BIBLE_MODULES)))
        v.addWidget(bible)
        g = QGridLayout()
        for i, (name, cmd, pkg, desc) in enumerate(STUDY_APPS):
            installed = shutil.which(cmd.split()[0]) and (not pkg.startswith("flatpak:") or self._has_flatpak(pkg))
            b = QPushButton(name if installed else f"{name} — {T('install')}")
            b.setToolTip(desc)
            b.setMinimumHeight(38)
            if installed:
                b.clicked.connect(lambda _=False, c=cmd: run_detached(*c.split()))
            elif pkg.startswith("flatpak:"):
                b.clicked.connect(lambda _=False, p=pkg[8:]: in_terminal("flatpak", "install", "-y", "flathub", p))
            else:
                b.clicked.connect(lambda _=False, p=pkg: in_terminal("pkexec", "dnf", "install", "-y", p))
            g.addWidget(b, i // 2, i % 2)
        v.addLayout(g)
        v.addStretch()

    @staticmethod
    def _has_flatpak(pkg):
        if not shutil.which("flatpak"):
            return False
        r = subprocess.run(["flatpak", "info", pkg[8:]], capture_output=True)
        return r.returncode == 0


class MacAppsPage(QWidget):
    """Find the Linux version or the closest equivalent of a Mac app; optional Darling."""

    def __init__(self, initial=""):
        super().__init__()
        from . import macapps
        self.macapps = macapps
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"<h2>{T('macapps')}</h2><p>{T('macapps_desc')}</p>"))
        v.itemAt(0).widget().setWordWrap(True)
        row = QHBoxLayout()
        self.query = QLineEdit(initial)
        self.query.setPlaceholderText(T("macapps_ph"))
        self.query.textChanged.connect(self.search)
        row.addWidget(self.query, 1)
        row.addWidget(button(T("macapps_file"), self.choose_file))
        v.addLayout(row)
        self.results = QVBoxLayout()
        box = QWidget()
        box.setLayout(self.results)
        v.addWidget(box)
        v.addStretch()
        darling = QGroupBox(T("darling"))
        dl = QVBoxLayout(darling)
        note = QLabel(macapps.DARLING_NOTE)
        note.setWordWrap(True)
        dl.addWidget(note)
        dl.addWidget(button(T("darling_install"), lambda: in_terminal("/usr/libexec/credo/install-darling")))
        v.addWidget(darling)
        self.search(initial)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, T("macapps_file"), "",
                                              "Mac apps (*.dmg *.pkg *.zip *.app);;All files (*)")
        if path:
            self.query.setText(path.rstrip("/").split("/")[-1])

    def search(self, text):
        while self.results.count():
            w = self.results.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not text.strip():
            return
        found = self.macapps.find(text)[:6]
        if not found:
            self.results.addWidget(QLabel(T("macapps_none")))
            return
        for names, linux, kind, target, note in found:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(f"<b>{names[0]}</b> → <b>{linux}</b><br><span style='opacity:.75'>{note}</span>")
            lbl.setWordWrap(True)
            h.addWidget(lbl, 1)
            if kind == "installed":
                b = button(T("open"), lambda _=False, c=target: run_detached(*c.split()))
            elif kind == "dnf":
                b = button(T("install"), lambda _=False, p=target: in_terminal("pkexec", "dnf", "install", "-y", p))
            elif kind == "flatpak":
                b = button(T("install"), lambda _=False, p=target: in_terminal("flatpak", "install", "-y", "flathub", p))
            else:
                b = button(T("open_web"), lambda _=False, u=target: run_detached("credo-browser", u)
                           or run_detached("xdg-open", u))
            h.addWidget(b)
            self.results.addWidget(row)


class WinAppsPage(QWidget):
    """Run Windows programs: Bottles (Wine) for everyday ones, WinBoat (real Windows) for big ones."""

    def __init__(self, initial=""):
        super().__init__()
        from . import winapps
        self.winapps = winapps
        v = QVBoxLayout(self)
        intro = QLabel(f"<h2>{T('winapps')}</h2><p>{T('winapps_desc')}</p>")
        intro.setWordWrap(True)
        v.addWidget(intro)
        row = QHBoxLayout()
        self.query = QLineEdit(initial)
        self.query.setPlaceholderText(T("winapps_ph"))
        self.query.textChanged.connect(self.search)
        row.addWidget(self.query, 1)
        row.addWidget(button(T("winapps_file"), self.choose_file))
        v.addLayout(row)
        self.results = QVBoxLayout()
        box = QWidget()
        box.setLayout(self.results)
        v.addWidget(box)
        v.addStretch()
        for key, route, install, opener in (
                ("bottles", "bottles", lambda: in_terminal("/usr/libexec/credo/install-bottles"),
                 lambda: run_detached("flatpak", "run", "com.usebottles.bottles")),
                ("winboat", "winboat", lambda: in_terminal("/usr/libexec/credo/install-winboat"),
                 lambda: run_detached("winboat"))):
            g = QGroupBox(T(key))
            gl = QVBoxLayout(g)
            note = QLabel(winapps.ROUTE_NOTE[route])
            note.setWordWrap(True)
            gl.addWidget(note)
            bl = QHBoxLayout()
            bl.addWidget(button(T(f"{key}_install"), install))
            bl.addWidget(button(T(f"{key}_open"), opener))
            bl.addStretch()
            gl.addLayout(bl)
            v.addWidget(g)
        self.search(initial)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, T("winapps_file"), "",
                                              "Windows programs (*.exe *.msi);;All files (*)")
        if path:
            run_detached("credo-winrun", path)

    def search(self, text):
        while self.results.count():
            w = self.results.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not text.strip():
            return
        found = self.winapps.find(text)[:6]
        if not found:
            self.results.addWidget(QLabel(T("winapps_none")))
            return
        label = {"linux": "Linux", "bottles": "Bottles", "winboat": "WinBoat"}
        for names, route, target, note in found:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(f"<b>{names[0]}</b> → <b>{label[route]}</b><br><span style='opacity:.75'>{note}</span>")
            lbl.setWordWrap(True)
            h.addWidget(lbl, 1)
            if route == "bottles":
                b = button(T("winapps_file"), self.choose_file)
            elif route == "winboat":
                b = button(T("winboat_install"), lambda: in_terminal("/usr/libexec/credo/install-winboat"))
            elif target.startswith("flatpak:"):
                b = button(T("install"), lambda _=False, p=target[8:]: in_terminal("flatpak", "install", "-y", "flathub", p))
            elif target.startswith("dnf:"):
                b = button(T("install"), lambda _=False, p=target[4:]: in_terminal("pkexec", "dnf", "install", "-y", p))
            else:
                u = target[4:] if target.startswith("web:") else target
                b = button(T("open_web"), lambda _=False, u=u: run_detached("credo-browser", u))
            h.addWidget(b)
            self.results.addWidget(row)


class SystemPage(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)
        g = QGridLayout()
        items = [
            ("updates", lambda: run_detached("plasma-discover", "--mode", "update")),
            ("store", lambda: run_detached("plasma-discover")),
            ("rpmfusion", lambda: self.helper("enable-rpmfusion")),
            ("flathub", lambda: self.helper("enable-flathub")),
            ("network", lambda: kcm("kcm_networkmanagement")),
            ("bluetooth", lambda: kcm("kcm_bluetooth")),
            ("sound", lambda: kcm("kcm_pulseaudio")),
            ("display", lambda: kcm("kcm_kscreen")),
            ("users", lambda: kcm("kcm_users")),
            ("allset", lambda: run_detached("systemsettings")),
        ]
        for i, (k, fn) in enumerate(items):
            b = button(T(k), fn)
            b.setMinimumHeight(40)
            g.addWidget(b, i // 2, i % 2)
        v.addLayout(g)
        self.msg = QLabel()
        v.addWidget(self.msg)
        v.addStretch()

    def helper(self, cmd):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            r = subprocess.run(HELPER + [cmd], capture_output=True, text=True)
        finally:
            QApplication.restoreOverrideCursor()
        self.msg.setText("Done." if r.returncode == 0 else r.stderr.strip()[-400:])


# ------------------------------------------------------------------ window
class Center(QMainWindow):
    PAGES = [("welcome", WelcomePage, "credo"), ("devotions", DevotionsPage, "credo-marian"),
             ("liturgy", LiturgyPage, "credo-ihs"), ("library", LibraryPage, "credo-keys"),
             ("study", StudyPage, "accessories-dictionary"), ("macapps", MacAppsPage, "credo-macapps"),
             ("winapps", WinAppsPage, "credo-winapps"),
             ("appearance", AppearancePage, "preferences-desktop-theme"),
             ("thinkpad", ThinkPadPage, "computer-laptop"), ("system", SystemPage, "preferences-system")]

    def __init__(self, start=0):
        super().__init__()
        self.setWindowTitle(T("title"))
        self.setWindowIcon(QIcon.fromTheme("credo"))
        self.resize(940, 680)
        central = QWidget()
        h = QHBoxLayout(central)
        side = QVBoxLayout()
        self.nav = QListWidget()
        self.nav.setFixedWidth(200)
        self.stack = QStackedWidget()
        for key, cls, icon in self.PAGES:
            self.nav.addItem(QListWidgetItem(QIcon.fromTheme(icon), T(key)))
            self.stack.addWidget(cls())
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        side.addWidget(self.nav)
        self.lang = QComboBox()
        self.lang.addItem("English", "en")
        self.lang.addItem("Latina", "la")
        self.lang.setCurrentIndex(self.lang.findData(config.language()))
        self.lang.currentIndexChanged.connect(self.switch_language)
        side.addWidget(QLabel(T("language")))
        side.addWidget(self.lang)
        h.addLayout(side)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.go(start)

    def go(self, index):
        self.nav.setCurrentRow(index)

    def go_key(self, key):
        self.go(next(i for i, (k, _, _) in enumerate(self.PAGES) if k == key))

    def switch_language(self):
        lang = self.lang.currentData()
        config.set_value("general", "language", lang)
        set_desktop_language(lang)
        QMessageBox.information(self, T("language"), T("relogin"))
        row = self.nav.currentRow()
        self.hide()
        new = Center(row)
        new.show()
        QApplication.instance()._win = new
        self.deleteLater()


def main(argv=None):
    argv = sys.argv if argv is None else argv
    app = QApplication(argv)
    app.setApplicationName("Credo Center")
    app.setDesktopFileName("credo-center")
    start = 0
    for i, (k, _, _) in enumerate(Center.PAGES):
        if f"--{k}" in argv:
            start = i
    app._win = Center(start)
    # "credo-center --macapps FILE.dmg" (double-clicking a Mac app): look it up straight away
    for flag in ("--macapps", "--winapps"):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                page = app._win.stack.widget(start)
                page.query.setText(argv[i + 1].rstrip("/").split("/")[-1])
    app._win.show()
    return app.exec()
