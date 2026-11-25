"""Mac apps on Credo OS: find the Linux version or the closest equivalent of a Mac app.

macOS programs do not run on Linux directly. Darling (darlinghq.org) can run many macOS
command-line programs, but graphical Mac apps barely work yet; Credo offers it as an
experimental extra. For everything else, most popular Mac apps have a Linux version or a
good equivalent, listed here with a one-click install.
"""
import re

# kind: "installed" (command), "dnf" (package), "flatpak" (Flathub id), "web" (URL)
# (Mac app names / aliases, Linux app, kind, target, note)
APPS = [
    (["Safari"], "Credo Browser", "installed", "credo-browser", "Credo's own browser"),
    (["Google Chrome", "Chrome"], "Google Chrome", "flatpak", "com.google.Chrome", "The same browser, Linux version"),
    (["Firefox"], "Firefox", "installed", "firefox", "Already installed"),
    (["Microsoft Edge", "Edge"], "Microsoft Edge", "flatpak", "com.microsoft.Edge", "Linux version"),
    (["Brave"], "Brave", "flatpak", "com.brave.Browser", "Linux version"),
    (["Visual Studio Code", "VS Code", "VSCode", "Code"], "Visual Studio Code", "flatpak", "com.visualstudio.code",
     "Linux version"),
    (["Xcode"], "VS Code + Fedora developer tools", "flatpak", "com.visualstudio.code",
     "Xcode is Mac-only; for C, C++, Python, Rust or web work use VS Code"),
    (["Pages", "Microsoft Word", "Word"], "LibreOffice Writer", "installed", "libreoffice --writer",
     "Opens and saves Word files; already installed"),
    (["Numbers", "Microsoft Excel", "Excel"], "LibreOffice Calc", "installed", "libreoffice --calc",
     "Opens and saves Excel files; already installed"),
    (["Keynote", "Microsoft PowerPoint", "PowerPoint"], "LibreOffice Impress", "installed", "libreoffice --impress",
     "Opens and saves PowerPoint files; already installed"),
    (["Microsoft Office", "Office"], "ONLYOFFICE", "flatpak", "org.onlyoffice.desktopeditors",
     "Closest to Microsoft Office's look; LibreOffice is also installed"),
    (["Mail", "Microsoft Outlook", "Outlook", "Spark"], "Thunderbird", "installed", "thunderbird", "Already installed"),
    (["Calendar", "Fantastical"], "Thunderbird Calendar", "installed", "thunderbird", "Built into Thunderbird"),
    (["Notes", "TextEdit", "BBEdit", "Sublime Text"], "Kate", "installed", "kate", "Already installed"),
    (["Obsidian"], "Obsidian", "flatpak", "md.obsidian.Obsidian", "Linux version"),
    (["Notion"], "Notion (web)", "web", "https://www.notion.so", "Use it in the browser"),
    (["Evernote"], "Evernote (web)", "web", "https://www.evernote.com", "Use it in the browser"),
    (["Finder"], "Files", "installed", "dolphin", "Already installed"),
    (["Terminal", "iTerm", "iTerm2", "Warp"], "Credo Console", "installed", "credo-console", "Already installed"),
    (["Preview"], "Okular", "installed", "okular", "PDFs and images; already installed"),
    (["Photos", "Lightroom", "Adobe Lightroom"], "digiKam", "dnf", "digikam", "Photo library and editing"),
    (["Photoshop", "Adobe Photoshop", "Pixelmator", "Affinity Photo"], "GIMP", "installed", "gimp",
     "Already installed; Krita is another good choice"),
    (["Procreate", "Krita"], "Krita", "dnf", "krita", "Digital painting"),
    (["Illustrator", "Adobe Illustrator", "Affinity Designer", "Sketch"], "Inkscape", "installed", "inkscape",
     "Already installed"),
    (["Figma"], "Figma (web)", "web", "https://www.figma.com", "Works fully in the browser"),
    (["iMovie", "Final Cut Pro", "Final Cut", "Adobe Premiere", "Premiere"], "Kdenlive", "dnf", "kdenlive",
     "Video editing; DaVinci Resolve also has a Linux version"),
    (["GarageBand", "Logic Pro", "Logic"], "Ardour", "flatpak", "org.ardour.Ardour", "Recording studio"),
    (["Music", "iTunes"], "Elisa", "installed", "elisa", "Already installed"),
    (["Spotify"], "Spotify", "flatpak", "com.spotify.Client", "Linux version"),
    (["QuickTime", "QuickTime Player", "IINA"], "Haruna", "installed", "haruna", "Already installed"),
    (["VLC"], "VLC", "flatpak", "org.videolan.VLC", "Linux version"),
    (["OBS", "OBS Studio"], "OBS Studio", "flatpak", "com.obsproject.Studio", "Linux version"),
    (["HandBrake"], "HandBrake", "flatpak", "fr.handbrake.ghb", "Linux version"),
    (["Audacity"], "Audacity", "installed", "audacity", "Already installed"),
    (["MuseScore"], "MuseScore", "installed", "musescore", "Already installed"),
    (["Blender"], "Blender", "flatpak", "org.blender.Blender", "Linux version"),
    (["Zoom", "zoom.us"], "Zoom", "flatpak", "us.zoom.Zoom", "Linux version"),
    (["Microsoft Teams", "Teams"], "Microsoft Teams (web)", "web", "https://teams.microsoft.com", "Use it in the browser"),
    (["Slack"], "Slack", "flatpak", "com.slack.Slack", "Linux version"),
    (["Discord"], "Discord", "flatpak", "com.discordapp.Discord", "Linux version"),
    (["Telegram"], "Telegram", "flatpak", "org.telegram.desktop", "Linux version"),
    (["Signal"], "Signal", "flatpak", "org.signal.Signal", "Linux version"),
    (["WhatsApp"], "WhatsApp (web)", "web", "https://web.whatsapp.com", "Use it in the browser"),
    (["Messages", "FaceTime"], "KDE Connect / web apps", "installed", "kdeconnect-app",
     "Apple's own services are Mac/iPhone-only; KDE Connect links an Android phone"),
    (["Steam"], "Steam", "flatpak", "com.valvesoftware.Steam", "Linux version (many Windows games run through Proton)"),
    (["Kindle"], "Kindle Cloud Reader (web)", "web", "https://read.amazon.com", "Your Kindle books in the browser"),
    (["Books", "Apple Books"], "Foliate", "installed", "foliate", "EPUB reader; already installed"),
    (["Calibre"], "Calibre", "installed", "calibre", "Already installed"),
    (["1Password"], "1Password", "web", "https://1password.com/downloads/linux", "Has a Linux version (download page)"),
    (["Bitwarden"], "Bitwarden", "flatpak", "com.bitwarden.desktop", "Linux version"),
    (["Keychain Access"], "KeePassXC", "installed", "keepassxc", "Already installed"),
    (["Dropbox"], "Dropbox", "flatpak", "com.dropbox.Client", "Linux version"),
    (["Google Drive"], "Google Drive (web)", "web", "https://drive.google.com", "In the browser, or in Settings > Online Accounts"),
    (["The Unarchiver", "Archive Utility"], "Ark", "installed", "ark", "Already installed"),
    (["Anki"], "Anki", "flatpak", "net.ankiweb.Anki", "Linux version"),
    (["Zotero"], "Zotero", "flatpak", "org.zotero.Zotero", "Linux version"),
    (["Godot"], "Godot", "flatpak", "org.godotengine.Godot", "Linux version"),
    (["Unity", "Unity Hub"], "Unity Hub", "flatpak", "com.unity.UnityHub", "Linux version"),
    # Catholic apps
    (["Verbum", "Logos", "Logos Bible Software"], "Verbum (web) + Xiphos", "web", "https://app.verbum.com",
     "Verbum works in the browser; Xiphos and BibleTime are installed for offline study"),
    (["iBreviary", "Divine Office", "Universalis", "Breviary"], "Divinum Officium", "web",
     "https://www.divinumofficium.com", "The traditional Breviary (1954 and other rubrics)"),
    (["Laudate", "Hallow", "Rosary"], "Credo Prayers & Holy Rosary", "installed", "credo-library open /prayers",
     "Built into Credo"),
    (["Missal", "iMass", "Ordo"], "Mass of the Day", "installed", "credo-library open /mass",
     "1954 Missal, Latin and English, built into Credo"),
]


def normalize(name):
    name = re.sub(r"\.(app|dmg|pkg|zip)$", "", name.strip(), flags=re.I)
    name = re.sub(r"[-_]?\d+(\.\d+)*$", "", name)                 # "Zoom-5.17" -> "Zoom"
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def find(query):
    """Best matches for a Mac app name, a .app bundle or a .dmg file name."""
    q = normalize(query)
    if not q:
        return []
    exact, partial = [], []
    for entry in APPS:
        names = [normalize(n) for n in entry[0]]
        if q in names:
            exact.append(entry)
        elif any(q in n or n in q for n in names if len(n) > 2):
            partial.append(entry)
    return exact + partial


DARLING_NOTE = ("Darling runs macOS programs on Linux. Command-line programs work reasonably well; "
                "graphical Mac apps mostly do not yet. It is built from source (about an hour).")
