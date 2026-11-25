"""Build Latin (la) catalogs for the most visible parts of KDE Plasma.

KDE has no Latin translation. This writes tools/latin/<domain>.po with the strings below,
matched exactly against the source strings of Fedora's own catalogs, and compiles them to
overlay/usr/share/locale/la/LC_MESSAGES/<domain>.mo. Strings not listed stay in English.

    python3 tools/make_latin.py DIR_WITH_ITALIAN_PO_FILES     (needs msgfmt; run on Fedora/WSL)

The Italian .po files only supply the exact source strings (msgctxt + msgid); see
tools/fetch_kde_strings.sh.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_PO = ROOT / "tools/latin"
OUT_MO = ROOT / "overlay/usr/share/locale/la/LC_MESSAGES"

# English -> Latin, per catalog. Keys are msgids (any context); "&" marks the keyboard accelerator.
COMMON_ACTIONS = {
    "&File": "&Fasciculus", "&Edit": "&Emendatio", "&View": "&Aspectus", "&Go": "&Iter", "&Bookmarks": "&Signacula",
    "&Tools": "&Instrumenta", "&Settings": "&Optiones", "&Help": "&Auxilium", "&Game": "&Ludus",
    "&New": "&Novum", "&Open…": "&Aperi…", "Open &Recent": "&Recentia", "&Save": "&Serva", "Save &As…": "Serva &ut…",
    "Re&vert": "Re&stitue", "&Close": "&Claude", "&Print…": "&Imprime…", "Print Previe&w": "Praevisio &impressionis",
    "&Mail…": "&Epistula…", "&Quit": "E&xi", "&Undo": "&Revoca", "Re&do": "&Iterum fac", "Cu&t": "Ex&cide",
    "&Copy": "Ex&scribe", "&Paste": "&Insere", "Select &All": "Selige &omnia", "Dese&lect": "&Deselige",
    "&Find…": "&Quaere…", "Find &Next": "Quaere &sequens", "Find Pre&vious": "Quaere &priorem",
    "&Replace…": "&Substitue…", "&Delete": "&Dele", "&Move to Trash": "&Move in quisquilias",
    "&Rename…": "&Renomina…", "C&lear": "&Purga", "Clear List": "Purga indicem", "&Back": "&Retro",
    "&Forward": "&Porro", "&Up": "&Sursum", "&Home": "&Domus", "&Refresh": "&Renova", "Zoom &In": "&Amplifica",
    "Zoom &Out": "&Minue", "Zoom to &Actual Size": "Magnitudo &vera", "&Zoom…": "&Magnitudo…",
    "&Fit to Page": "Ad paginam &apta", "Fit to Page &Width": "Ad latitudinem paginae",
    "Fit to Page &Height": "Ad altitudinem paginae", "&First Page": "&Prima pagina", "&Last Page": "&Ultima pagina",
    "&Next Page": "Pagina &sequens", "&Previous Page": "Pagina &prior", "&Go To…": "&I ad…",
    "&Go to Line…": "I ad &lineam…", "&Go to Page…": "I ad &paginam…", "&Add Bookmark": "&Adde signaculum",
    "&Edit Bookmarks…": "&Muta signacula…", "&Spelling…": "&Orthographia…", "F&ull Screen Mode": "&Plena visio",
    "Show &Menubar": "Ostende taeniam &indicis", "Show &Toolbar": "Ostende taeniam &instrumentorum",
    "Show St&atusbar": "Ostende taeniam &status", "Configure Tool&bars…": "Configura taenias &instrumentorum…",
    "Configure &Notifications…": "Configura &nuntia…", "Configure &Language…": "Configura &linguam…",
    "&Configure %1…": "&Configura %1…", "%1 &Handbook": "&Enchiridion %1", "What's &This?": "&Quid est hoc?",
    "&Report Bug…": "&Refer vitium…", "&Donate": "&Dona", "&About %1": "&De %1", "About &KDE": "De &KDE",
    "Open &Menu": "Aperi &indicem", "&Menu": "&Index", "More": "Plura", "More Actions": "Plures actiones",
    "Color Scheme": "Colores", "Default": "Solitum", "Configure": "Configura", "Undo": "Revoca", "Redo": "Iterum fac",
    "Undo last action": "Revoca ultimam actionem", "Redo last undone action": "Iterum fac actionem revocatam",
    "Quit application": "Exi ex applicatione", "Create new document": "Crea novum documentum",
    "Open an existing document": "Aperi documentum", "Save document": "Serva documentum",
    "Print document": "Imprime documentum", "Close document": "Claude documentum",
    "Paste clipboard content": "Insere contentum", "Go up": "Sursum", "No Entries": "Nihil",
    "Main Toolbar": "Taenia principalis", "Configure Toolbars": "Configura taenias", "Shortcuts": "Compendia",
    "Shortcut": "Compendium", "Action": "Actio", "Description": "Descriptio", "Filter": "Cola", "Reset": "Restitue",
    "Remove": "Remove", "Delete": "Dele", "Clear": "Purga", "Copy to Clipboard": "Exscribe", "Global": "Universale",
    "Top": "Supra", "Bottom": "Infra", "Left": "Sinistra", "Right": "Dextra", "Text Only": "Textus tantum",
    "Icons Only": "Icones tantum", "Text Alongside Icons": "Textus iuxta icones",
    "Text Under Icons": "Textus sub iconibus", "Icon Size": "Magnitudo iconum", "Text Position": "Locus textus",
    "Lock Toolbar Positions": "Fige taenias", "About": "De", "Author": "Auctor", "Thanks To": "Gratias",
    "Translation": "Translatio", "Version %1": "Versio %1", "Version:": "Versio:", "None": "Nihil",
    "Toolbars Shown": "Taeniae ostensae", "Configure Language": "Configura linguam",
    "Primary language:": "Lingua prima:", "Fallback language:": "Lingua subsidiaria:",
    "Add Fallback Language": "Adde linguam subsidiariam", "Find Action…": "Quaere actionem…",
    "Shortcuts for %1": "Compendia pro %1", "Name for new scheme:": "Nomen novi schematis:",
}

KICKOFF = {
    "Applications": "Applicationes", "Places": "Loca", "Computer": "Computatrum", "History": "Historia",
    "Frequently Used": "Saepe adhibita", "Add to Favorites": "Adde ad dilecta", "Remove from Favorites":
    "Remove a dilectis", "Show in Favorites": "Ostende in dilectis", "Session": "Sessio", "Power": "Potentia",
    "Session and Power": "Sessio et potentia", "Power and session": "Potentia et sessio", "More": "Plura",
    "Edit Applications…": "Muta applicationes…", "No matches": "Nihil inventum", "New!": "Novum!",
    "Keep Open": "Tene apertum", "Newly-installed application": "Applicatio nuper instituta",
    "There is a newly-installed application in this category": "Applicatio nuper instituta in hac categoria est",
    "On All Activities": "In omnibus actionibus", "On the Current Activity": "In actione praesenti",
    "General": "Generalia", "General:": "Generalia:", "Left": "Sinistra", "Right": "Dextra", "Icon:": "Icon:",
    "Choose…": "Elige…", "Reset to default icon": "Restitue iconem solitam", "Remove icon": "Remove iconem",
    "Sort applications alphabetically": "Ordina applicationes litteris",
    "Show applications as:": "Ostende applicationes ut:", "Name only": "Nomen tantum",
    "Description only": "Descriptio tantum", "Name (Description)": "Nomen (Descriptio)",
    "Description (Name)": "Descriptio (Nomen)", "In a grid": "In craticula", "In a list": "In indice",
    "Show favorites:": "Ostende dilecta:", "Show other applications:": "Ostende alias applicationes:",
    "Show buttons for:": "Ostende globulos pro:", "Sidebar position:": "Locus taeniae lateralis:",
}

CLOCK = {
    "Calendar": "Calendarium", "Today": "Hodie", "Days": "Dies", "Months": "Menses", "Years": "Anni",
    "Previous Month": "Mensis prior", "Next Month": "Mensis sequens", "Previous Year": "Annus prior",
    "Next Year": "Annus sequens", "Copy to Clipboard": "Exscribe", "Adjust Date and Time…": "Dies et hora…",
    "Set Time Format…": "Forma horae…", "Time Zones": "Zonae horariae", "Appearance": "Species",
    "Show date": "Ostende diem", "Show seconds": "Ostende secunda", "Show week numbers": "Ostende numeros hebdomadum",
    "Font:": "Typus litterarum:", "Date format:": "Forma diei:", "Long Date": "Dies longus",
    "Short Date": "Dies brevis", "ISO Date": "Dies ISO", "Custom": "Proprium", "Holidays": "Feriae",
}

TASKS = {
    "Pin to Task Manager": "Fige in navali", "Unpin from Task Manager": "Solve a navali",
    "Close": "Claude", "Close All": "Claude omnia", "Minimize": "Minue", "Maximize": "Maximiza",
    "Move": "Move", "Resize": "Magnitudinem muta", "More": "Plura", "Start New Instance": "Novum exemplum incipe",
    "Recent Files": "Fasciculi recentes", "Places": "Loca", "Actions": "Actiones",
    "Keep Above Others": "Tene supra alias", "Keep Below Others": "Tene infra alias", "Fullscreen": "Plena visio",
    "Shade": "Contrahe", "Move to &Desktop": "Move ad &mensam", "All Desktops": "Omnes mensae",
    "&All Desktops": "&Omnes mensae", "New Desktop": "Nova mensa", "Show in &Activities": "Ostende in &actionibus",
    "Forget Recent Files": "Obliviscere fasciculos recentes", "Show Audio Channels": "Ostende canales soni",
    "Mute": "Tace", "Unmute": "Sonum redde",
}

TRAY = {
    "Status and Notifications": "Status et nuntia", "Show hidden icons": "Ostende icones occultas",
    "Hide icons": "Occulta icones", "Back": "Retro", "Configure System Tray…": "Configura arcam systematis…",
    "Entries": "Elementa", "General": "Generalia", "Always shown": "Semper ostensum",
    "Shown when relevant": "Ostensum cum opus est", "Hidden": "Occultum", "Disabled": "Inactivum",
}

DOLPHIN = {
    "Places": "Loca", "Folders": "Plicae", "Information": "Notitiae", "Terminal": "Terminale",
    "Create New": "Crea novum", "Folder…": "Plica…", "New Window": "Nova fenestra", "New Tab": "Nova tabula",
    "Close Tab": "Claude tabulam", "Show Hidden Files": "Ostende fasciculos occultos",
    "Hidden Files": "Fasciculi occulti", "Split": "Divide", "Close": "Claude", "Name": "Nomen", "Size": "Magnitudo",
    "Modified": "Mutatum", "Type": "Genus", "Icons": "Icones", "Compact": "Compactum", "Details": "Singula",
    "Sort By": "Ordina secundum", "View Mode": "Modus aspectus", "Filter…": "Cola…", "Search…": "Quaere…",
    "Search": "Quaere", "Properties": "Proprietates", "Open in New Tab": "Aperi in nova tabula",
    "Open in New Window": "Aperi in nova fenestra", "Copy Location": "Exscribe locum",
    "Move to Trash": "Move in quisquilias", "Delete": "Dele", "Empty Trash": "Exhauri quisquilias",
    "Invert Selection": "Inverte selectionem", "Show Panels": "Ostende tabulas laterales",
    "Location Bar": "Taenia loci", "Editable Location": "Locus mutabilis", "Open With": "Aperi cum",
    "Other Application…": "Alia applicatio…", "Copy To": "Exscribe ad", "Move To": "Move ad",
    "Duplicate Here": "Duplica hic", "Sort Folders First": "Plicas primum ordina", "Ascending": "Ascendens",
    "Descending": "Descendens", "Preview": "Praevisio", "Show Previews": "Ostende praevisiones",
    "Free space: %1": "Spatium liberum: %1", "Configure Dolphin…": "Configura Dolphin…",
    "Recently Saved": "Nuper servata", "Recent Files": "Fasciculi recentes", "Recent Locations": "Loca recentia",
    "Remote": "Remota", "Devices": "Instrumenta", "Removable Devices": "Instrumenta removibilia",
    "Trash": "Quisquiliae", "Home": "Domus", "Desktop": "Mensa", "Documents": "Documenta",
    "Downloads": "Depositiones", "Music": "Musica", "Pictures": "Imagines", "Videos": "Pelliculae",
    "Network": "Rete", "Root": "Radix", "Undo": "Revoca", "Paste": "Insere", "Copy": "Exscribe", "Cut": "Excide",
    "Rename…": "Renomina…", "Select All": "Selige omnia", "Reload": "Renova", "Stop": "Siste", "Up": "Sursum",
    "Back": "Retro", "Forward": "Porro", "Zoom In": "Amplifica", "Zoom Out": "Minue", "Open Terminal": "Aperi terminale",
    "Open Terminal Here": "Aperi terminale hic", "Add to Places": "Adde ad loca",
    "Remove from Places": "Remove a locis", "Edit…": "Muta…", "Hide": "Occulta", "Show All Entries":
    "Ostende omnia", "Folder is empty": "Plica vacua est", "No items": "Nihil",
}

DOMAINS = {
    "kconfigwidgets6": COMMON_ACTIONS, "kxmlgui6": COMMON_ACTIONS,
    "plasma_applet_org.kde.plasma.kickoff": KICKOFF, "plasma_applet_org.kde.plasma.digitalclock": CLOCK,
    "plasma_applet_org.kde.plasma.taskmanager": TASKS, "plasma_applet_org.kde.plasma.systemtray": TRAY,
    "dolphin": DOLPHIN,
}

ENTRY = re.compile(r'(?:msgctxt ((?:"(?:[^"\\]|\\.)*"\n)+))?msgid ((?:"(?:[^"\\]|\\.)*"\n)+)'
                   r'(msgid_plural (?:"(?:[^"\\]|\\.)*"\n)+)?msgstr', re.M)


def unquote(block):
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', block or "")
    return "".join(parts).encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")


def quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def build(src_dir):
    OUT_PO.mkdir(parents=True, exist_ok=True)
    OUT_MO.mkdir(parents=True, exist_ok=True)
    report = []
    for domain, table in DOMAINS.items():
        src = pathlib.Path(src_dir) / f"{domain}.it.po"
        if not src.exists():
            report.append(f"{domain}: source strings missing, skipped")
            continue
        text = src.read_text(encoding="utf-8")
        out = ['msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', '"Language: la\\n"',
               '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"', ""]
        n, seen = 0, set()
        for m in ENTRY.finditer(text):
            ctx_b, mid_b, plural = m.groups()
            if plural:
                continue
            mid = unquote(mid_b)
            ctx = unquote(ctx_b) if ctx_b else None
            latin = table.get(mid)
            if not mid or latin is None or (ctx, mid) in seen:
                continue
            seen.add((ctx, mid))
            if ctx is not None:
                out.append(f"msgctxt {quote(ctx)}")
            out += [f"msgid {quote(mid)}", f"msgstr {quote(latin)}", ""]
            n += 1
        po = OUT_PO / f"{domain}.po"
        po.write_text("\n".join(out), encoding="utf-8")
        subprocess.run(["msgfmt", "-o", str(OUT_MO / f"{domain}.mo"), str(po)], check=True)
        report.append(f"{domain}: {n} strings in Latin")
    return report


if __name__ == "__main__":
    for line in build(sys.argv[1]):
        print(line)
