"""Plain, generic app names, as on a Mac ("Files", "Terminal", "Music"), instead of project names
("Dolphin", "Konsole", "Elisa").

For each known app, a copy of its .desktop launcher with the new name is written to
/usr/local/share/applications, which the desktop reads before /usr/share/applications. The original
files are untouched (package updates keep working); running this again refreshes the copies.

    sudo python3 -m credo.appnames            apply (needs root)
    sudo python3 -m credo.appnames --remove   go back to the original names
"""
import pathlib
import re
import sys

SRC = pathlib.Path("/usr/share/applications")
DEST = pathlib.Path("/usr/local/share/applications")
MARK = "X-Credo-Renamed=true"

# desktop file ids (first one found is used) -> (English name, Latin name)
NAMES = [
    (["org.kde.dolphin"], "Files", "Fasciculi"),
    (["org.kde.konsole"], "Terminal", "Terminale"),
    (["org.kde.kwrite"], "Text Editor", "Editor textuum"),
    (["org.kde.kate"], "Code Editor", "Editor codicis"),
    (["org.kde.gwenview"], "Photos", "Imagines"),
    (["org.kde.okular", "okularApplication_pdf"], "Document Viewer", "Lector documentorum"),
    (["org.kde.elisa"], "Music", "Musica"),
    (["org.kde.haruna"], "Videos", "Pelliculae"),
    (["org.kde.ark"], "Archives", "Archiva"),
    (["org.kde.kcalc"], "Calculator", "Calculatrum"),
    (["org.kde.spectacle"], "Screenshot", "Imago veli"),
    (["org.kde.discover"], "Software", "Programmata"),
    (["systemsettings", "kdesystemsettings"], "Settings", "Optiones"),
    (["org.kde.kinfocenter"], "System Information", "De systemate"),
    (["org.kde.plasma-systemmonitor"], "Activity Monitor", "Monitor actionum"),
    (["org.kde.filelight"], "Disk Usage", "Usus disci"),
    (["org.kde.kfind"], "Find Files", "Quaere fasciculos"),
    (["org.kde.kcharselect"], "Characters", "Characteres"),
    (["org.kde.kdeconnect.app"], "Phone Link", "Telephonum"),
    (["org.kde.kdeconnect.sms"], "Text Messages", "Nuntii breves"),
    (["org.kde.kleopatra"], "Keys & Certificates", "Claves et testimonia"),
    (["org.keepassxc.KeePassXC"], "Passwords", "Tesserae"),
    (["org.kde.kamoso"], "Camera", "Camera"),
    (["org.kde.k3b"], "Disc Burner", "Disci ardentes"),
    (["org.kde.partitionmanager"], "Disks", "Disci"),
    (["org.kde.kwalletmanager", "org.kde.kwalletmanager5"], "Wallet", "Crumena"),
    (["org.kde.krdc"], "Remote Desktop", "Mensa remota"),
    (["org.kde.krfb"], "Desktop Sharing", "Mensa communicata"),
    (["org.kde.ktorrent"], "Torrents", "Torrentes"),
    (["org.kde.kolourpaint"], "Paint", "Pictura"),
    (["org.kde.kaddressbook"], "Contacts", "Inscriptiones"),
    (["org.kde.drkonqi.coredump.gui"], "Crash Reports", "Relationes erratorum"),
    (["org.kde.plasma.emojier"], "Emoji", "Emoji"),
    (["org.kde.kdebugsettings"], "Debug Settings", "Optiones vestigandi"),
    (["org.kde.kmouth"], "Text to Speech", "Lectio vocalis"),
    (["org.kde.kgpg"], "Encryption", "Cryptographia"),
    (["org.kde.ksystemlog", "org.kde.kjournaldbrowser"], "System Log", "Acta systematis"),
    (["org.kde.krusader"], "Dual-Pane Files", "Fasciculi duplices"),
    (["org.kde.digikam"], "Photo Library", "Bibliotheca imaginum"),
    (["gimp", "org.gimp.GIMP"], "Image Editor", "Editor imaginum"),
    (["org.inkscape.Inkscape", "inkscape"], "Vector Drawing", "Delineatio"),
    (["calibre-gui"], "E-book Library", "Bibliotheca librorum"),
    (["com.github.johnfactotum.Foliate"], "Books", "Libri"),
    (["org.xiphos.Xiphos", "xiphos"], "Bible", "Biblia"),
    (["info.bibletime.BibleTime", "bibletime"], "Bible Study", "Studium Bibliorum"),
    (["io.github.xiaoyifang.goldendict_ng", "goldendict"], "Dictionary", "Lexicon"),
    (["com.github.xournalpp.xournalpp", "xournalpp"], "Handwritten Notes", "Notae manu scriptae"),
    (["org.zim_wiki.Zim", "zim"], "Notebook", "Commentarius"),
    (["org.musescore.MuseScore", "mscore", "musescore"], "Sheet Music", "Partitura"),
    (["org.audacityteam.Audacity", "audacity"], "Audio Editor", "Editor soni"),
    (["libreoffice-writer"], "Word Processor", "Scriptor"),
    (["libreoffice-calc"], "Spreadsheets", "Tabulae computandi"),
    (["libreoffice-impress"], "Presentations", "Praesentationes"),
    (["libreoffice-draw"], "Drawing", "Delineatio"),
    (["libreoffice-startcenter"], "Office", "Officina"),
    (["org.mozilla.Thunderbird", "mozilla-thunderbird", "thunderbird"], "Mail", "Epistulae"),
    (["btop"], "Resource Monitor", "Monitor opum"),
    (["htop"], "Process Viewer", "Processus"),
    (["org.kde.kmenuedit"], "Menu Editor", "Editor indicis"),
    (["org.gnome.SimpleScan", "org.kde.skanpage"], "Scanner", "Scrutator"),
]


def rename(text, en, la):
    """The launcher with Name (and Name[la]) set to the generic name; other translations dropped."""
    out = []
    section = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            section = s
        if section == "[Desktop Entry]" and re.match(r"Name(\[[^\]]+\])?=", s):
            continue
        out.append(line)
        if s == "[Desktop Entry]":
            out += [f"Name={en}", f"Name[la]={la}", MARK]
    return "\n".join(out) + "\n"


# KDE apps replaced by Credo's own (still installed, just not shown in menus).
HIDE = ["org.kde.plasma-welcome"]


def apply():
    DEST.mkdir(parents=True, exist_ok=True)
    done = []
    for i in HIDE:
        src = SRC / f"{i}.desktop"
        if src.is_file():
            text = re.sub(r"^NoDisplay=.*\n?", "", src.read_text(encoding="utf-8"), flags=re.M)
            text = text.replace("[Desktop Entry]\n", f"[Desktop Entry]\nNoDisplay=true\n{MARK}\n", 1)
            (DEST / src.name).write_text(text, encoding="utf-8")
            done.append(f"{i} hidden")
    for ids, en, la in NAMES:
        for i in ids:
            src = SRC / f"{i}.desktop"
            if src.is_file():
                (DEST / src.name).write_text(rename(src.read_text(encoding="utf-8"), en, la), encoding="utf-8")
                done.append(f"{i} -> {en}")
                break
    return done


def remove():
    for f in DEST.glob("*.desktop"):
        if MARK in f.read_text(encoding="utf-8", errors="replace"):
            f.unlink()


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove()
    else:
        for line in apply():
            print(line)
