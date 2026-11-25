"""Windows apps on Credo OS: the easiest working way to run a given Windows program.

Three routes, best first:
  * "linux"   the program (or a very close equivalent) exists for Linux: install that.
  * "bottles" ordinary Windows programs run through Wine, managed by Bottles: double-click the
              .exe/.msi installer and it is installed into a Windows "bottle".
  * "winboat" big professional software (SolidWorks, Adobe Creative Cloud, AutoCAD, full
              Microsoft 365...) needs real Windows. WinBoat runs Windows in a background virtual
              machine and shows its programs as normal windows on the Credo desktop. It needs a
              Windows licence; 3D is drawn without the graphics card, so very large models are slow.
"""
import re

# (Windows app names / aliases, route, target, note)
#   route "linux": target is "dnf:PKG", "flatpak:ID", "web:URL" or a command already installed
APPS = [
    (["SolidWorks", "SOLIDWORKS", "Solid Works"], "winboat", "",
     "Needs real Windows (Wine cannot run current versions). Install it inside WinBoat. "
     "Lighter alternatives: Onshape in the browser (made by SolidWorks' founders) or FreeCAD."),
    (["Onshape"], "linux", "web:https://cad.onshape.com", "Full CAD in the browser; free for hobby use"),
    (["FreeCAD"], "linux", "flatpak:org.freecad.FreeCAD", "Open-source parametric CAD (opens STEP files)"),
    (["AutoCAD", "Autodesk AutoCAD"], "winboat", "",
     "Needs real Windows: install it in WinBoat. Alternatives: DraftSight or LibreCAD"),
    (["Fusion 360", "Fusion", "Autodesk Fusion"], "winboat", "",
     "Best in WinBoat; community Wine scripts exist but break with updates"),
    (["Inventor", "Revit", "CATIA", "Creo", "NX", "Siemens NX", "ANSYS"], "winboat", "",
     "Professional CAD/CAE needs real Windows: install it in WinBoat"),
    (["KiCad"], "linux", "flatpak:org.kicad.KiCad", "Linux version"),
    (["Blender"], "linux", "flatpak:org.blender.Blender", "Linux version"),
    (["MATLAB"], "linux", "web:https://www.mathworks.com/downloads/", "Has an official Linux version"),
    (["Photoshop", "Adobe Photoshop", "Lightroom", "Premiere", "Adobe Premiere", "After Effects",
      "Illustrator", "Adobe Illustrator", "InDesign", "Creative Cloud", "Adobe"], "winboat", "",
     "Adobe Creative Cloud needs real Windows: install it in WinBoat. GIMP, Krita, Inkscape and "
     "Kdenlive are Linux alternatives"),
    (["Microsoft Office", "Office", "Microsoft 365", "Word", "Excel", "PowerPoint", "Outlook", "Access",
      "OneNote", "Visio", "Project"], "winboat", "",
     "Full desktop Office needs Windows (WinBoat). For most work: Office on the web in the browser, "
     "or LibreOffice (installed), which opens and saves Office files"),
    (["Notepad++", "7-Zip", "IrfanView", "Paint.NET", "foobar2000", "WinRAR", "PuTTY", "WinSCP",
      "HxD", "Everything"], "bottles", "", "Runs well in Bottles: open its installer (.exe)"),
    (["Steam", "game", "games", "Epic Games", "GOG", "Battle.net"], "linux", "flatpak:com.valvesoftware.Steam",
     "Most Windows games run through Steam's Proton; Heroic covers Epic and GOG"),
    (["Visual Studio"], "winboat", "", "Needs Windows (WinBoat). VS Code and JetBrains IDEs have Linux versions"),
    (["Visual Studio Code", "VS Code"], "linux", "flatpak:com.visualstudio.code", "Linux version"),
    (["Chrome", "Google Chrome"], "linux", "flatpak:com.google.Chrome", "Linux version"),
    (["Zoom"], "linux", "flatpak:us.zoom.Zoom", "Linux version"),
    (["Teams", "Microsoft Teams"], "linux", "web:https://teams.microsoft.com", "Works in the browser"),
    (["Spotify"], "linux", "flatpak:com.spotify.Client", "Linux version"),
    (["Discord"], "linux", "flatpak:com.discordapp.Discord", "Linux version"),
    (["Logos", "Verbum", "Logos Bible Software"], "bottles", "",
     "Logos/Verbum run in Bottles (or use app.verbum.com in the browser)"),
    (["eSword", "e-Sword", "theWord"], "bottles", "", "Runs in Bottles; Xiphos and BibleTime are installed"),
]

ROUTE_NOTE = {
    "bottles": "Bottles runs Windows programs through Wine: no Windows needed, starts instantly. "
               "Most everyday programs and many older ones work.",
    "winboat": "WinBoat runs real Windows in a background virtual machine and shows its programs as "
               "normal Credo windows. Everything that installs on Windows works there. You need a Windows "
               "licence and about 32 GB of free space; 3D is drawn without the graphics card, so very "
               "large CAD assemblies are slower than on a Windows PC.",
}


def normalize(name):
    name = re.sub(r"\.(exe|msi|zip)$", "", name.strip(), flags=re.I)
    name = re.sub(r"(setup|installer|install|x64|x86|win64|win32)", " ", name, flags=re.I)
    name = re.sub(r"[-_ ]?v?\d+(\.\d+)*", " ", name)                   # "SolidWorks2024 SP3" -> "solidworks"
    return re.sub(r"[^a-z0-9+]+", " ", name.lower()).strip()


def find(query):
    """Best matches for a Windows program name or an installer file name."""
    q = normalize(query)
    if not q:
        return []
    exact, partial = [], []
    for entry in APPS:
        names = [normalize(n) for n in entry[0]]
        if q in names:
            exact.append(entry)
        elif any(n and (q in n or n in q) for n in names if len(n) > 2):
            partial.append(entry)
    return exact + partial
