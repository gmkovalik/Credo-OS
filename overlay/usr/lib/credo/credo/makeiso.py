"""Make Credo ISO: build an installable Credo OS ISO of the Credo version on this computer.

The work is done by /usr/libexec/credo/make-iso (as administrator, through pkexec); this window
shows its progress. The finished ISO goes to the Downloads folder.
"""
import getpass
import shutil
import subprocess
import sys

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit,
                               QPushButton, QVBoxLayout, QWidget)

from . import config

BACKEND = "/usr/libexec/credo/make-iso"


def T(en, la):
    return la if config.language() == "la" else en


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(T("Make Credo ISO", "Fac imaginem ISO Credo"))
        self.setWindowIcon(QIcon.fromTheme("media-optical-burn", QIcon.fromTheme("credo")))
        self.resize(760, 560)
        v = QVBoxLayout()
        v.setContentsMargins(28, 24, 28, 20)
        head = QLabel(f"<h2>{T('Make an ISO of this Credo OS', 'Fac imaginem ISO huius Credo OS')}</h2>"
                      + T("<p>Builds a new installable Credo OS image with every Credo update on this computer, "
                          "from fresh Fedora packages. The ISO (about 5–6 GB) is saved in your <b>Downloads</b> "
                          "folder.</p><p>Needs about <b>20 GB free</b>, an internet connection and "
                          "<b>30–60 minutes</b>. Keep the laptop plugged in; it will not go to sleep.</p>",
                          "<p>Imago nova cum omnibus renovationibus Credo. In <b>Depositiones</b> servatur. "
                          "Opus est 20 GB et conexione interretiali; 30–60 minuta.</p>"))
        head.setWordWrap(True)
        v.addWidget(head)
        self.apps = QCheckBox(T("Also include the apps I installed myself", "Etiam applicationes a me institutas adde"))
        self.public = QCheckBox(T("Public version: leave out personal photos (church wallpapers)",
                                  "Versio publica: imagines privatas omitte"))
        v.addWidget(self.apps)
        v.addWidget(self.public)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("monospace", 9))
        self.log.setPlaceholderText(T("Progress will appear here.", "Progressus hic apparebit."))
        v.addWidget(self.log, 1)
        row = QHBoxLayout()
        self.status = QLabel("")
        row.addWidget(self.status, 1)
        self.open_btn = QPushButton(T("Open Downloads", "Aperi Depositiones"))
        self.open_btn.clicked.connect(lambda: subprocess.Popen(["xdg-open", self.downloads()],
                                                               start_new_session=True))
        self.open_btn.hide()
        row.addWidget(self.open_btn)
        self.go = QPushButton(T("Build ISO", "Fac ISO"))
        self.go.setDefault(True)
        self.go.clicked.connect(self.start)
        row.addWidget(self.go)
        v.addLayout(row)
        w = QWidget()
        w.setLayout(v)
        self.setCentralWidget(w)
        self.proc = None

    @staticmethod
    def downloads():
        r = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True)
        return r.stdout.strip() or str(config.HOME / "Downloads")

    def start(self):
        if not shutil.which("pkexec"):
            self.status.setText(T("pkexec is missing.", "pkexec deest."))
            return
        args = [BACKEND, "--user", getpass.getuser()]
        if self.apps.isChecked():
            args.append("--include-apps")
        if self.public.isChecked():
            args.append("--public")
        self.log.clear()
        self.go.setEnabled(False)
        self.apps.setEnabled(False)
        self.public.setEnabled(False)
        self.open_btn.hide()
        self.status.setText(T("Building… (asks for your password)", "Aedificatur…"))
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self.read)
        self.proc.finished.connect(self.done)
        self.proc.start("pkexec", args)

    def read(self):
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.log.moveCursor(QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QTextCursor.MoveOperation.End)

    def done(self, code, _status):
        self.go.setEnabled(True)
        self.apps.setEnabled(True)
        self.public.setEnabled(True)
        if code == 0:
            self.status.setText(T("Done: the ISO is in Downloads.", "Factum: ISO in Depositionibus est."))
            self.open_btn.show()
        elif code in (126, 127):
            self.status.setText(T("Cancelled (password not given).", "Abrogatum."))
        else:
            self.status.setText(T(f"Stopped with an error (code {code}); see the log above.",
                                  f"Error (codex {code})."))

    def closeEvent(self, e):
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.status.setText(T("Still building: wait for it to finish.", "Adhuc aedificatur."))
            e.ignore()
            return
        e.accept()


def main(argv=None):
    app = QApplication(list(sys.argv if argv is None else argv))
    app.setApplicationName("Make Credo ISO")
    app.setDesktopFileName("credo-make-iso")
    w = Window()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
