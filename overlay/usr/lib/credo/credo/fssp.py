"""FSSP: the Priestly Fraternity of St. Peter's monthly prayer card and its magazine Cum Petro,
in one window (Qt WebEngine, with its built-in PDF viewer).

    credo-fssp            open (the prayer card)
    credo-fssp cumpetro   open Cum Petro
"""
import pathlib
import subprocess
import sys

from PySide6.QtCore import QStandardPaths, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QToolButton

from . import config

PAGES = [("card", "Prayer Card", "Imago precum", "https://fssp.com/fssp-monthly-prayer-card/"),
         ("cumpetro", "Cum Petro", "Cum Petro", "https://fssp.com/cum-petro/")]


def T(en, la):
    return la if config.language() == "la" else en


class Window(QMainWindow):
    def __init__(self, start="card"):
        super().__init__()
        self.setWindowTitle("FSSP")
        self.setWindowIcon(QIcon.fromTheme("credo-fssp"))
        self.resize(1100, 820)
        profile = QWebEngineProfile("credo-fssp", self)
        profile.setPersistentStoragePath(str(config.DATA_DIR / "fssp"))
        profile.downloadRequested.connect(self.download)
        s = profile.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)        # built-in PDF viewer
        s.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        self.view = QWebEngineView()
        self.view.setPage(QWebEnginePage(profile, self.view))
        self.setCentralWidget(self.view)

        bar = QToolBar()
        bar.setMovable(False)
        self.addToolBar(bar)
        bar.addAction(QIcon.fromTheme("go-previous"), T("Back", "Retro"), self.view.back)
        bar.addAction(QIcon.fromTheme("go-next"), T("Forward", "Porro"), self.view.forward)
        bar.addSeparator()
        self.buttons = {}
        for key, en, la, url in PAGES:
            b = QToolButton()
            b.setText(T(en, la))
            b.setCheckable(True)
            b.setAutoRaise(True)
            b.clicked.connect(lambda _=False, k=key: self.go(k))
            bar.addWidget(b)
            self.buttons[key] = b
        bar.addSeparator()
        bar.addAction(QIcon.fromTheme("internet-web-browser"), T("Open in browser", "Aperi in navigatore"),
                      lambda: subprocess.Popen(["credo-browser", self.view.url().toString()],
                                               start_new_session=True))
        self.view.titleChanged.connect(lambda t: self.setWindowTitle(f"{t} — FSSP" if t else "FSSP"))
        self.go(start if start in self.buttons else "card")

    def go(self, key):
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        self.view.setUrl(QUrl(next(u for k, _, _, u in PAGES if k == key)))

    def download(self, item):
        """PDFs and other files: save to Downloads (the PDF viewer opens PDFs in the window itself)."""
        folder = pathlib.Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation))
        item.setDownloadDirectory(str(folder))
        item.accept()


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication(argv)
    app.setApplicationName("FSSP")
    app.setDesktopFileName("credo-fssp")
    w = Window(argv[1] if len(argv) > 1 else "card")
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
