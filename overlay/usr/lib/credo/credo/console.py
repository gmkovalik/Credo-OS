"""Credo Console: a terminal emulator for Credo OS (PySide6 + pyte).

A real pseudo-terminal running your shell, xterm-256color with true color, tabs, scrollback,
the alternate screen (vim, less, htop), mouse reporting, selection and clipboard, bracketed
paste, Ctrl+click links, find in scrollback, font zoom, Credo color schemes, new tabs in the
current directory, and today's liturgical day as a greeting.

    credo-console [-e COMMAND ...] [--workdir DIR]
"""
import fcntl
import os
import pty
import re
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import termios

import pyte
from PySide6.QtCore import QPoint, QRect, QSocketNotifier, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF, QGuiApplication, QIcon, QKeySequence,
                           QPainter, QPalette)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFontComboBox,
                               QFormLayout, QHBoxLayout, QLineEdit, QMainWindow, QMenu, QScrollBar, QSpinBox,
                               QTabWidget, QToolBar, QToolButton, QWidget)

from . import config, liturgy, palettes

TR = {
    "new_tab": ("New tab", "Nova tabula"), "new_window": ("New window", "Nova fenestra"),
    "copy": ("Copy", "Exscribe"), "paste": ("Paste", "Insere"), "select_all": ("Select all", "Selige omnia"),
    "find": ("Find…", "Quaere…"), "zoom_in": ("Larger text", "Litterae maiores"),
    "zoom_out": ("Smaller text", "Litterae minores"), "zoom_reset": ("Default size", "Magnitudo solita"),
    "clear": ("Clear scrollback", "Purga historiam"), "reset": ("Reset terminal", "Restitue terminale"),
    "scheme": ("Colors", "Colores"), "settings": ("Settings…", "Optiones…"),
    "close_tab": ("Close tab", "Claude tabulam"), "quit": ("Quit", "Exi"),
    "font": ("Font", "Typus litterarum"), "size": ("Size", "Magnitudo"),
    "scrollback": ("Scrollback lines", "Lineae historiae"), "greeting": ("Show today's feast when opening",
                                                                       "Ostende festum hodiernum"),
    "open_link": ("Open link", "Aperi nexum"), "copy_link": ("Copy link", "Exscribe nexum"),
}


def T(key):
    en, la = TR.get(key, (key, key))
    return la if config.language() == "la" else en


# ------------------------------------------------------------------ colors
ANSI_DARK = ["#1d1f21", "#cc4b4b", "#7fa35b", "#d6a64a", "#5f8fc4", "#a476b8", "#5aa8a8", "#d0d0c8",
             "#6b6b66", "#e86a6a", "#9fc77a", "#f0c674", "#81a8db", "#c397d8", "#7fcccc", "#ffffff"]
ANSI_LIGHT = ["#2b2417", "#b02a2a", "#4d7a24", "#8f6a10", "#2f5fa7", "#7d3c98", "#1f7a7a", "#d8d0c0",
              "#6b6252", "#d13b3b", "#5f9530", "#a8801c", "#3b74c4", "#9b4fb8", "#2a9393", "#fffdf7"]
NAMES = ["black", "red", "green", "brown", "blue", "magenta", "cyan", "white"]

SCHEMES = {"credo": ("Credo (follows the theme)", "Credo (secundum thema)")}
SCHEMES.update({k: v for k, v in palettes.VARIANTS.items() if k != "liturgical"})


def scheme_colors(key):
    variant = config.load().get("appearance", "variant", fallback="monastic") if key == "credo" else key
    try:
        _, p = palettes.resolve(variant)
    except Exception:
        _, p = palettes.resolve("monastic")
    ansi = list(ANSI_DARK if p["dark"] else ANSI_LIGHT)
    bg = p["view"]
    if not p["dark"]:
        ansi[7] = p["fg_dim"]                 # "white" text must stay readable on a light page
    table = {}
    for i, n in enumerate(NAMES):
        table[n] = QColor(ansi[i])
        table["bright" + n] = QColor(ansi[i + 8])
    table["yellow"], table["brightyellow"] = table["brown"], table["brightbrown"]
    return {"fg": QColor(p["fg"]), "bg": QColor(bg), "cursor": QColor(p["accent"]),
            "sel": QColor(p["accent"]), "gold": QColor(p["logo"]), "ansi": table, "dark": p["dark"]}


def to_qcolor(value, table, default):
    if value == "default":
        return default
    c = table.get(value)
    if c is not None:
        return c
    if len(value) == 6:
        try:
            int(value, 16)
            return QColor("#" + value)
        except ValueError:
            pass
    return default


# ------------------------------------------------------------------ emulation
class Screen(pyte.HistoryScreen):
    """pyte screen plus the alternate screen buffer, private-mode tracking and replies to the app."""

    def __init__(self, cols, rows, history, reply, bell):
        super().__init__(cols, rows, history=history, ratio=0.5)
        self.private = set()
        self._alt = None
        self._reply, self._bell = reply, bell

    def write_process_input(self, data):
        self._reply(data)

    def bell(self, *args):
        self._bell()

    def set_mode(self, *modes, **kw):
        if kw.get("private"):
            self.private.update(modes)
            if {47, 1047, 1049} & set(modes) and self._alt is None:
                self._alt = ({y: dict(line) for y, line in self.buffer.items()}, self.cursor.x, self.cursor.y)
                self.buffer.clear()
                self.dirty.update(range(self.lines))
        super().set_mode(*modes, **kw)

    def reset_mode(self, *modes, **kw):
        if kw.get("private"):
            self.private.difference_update(modes)
            if {47, 1047, 1049} & set(modes) and self._alt is not None:
                saved, x, y = self._alt
                self._alt = None
                self.buffer.clear()
                for row, line in saved.items():
                    if row < self.lines:
                        self.buffer[row].update(line)
                self.cursor.x, self.cursor.y = min(x, self.columns - 1), min(y, self.lines - 1)
                self.dirty.update(range(self.lines))
        super().reset_mode(*modes, **kw)

    @property
    def alternate(self):
        return self._alt is not None

    def index(self):
        if self._alt is not None:                 # full-screen apps don't fill the scrollback
            return pyte.Screen.index(self)
        return super().index()


URL_RE = re.compile(r"(https?://|file://|www\.)[^\s<>\"'`]+[^\s<>\"'`.,;:!?)\]]")

SPECIAL = {Qt.Key_Return: b"\r", Qt.Key_Enter: b"\r", Qt.Key_Backspace: b"\x7f", Qt.Key_Tab: b"\t",
           Qt.Key_Backtab: b"\x1b[Z", Qt.Key_Escape: b"\x1b", Qt.Key_Insert: b"\x1b[2~",
           Qt.Key_Delete: b"\x1b[3~", Qt.Key_PageUp: b"\x1b[5~", Qt.Key_PageDown: b"\x1b[6~",
           Qt.Key_F1: b"\x1bOP", Qt.Key_F2: b"\x1bOQ", Qt.Key_F3: b"\x1bOR", Qt.Key_F4: b"\x1bOS",
           Qt.Key_F5: b"\x1b[15~", Qt.Key_F6: b"\x1b[17~", Qt.Key_F7: b"\x1b[18~", Qt.Key_F8: b"\x1b[19~",
           Qt.Key_F9: b"\x1b[20~", Qt.Key_F10: b"\x1b[21~", Qt.Key_F11: b"\x1b[23~", Qt.Key_F12: b"\x1b[24~"}
CURSOR_KEYS = {Qt.Key_Up: "A", Qt.Key_Down: "B", Qt.Key_Right: "C", Qt.Key_Left: "D", Qt.Key_Home: "H",
               Qt.Key_End: "F"}


def default_shell():
    sh = os.environ.get("SHELL")
    if not sh:
        try:
            import pwd
            sh = pwd.getpwuid(os.getuid()).pw_shell
        except (KeyError, ImportError):
            sh = None
    return sh if sh and os.path.exists(sh) else "/bin/bash"


def greeting(colors):
    """A short line about the liturgical day, written straight to the screen (not the shell)."""
    L = config.language()
    d = liturgy.today()
    from . import devotions
    myst = devotions.MYSTERIES[devotions.mysteries_for(d.date)]
    gold = colors["gold"]
    day = QColor(d.color_hex)
    title = d.feast(L) or d.title(L)
    rosary = ("Rosarium: " + myst[1]) if L == "la" else ("Rosary: " + myst[0])
    notes = f" · {', '.join(d.notes)}" if d.notes else ""
    return (f"\x1b[1;38;2;{gold.red()};{gold.green()};{gold.blue()}m✠ {title}\x1b[0m\r\n"
            f"\x1b[38;2;{day.red()};{day.green()};{day.blue()}m●\x1b[0m\x1b[2m {d.date:%A %d %B %Y} · "
            f"{d.season_name(L)} · {rosary}{notes}\x1b[0m\r\n\r\n")


class Terminal(QWidget):
    titleChanged = Signal(str)
    finished = Signal()

    def __init__(self, command=None, workdir=None, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_InputMethodEnabled)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setCursor(Qt.IBeamCursor)
        cp = config.load()
        self.font_family = cp.get("console", "font", fallback="")
        self.base_size = cp.getint("console", "size", fallback=11)
        self.font_size = self.base_size
        self.colors = scheme_colors(cp.get("console", "scheme", fallback="credo"))
        history = cp.getint("console", "scrollback", fallback=10000)
        self.screen = Screen(80, 24, history, self._write_reply, self._flash)
        self.stream = pyte.ByteStream(self.screen)
        self.offset = 0                 # lines scrolled back into history
        self.sel = None                 # ((row, col), (row, col)) in view coordinates
        self.pressed = None
        self.flash = False
        self.title = ""
        self.fd = None
        self.pid = None
        self.vbar = QScrollBar(Qt.Vertical, self)
        self.vbar.valueChanged.connect(self._scrolled)
        self._apply_font()
        if cp.getboolean("console", "greeting", fallback=True) and command is None:
            try:
                self.stream.feed(greeting(self.colors).encode())
            except Exception:
                pass
        self._spawn(command, workdir)

    # ---- process
    def _spawn(self, command, workdir):
        shell = default_shell()
        argv = ["/bin/sh", "-c", command] if command else [shell]
        env = dict(os.environ, TERM="xterm-256color", COLORTERM="truecolor", TERM_PROGRAM="credo-console")
        env.pop("COLUMNS", None)
        env.pop("LINES", None)
        pid, fd = pty.fork()
        if pid == 0:                                    # child
            try:
                os.chdir(workdir or os.path.expanduser("~"))
            except OSError:
                pass
            try:
                os.execvpe(argv[0], argv, env)
            finally:
                os._exit(127)
        self.pid, self.fd = pid, fd
        os.set_blocking(fd, False)
        self.notifier = QSocketNotifier(fd, QSocketNotifier.Read, self)
        self.notifier.activated.connect(self._read)
        self._resize_pty()

    def _read(self, *_):
        try:
            data = os.read(self.fd, 1 << 16)
        except BlockingIOError:
            return
        except OSError:
            data = b""
        if not data:
            self._exited()
            return
        self.stream.feed(data)
        if self.screen.title != self.title:
            self.title = self.screen.title
            self.titleChanged.emit(self.title)
        if self.offset == 0:
            self.sel = None if self.sel and self.screen.dirty else self.sel
        self.screen.dirty.clear()
        self._update_scrollbar()
        self.update()

    def _exited(self):
        if self.notifier:
            self.notifier.setEnabled(False)
        try:
            os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            pass
        try:
            os.close(self.fd)
        except OSError:
            pass
        self.fd = None
        self.finished.emit()

    def send(self, data):
        if self.fd is None:
            return
        if self.offset:
            self.scroll_to_bottom()
        try:
            os.write(self.fd, data)
        except OSError:
            pass

    def _write_reply(self, text):
        self.send(text.encode() if isinstance(text, str) else text)

    def _flash(self):
        self.flash = True
        self.update()
        QTimer.singleShot(120, lambda: (setattr(self, "flash", False), self.update()))

    def close_process(self):
        if self.pid:
            try:
                os.killpg(os.getpgid(self.pid), signal.SIGHUP)
            except (ProcessLookupError, PermissionError, OSError):
                pass
            try:
                os.waitpid(self.pid, os.WNOHANG)
            except ChildProcessError:
                pass
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def cwd(self):
        try:
            return os.readlink(f"/proc/{self.pid}/cwd")
        except OSError:
            return None

    def busy(self):
        """True when a program other than the shell is in the foreground."""
        try:
            return os.tcgetpgrp(self.fd) != self.pid
        except OSError:
            return False

    # ---- geometry and fonts
    def _apply_font(self):
        f = QFont(self.font_family) if self.font_family else QFontDatabase.systemFont(QFontDatabase.FixedFont)
        f.setStyleHint(QFont.TypeWriter)
        f.setFixedPitch(True)
        f.setPointSizeF(self.font_size)
        self.font_ = f
        self.bold_font = QFont(f)
        self.bold_font.setBold(True)
        fm = QFontMetricsF(f)
        self.cw = max(1.0, fm.horizontalAdvance("M"))
        self.ch = max(1.0, round(fm.height()))
        self.ascent = fm.ascent()
        self._resize_pty()
        self.update()

    def zoom(self, d):
        self.font_size = self.base_size if d == 0 else max(6, min(48, self.font_size + d))
        self._apply_font()

    def resizeEvent(self, e):
        sw = self.vbar.sizeHint().width()
        self.vbar.setGeometry(self.width() - sw, 0, sw, self.height())
        self._resize_pty()

    def _resize_pty(self):
        if not hasattr(self, "screen"):
            return
        sw = self.vbar.sizeHint().width() if hasattr(self, "vbar") else 0
        cols = max(2, int((self.width() - sw - 8) // self.cw))
        rows = max(1, int((self.height() - 6) // self.ch))
        if (rows, cols) != (self.screen.lines, self.screen.columns):
            self.screen.resize(rows, cols)
            self.offset = min(self.offset, len(self.screen.history.top))
        if self.fd is not None:
            try:
                fcntl.ioctl(self.fd, termios.TIOCSWINSZ,
                            struct.pack("HHHH", rows, cols, int(cols * self.cw), int(rows * self.ch)))
            except OSError:
                pass
        self._update_scrollbar()

    # ---- scrollback
    def _update_scrollbar(self):
        n = len(self.screen.history.top)
        self.vbar.blockSignals(True)
        self.vbar.setRange(0, n)
        self.vbar.setPageStep(self.screen.lines)
        self.vbar.setValue(n - self.offset)
        self.vbar.blockSignals(False)
        self.vbar.setVisible(n > 0 and not self.screen.alternate)

    def _scrolled(self, value):
        self.offset = len(self.screen.history.top) - value
        self.sel = None
        self.update()

    def scroll_lines(self, n):
        self.sel = None
        self.offset = max(0, min(len(self.screen.history.top), self.offset + n))
        self._update_scrollbar()
        self.update()

    def scroll_to_bottom(self):
        self.sel = None
        self.offset = 0
        self._update_scrollbar()
        self.update()

    def all_lines(self):
        return list(self.screen.history.top) + [self.screen.buffer[y] for y in range(self.screen.lines)]

    def view_line(self, row):
        hist = self.screen.history.top
        if self.offset and row < self.offset:
            return hist[len(hist) - self.offset + row]
        return self.screen.buffer[row - self.offset]

    def line_text(self, line):
        cols = self.screen.columns
        return "".join(line[x].data if x in line else " " for x in range(cols))

    # ---- painting
    def paintEvent(self, e):
        p = QPainter(self)
        c = self.colors
        bg_default, fg_default = c["bg"], c["fg"]
        p.fillRect(self.rect(), bg_default)
        default_char = self.screen.default_char
        sel = self._sel_range()
        for row in range(self.screen.lines):
            line = self.view_line(row)
            y = 3 + row * self.ch
            run_attrs, run_text, run_start = None, [], 0
            for col in range(self.screen.columns + 1):
                if col < self.screen.columns:
                    ch = line[col] if col in line else default_char
                    selected = sel and self._in_sel(sel, row, col)
                    attrs = (ch.fg, ch.bg, ch.bold, ch.italics, ch.underscore, ch.strikethrough,
                             ch.reverse, selected)
                else:
                    attrs, ch = None, None
                if attrs != run_attrs:
                    if run_attrs is not None:
                        self._draw_run(p, run_attrs, "".join(run_text), run_start, y, col - run_start)
                    run_attrs, run_text, run_start = attrs, [], col
                if ch is not None:
                    run_text.append(ch.data or "")
        # cursor
        if self.offset == 0 and not self.screen.cursor.hidden:
            cx = 4 + self.screen.cursor.x * self.cw
            cy = 3 + self.screen.cursor.y * self.ch
            r = QRect(int(cx), int(cy), int(self.cw), int(self.ch))
            if self.hasFocus():
                p.fillRect(r, c["cursor"])
                line = self.screen.buffer[self.screen.cursor.y]
                ch = line[self.screen.cursor.x] if self.screen.cursor.x in line else None
                if ch is not None and ch.data.strip():
                    p.setFont(self.bold_font if ch.bold else self.font_)
                    p.setPen(bg_default)
                    p.drawText(QPoint(int(cx), int(cy + self.ascent)), ch.data)
            else:
                p.setPen(c["cursor"])
                p.drawRect(r.adjusted(0, 0, -1, -1))
        if self.flash:
            col = QColor(c["fg"])
            col.setAlpha(40)
            p.fillRect(self.rect(), col)

    def _draw_run(self, p, attrs, text, col, y, n):
        fg, bg, bold, italics, underscore, strike, reverse, selected = attrs
        table = self.colors["ansi"]
        fgc = to_qcolor(fg, table, self.colors["fg"])
        bgc = to_qcolor(bg, table, self.colors["bg"])
        if bold and fg in NAMES:                        # bold + basic color -> bright color, like xterm
            fgc = table["bright" + fg]
        if reverse:
            fgc, bgc = bgc, fgc
        if selected:
            bgc = QColor(self.colors["sel"])
            bgc.setAlpha(150)
        x = 4 + col * self.cw
        if bgc != self.colors["bg"] or selected:
            p.fillRect(QRect(int(x), int(y), int(n * self.cw + 0.99), int(self.ch)), bgc)
        if not text.strip():
            return
        f = self.bold_font if bold else self.font_
        if italics:
            f = QFont(f)
            f.setItalic(True)
        if underscore or strike:
            f = QFont(f)
            f.setUnderline(bool(underscore))
            f.setStrikeOut(bool(strike))
        p.setFont(f)
        p.setPen(fgc)
        # draw cell by cell when the font isn't perfectly monospaced for these glyphs
        width = QFontMetricsF(f).horizontalAdvance(text)
        if abs(width - n * self.cw) < 0.5 * self.cw:
            p.drawText(QPoint(int(x), int(y + self.ascent)), text)
        else:
            for i, chr_ in enumerate(text):
                p.drawText(QPoint(int(x + i * self.cw), int(y + self.ascent)), chr_)

    # ---- selection
    def _cell_at(self, pos):
        col = int((pos.x() - 4) // self.cw)
        row = int((pos.y() - 3) // self.ch)
        return (max(0, min(self.screen.lines - 1, row)), max(0, min(self.screen.columns - 1, col)))

    def _sel_range(self):
        if not self.sel:
            return None
        a, b = self.sel
        return (a, b) if a <= b else (b, a)

    @staticmethod
    def _in_sel(sel, row, col):
        (r1, c1), (r2, c2) = sel
        if row < r1 or row > r2:
            return False
        if r1 == r2:
            return c1 <= col <= c2
        if row == r1:
            return col >= c1
        if row == r2:
            return col <= c2
        return True

    def selected_text(self):
        sel = self._sel_range()
        if not sel:
            return ""
        (r1, c1), (r2, c2) = sel
        out = []
        for row in range(r1, r2 + 1):
            text = self.line_text(self.view_line(row))
            a = c1 if row == r1 else 0
            b = c2 + 1 if row == r2 else len(text)
            out.append(text[a:b].rstrip())
        return "\n".join(out)

    def copy(self):
        t = self.selected_text()
        if t:
            QGuiApplication.clipboard().setText(t)

    def paste(self, mode=None):
        cb = QGuiApplication.clipboard()
        text = cb.text(mode) if mode is not None else cb.text()
        if not text:
            return
        data = text.replace("\r\n", "\r").replace("\n", "\r").encode()
        if 2004 in self.screen.private:
            data = b"\x1b[200~" + data + b"\x1b[201~"
        self.send(data)

    def select_all(self):
        self.sel = ((0, 0), (self.screen.lines - 1, self.screen.columns - 1))
        self.update()

    def link_at(self, pos):
        row, col = self._cell_at(pos)
        text = self.line_text(self.view_line(row))
        for m in URL_RE.finditer(text):
            if m.start() <= col < m.end():
                url = m.group(0)
                return url if "://" in url else "https://" + url
        return None

    # ---- mouse
    def _mouse_reporting(self):
        return bool({1000, 1002, 1003} & self.screen.private)

    def _report(self, button, pos, release=False, motion=False):
        row, col = self._cell_at(pos)
        b = button + (32 if motion else 0)
        if 1006 in self.screen.private:
            self.send(f"\x1b[<{b};{col + 1};{row + 1}{'m' if release else 'M'}".encode())
        else:
            b = 3 if release else b
            self.send(b"\x1b[M" + bytes([32 + b, min(255, 33 + col), min(255, 33 + row)]))

    @staticmethod
    def _button_code(btn):
        return {Qt.LeftButton: 0, Qt.MiddleButton: 1, Qt.RightButton: 2}.get(btn, 0)

    def mousePressEvent(self, e):
        self.setFocus()
        if self._mouse_reporting() and not e.modifiers() & Qt.ShiftModifier:
            self._report(self._button_code(e.button()), e.position())
            return
        if e.button() == Qt.LeftButton:
            if e.modifiers() & Qt.ControlModifier:
                url = self.link_at(e.position())
                if url:
                    open_url(url)
                    return
            cell = self._cell_at(e.position())
            self.pressed = cell
            self.sel = None
            self.update()
        elif e.button() == Qt.MiddleButton:
            self.paste(QGuiApplication.clipboard().Mode.Selection)

    def mouseMoveEvent(self, e):
        if self._mouse_reporting() and not e.modifiers() & Qt.ShiftModifier:
            if e.buttons() and ({1002, 1003} & self.screen.private):
                self._report(self._button_code(e.buttons()), e.position(), motion=True)
            return
        if self.pressed and e.buttons() & Qt.LeftButton:
            self.sel = (self.pressed, self._cell_at(e.position()))
            self.update()

    def mouseReleaseEvent(self, e):
        if self._mouse_reporting() and not e.modifiers() & Qt.ShiftModifier:
            self._report(self._button_code(e.button()), e.position(), release=True)
            return
        self.pressed = None
        t = self.selected_text()
        if t:
            QGuiApplication.clipboard().setText(t, QGuiApplication.clipboard().Mode.Selection)

    def mouseDoubleClickEvent(self, e):
        if self._mouse_reporting():
            return
        row, col = self._cell_at(e.position())
        text = self.line_text(self.view_line(row))
        a = b = col
        word = re.compile(r"[\w\-./~:@%+=?&#]")
        while a > 0 and word.match(text[a - 1]):
            a -= 1
        while b < len(text) - 1 and word.match(text[b + 1]):
            b += 1
        self.sel = ((row, a), (row, b))
        QGuiApplication.clipboard().setText(self.selected_text(), QGuiApplication.clipboard().Mode.Selection)
        self.update()

    def wheelEvent(self, e):
        steps = e.angleDelta().y() // 120 or (1 if e.angleDelta().y() > 0 else -1 if e.angleDelta().y() else 0)
        if not steps:
            return
        if self._mouse_reporting():
            for _ in range(abs(steps)):
                self._report(64 if steps > 0 else 65, e.position())
        elif self.screen.alternate:
            self.send((b"\x1bOA" if steps > 0 else b"\x1bOB") * (abs(steps) * 3))
        else:
            self.scroll_lines(steps * 3)

    # ---- drag and drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        if md.hasUrls():
            text = " ".join(shlex.quote(u.toLocalFile() or u.toString()) for u in md.urls()) + " "
        else:
            text = md.text()
        self.send(text.encode())

    # ---- keyboard
    def focusNextPrevChild(self, _next):
        return False                                    # Tab goes to the shell, not to the next widget

    def inputMethodEvent(self, e):
        if e.commitString():
            self.send(e.commitString().encode())

    def keyPressEvent(self, e):
        key, mods = e.key(), e.modifiers()
        ctrl, shift, alt = bool(mods & Qt.ControlModifier), bool(mods & Qt.ShiftModifier), bool(mods & Qt.AltModifier)
        win = self.window()
        # terminal shortcuts (Ctrl+Shift+…), the rest goes to the program
        if ctrl and shift:
            action = {Qt.Key_C: self.copy, Qt.Key_V: self.paste, Qt.Key_T: getattr(win, "new_tab", None),
                      Qt.Key_W: getattr(win, "close_current", None), Qt.Key_N: getattr(win, "new_window", None),
                      Qt.Key_F: getattr(win, "open_find", None), Qt.Key_K: self.clear_scrollback,
                      Qt.Key_A: self.select_all}.get(key)
            if action:
                action()
                return
        if shift and key in (Qt.Key_PageUp, Qt.Key_PageDown) and not self.screen.alternate:
            self.scroll_lines(self.screen.lines - 1 if key == Qt.Key_PageUp else -(self.screen.lines - 1))
            return
        if shift and key == Qt.Key_Insert:
            self.paste(QGuiApplication.clipboard().Mode.Selection)
            return
        if ctrl and key in (Qt.Key_Equal, Qt.Key_Plus):
            self.zoom(1)
            return
        if ctrl and key == Qt.Key_Minus and not shift:
            self.zoom(-1)
            return
        if ctrl and key == Qt.Key_0:
            self.zoom(0)
            return
        if ctrl and key in (Qt.Key_PageUp, Qt.Key_PageDown) and hasattr(win, "cycle"):
            win.cycle(-1 if key == Qt.Key_PageUp else 1)
            return

        data = None
        if key in CURSOR_KEYS:
            c = CURSOR_KEYS[key]
            m = 1 + (1 if shift else 0) + (2 if alt else 0) + (4 if ctrl else 0)
            if m > 1:
                data = f"\x1b[1;{m}{c}".encode()
            else:
                app_mode = 1 in self.screen.private
                data = (("\x1bO" if app_mode else "\x1b[") + c).encode()
        elif key in SPECIAL:
            data = SPECIAL[key]
            if key == Qt.Key_Backspace and ctrl:
                data = b"\x08"
            elif key == Qt.Key_Tab and shift:
                data = b"\x1b[Z"
        elif ctrl and Qt.Key_A <= key <= Qt.Key_Z:
            data = bytes([key - Qt.Key_A + 1])
        elif ctrl and key in (Qt.Key_Space, Qt.Key_2, Qt.Key_At):
            data = b"\x00"
        elif ctrl and key in (Qt.Key_BracketLeft, Qt.Key_3):
            data = b"\x1b"
        elif ctrl and key in (Qt.Key_Backslash, Qt.Key_4):
            data = b"\x1c"
        elif ctrl and key in (Qt.Key_BracketRight, Qt.Key_5):
            data = b"\x1d"
        elif ctrl and key in (Qt.Key_6, Qt.Key_AsciiCircum):
            data = b"\x1e"
        elif ctrl and key in (Qt.Key_Underscore, Qt.Key_7, Qt.Key_Slash, Qt.Key_Minus):
            data = b"\x1f"
        elif e.text():
            data = e.text().encode()
        if data is None:
            return super().keyPressEvent(e)
        if alt and key not in CURSOR_KEYS and not data.startswith(b"\x1b["):
            data = b"\x1b" + data
        self.sel = None
        self.send(data)

    # ---- misc
    def clear_scrollback(self):
        self.screen.history.top.clear()
        self.offset = 0
        self._update_scrollbar()
        self.update()

    def reset(self):
        self.screen.reset()
        self.clear_scrollback()
        self.send(b"\x0c")

    def set_colors(self, key):
        self.colors = scheme_colors(key)
        self.update()

    def find(self, text, backwards=True):
        """Scroll to the previous (or next) line containing text and select it."""
        if not text:
            return False
        lines = self.all_lines()          # history first, then the screen; index i is absolute
        n_hist = len(self.screen.history.top)
        if getattr(self, "_find_text", None) != text:
            self._find_text, self._find_pos = text, len(lines)
        start = self._find_pos
        rng = range(start - 1, -1, -1) if backwards else range(start + 1, len(lines))
        low = text.lower()
        for i in rng:
            t = self.line_text(lines[i])
            k = t.lower().find(low)
            if k >= 0:
                self._find_pos = i
                # The view starts at absolute line (n_hist - offset); center the match in it.
                self.offset = 0 if i >= n_hist else max(0, min(n_hist, n_hist - i + self.screen.lines // 2))
                view_row = i - (n_hist - self.offset)
                if 0 <= view_row < self.screen.lines:
                    self.sel = ((view_row, k), (view_row, k + len(text) - 1))
                self._update_scrollbar()
                self.update()
                return True
        return False

    def contextMenuEvent(self, e):
        m = QMenu(self)
        url = self.link_at(e.pos())
        if url:
            m.addAction(QIcon.fromTheme("internet-web-browser"), T("open_link"), lambda: open_url(url))
            m.addAction(T("copy_link"), lambda: QGuiApplication.clipboard().setText(url))
            m.addSeparator()
        m.addAction(QIcon.fromTheme("edit-copy"), T("copy"), self.copy, QKeySequence("Ctrl+Shift+C"))
        m.addAction(QIcon.fromTheme("edit-paste"), T("paste"), self.paste, QKeySequence("Ctrl+Shift+V"))
        m.addAction(QIcon.fromTheme("edit-select-all"), T("select_all"), self.select_all)
        m.addSeparator()
        w = self.window()
        if hasattr(w, "new_tab"):
            m.addAction(QIcon.fromTheme("tab-new"), T("new_tab"), w.new_tab, QKeySequence("Ctrl+Shift+T"))
        m.addAction(QIcon.fromTheme("edit-clear-history"), T("clear"), self.clear_scrollback,
                    QKeySequence("Ctrl+Shift+K"))
        m.exec(e.globalPos())


def open_url(url):
    for cmd in (["credo-browser", url], ["xdg-open", url]):
        if shutil.which(cmd[0]):
            subprocess.Popen(cmd, start_new_session=True)
            return


# ------------------------------------------------------------------ window
class SettingsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.setWindowTitle(T("settings"))
        cp = config.load()
        f = QFormLayout(self)
        self.font_box = QFontComboBox()
        self.font_box.setFontFilters(QFontComboBox.MonospacedFonts)
        fam = cp.get("console", "font", fallback="")
        if fam:
            self.font_box.setCurrentFont(QFont(fam))
        self.size_box = QSpinBox()
        self.size_box.setRange(6, 48)
        self.size_box.setValue(cp.getint("console", "size", fallback=11))
        self.scheme = QComboBox()
        la = config.language() == "la"
        for k, names in SCHEMES.items():
            self.scheme.addItem(names[1 if la else 0], k)
        self.scheme.setCurrentIndex(max(0, self.scheme.findData(cp.get("console", "scheme", fallback="credo"))))
        self.lines_box = QSpinBox()
        self.lines_box.setRange(500, 200000)
        self.lines_box.setSingleStep(1000)
        self.lines_box.setValue(cp.getint("console", "scrollback", fallback=10000))
        self.greet = QCheckBox()
        self.greet.setChecked(cp.getboolean("console", "greeting", fallback=True))
        f.addRow(T("font"), self.font_box)
        f.addRow(T("size"), self.size_box)
        f.addRow(T("scheme"), self.scheme)
        f.addRow(T("scrollback"), self.lines_box)
        f.addRow(T("greeting"), self.greet)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def accept(self):
        for k, v in (("font", self.font_box.currentFont().family()), ("size", self.size_box.value()),
                     ("scheme", self.scheme.currentData()), ("scrollback", self.vbar.value()),
                     ("greeting", str(self.greet.isChecked()).lower())):
            config.set_value("console", k, str(v))
        super().accept()


class ConsoleWindow(QMainWindow):
    def __init__(self, app, command=None, workdir=None):
        super().__init__()
        self.app = app
        self.setWindowTitle("Credo Console")
        self.setWindowIcon(QIcon.fromTheme("credo-console"))
        self.resize(960, 600)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._tab_changed)
        corner = QWidget()
        h = QHBoxLayout(corner)
        h.setContentsMargins(0, 0, 4, 0)
        plus = QToolButton()
        plus.setIcon(QIcon.fromTheme("tab-new"))
        plus.setAutoRaise(True)
        plus.setToolTip(T("new_tab"))
        plus.clicked.connect(self.new_tab)
        menu = QToolButton()
        menu.setIcon(QIcon.fromTheme("application-menu"))
        menu.setAutoRaise(True)
        menu.setPopupMode(QToolButton.InstantPopup)
        menu.setMenu(self._menu())
        h.addWidget(plus)
        h.addWidget(menu)
        self.tabs.setCornerWidget(corner, Qt.TopRightCorner)
        self.setCentralWidget(self.tabs)

        self.findbar = QToolBar()
        self.findbar.setMovable(False)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText(T("find"))
        self.find_edit.returnPressed.connect(lambda: self.term() and self.term().find(self.find_edit.text()))
        self.findbar.addWidget(self.find_edit)
        self.findbar.addAction(QIcon.fromTheme("go-up"), "↑", lambda: self.term().find(self.find_edit.text()))
        self.findbar.addAction(QIcon.fromTheme("go-down"), "↓",
                               lambda: self.term().find(self.find_edit.text(), backwards=False))
        self.findbar.addAction(QIcon.fromTheme("window-close"), "×", self.close_find)
        self.addToolBar(Qt.BottomToolBarArea, self.findbar)
        self.findbar.hide()
        self._style()
        self.new_tab(command=command, workdir=workdir)

    def _style(self):
        c = scheme_colors(config.load().get("console", "scheme", fallback="credo"))
        pal = self.palette()
        pal.setColor(QPalette.Window, c["bg"])
        self.tabs.setStyleSheet(f"QTabWidget::pane {{ border:0; background:{c['bg'].name()}; }}"
                                f"QTabBar::tab {{ padding:5px 14px; min-width:110px; }}")

    def _menu(self):
        m = QMenu(self)
        m.addAction(QIcon.fromTheme("tab-new"), T("new_tab"), self.new_tab, QKeySequence("Ctrl+Shift+T"))
        m.addAction(QIcon.fromTheme("window-new"), T("new_window"), self.new_window, QKeySequence("Ctrl+Shift+N"))
        m.addSeparator()
        m.addAction(QIcon.fromTheme("edit-copy"), T("copy"), lambda: self.term().copy(), QKeySequence("Ctrl+Shift+C"))
        m.addAction(QIcon.fromTheme("edit-paste"), T("paste"), lambda: self.term().paste(), QKeySequence("Ctrl+Shift+V"))
        m.addAction(QIcon.fromTheme("edit-find"), T("find"), self.open_find, QKeySequence("Ctrl+Shift+F"))
        m.addSeparator()
        m.addAction(QIcon.fromTheme("zoom-in"), T("zoom_in"), lambda: self.term().zoom(1), QKeySequence("Ctrl++"))
        m.addAction(QIcon.fromTheme("zoom-out"), T("zoom_out"), lambda: self.term().zoom(-1), QKeySequence("Ctrl+-"))
        m.addAction(QIcon.fromTheme("zoom-original"), T("zoom_reset"), lambda: self.term().zoom(0),
                    QKeySequence("Ctrl+0"))
        schemes = m.addMenu(QIcon.fromTheme("color-management"), T("scheme"))
        la = config.language() == "la"
        for k, names in SCHEMES.items():
            schemes.addAction(names[1 if la else 0], lambda k=k: self.set_scheme(k))
        m.addSeparator()
        m.addAction(QIcon.fromTheme("edit-clear-history"), T("clear"), lambda: self.term().clear_scrollback(),
                    QKeySequence("Ctrl+Shift+K"))
        m.addAction(QIcon.fromTheme("view-refresh"), T("reset"), lambda: self.term().reset())
        m.addAction(QIcon.fromTheme("configure"), T("settings"), self.settings)
        m.addSeparator()
        m.addAction(QIcon.fromTheme("tab-close"), T("close_tab"), self.close_current, QKeySequence("Ctrl+Shift+W"))
        m.addAction(QIcon.fromTheme("application-exit"), T("quit"), self.close, QKeySequence("Ctrl+Shift+Q"))
        return m

    def term(self):
        return self.tabs.currentWidget()

    def new_tab(self, command=None, workdir=None):
        if workdir is None and self.term() is not None:
            workdir = self.term().cwd()
        t = Terminal(command if isinstance(command, str) else None, workdir)
        idx = self.tabs.addTab(t, os.path.basename(default_shell()))
        t.titleChanged.connect(lambda title, t=t: self._title(t, title))
        t.finished.connect(lambda t=t: self.close_tab(self.tabs.indexOf(t)))
        self.tabs.setCurrentIndex(idx)
        self.tabs.tabBar().setVisible(self.tabs.count() > 1)
        t.setFocus()
        return t

    def new_window(self):
        self.app.new_window(workdir=self.term().cwd() if self.term() else None)

    def _title(self, t, title):
        i = self.tabs.indexOf(t)
        short = title if len(title) < 32 else "…" + title[-30:]
        self.tabs.setTabText(i, short or os.path.basename(default_shell()))
        self.tabs.setTabToolTip(i, title)
        if t is self.term():
            self.setWindowTitle(f"{title} — Credo Console" if title else "Credo Console")

    def _tab_changed(self, _i):
        t = self.term()
        if t:
            t.setFocus()
            self._title(t, t.title)

    def cycle(self, d):
        if self.tabs.count():
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + d) % self.tabs.count())

    def close_tab(self, i):
        t = self.tabs.widget(i)
        if t is None:
            return
        t.close_process()
        self.tabs.removeTab(i)
        t.deleteLater()
        self.tabs.tabBar().setVisible(self.tabs.count() > 1)
        if self.tabs.count() == 0:
            self.close()

    def close_current(self):
        self.close_tab(self.tabs.currentIndex())

    def open_find(self):
        self.findbar.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def close_find(self):
        self.findbar.hide()
        if self.term():
            self.term().setFocus()

    def set_scheme(self, key):
        config.set_value("console", "scheme", key)
        for i in range(self.tabs.count()):
            self.tabs.widget(i).set_colors(key)
        self._style()

    def settings(self):
        if SettingsDialog(self).exec():
            cp = config.load()
            for i in range(self.tabs.count()):
                t = self.tabs.widget(i)
                t.font_family = cp.get("console", "font", fallback="")
                t.base_size = t.font_size = cp.getint("console", "size", fallback=11)
                t.set_colors(cp.get("console", "scheme", fallback="credo"))
                t._apply_font()
            self._style()

    def closeEvent(self, e):
        for i in range(self.tabs.count()):
            self.tabs.widget(i).close_process()
        if self in self.app.windows:
            self.app.windows.remove(self)
        super().closeEvent(e)


class ConsoleApp:
    def __init__(self):
        self.windows = []

    def new_window(self, command=None, workdir=None):
        w = ConsoleWindow(self, command, workdir)
        self.windows.append(w)
        w.show()
        return w


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    command, workdir = None, None
    if "--workdir" in argv:
        i = argv.index("--workdir")
        workdir = argv[i + 1] if i + 1 < len(argv) else None
        del argv[i:i + 2]
    if "-e" in argv:
        i = argv.index("-e")
        rest = argv[i + 1:]
        command = rest[0] if len(rest) == 1 else shlex.join(rest)
        del argv[i:]
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    qapp = QApplication(argv)
    qapp.setApplicationName("Credo Console")
    qapp.setDesktopFileName("credo-console")
    qapp.setWindowIcon(QIcon.fromTheme("credo-console"))
    app = ConsoleApp()
    app.new_window(command, workdir)
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
