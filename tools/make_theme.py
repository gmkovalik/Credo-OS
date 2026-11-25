"""Generate the Credo desktop theme: icon theme, window decoration (Aurorae) and GTK theme.

Writes into overlay/usr/share/ (so the ISO includes it) and builds an installable package
dist/credo-theme/ (+ dist/credo-theme.tar.gz) for systems that are already running.

    python tools/make_theme.py
"""
import math
import pathlib
import re
import shutil
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHARE = ROOT / "overlay/usr/share"
sys.path.insert(0, str(ROOT / "overlay/usr/lib/credo"))
from credo import palettes  # noqa: E402

LOGOS = ROOT / "overlay/usr/share/credo/logos"
SANS = 'font-family="Inter, Noto Sans, DejaVu Sans, sans-serif"'
SERIF = 'font-family="Noto Serif, DejaVu Serif, Liberation Serif, serif"'


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def polar(cx, cy, r, deg):
    a = math.radians(deg - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)


# =========================================================================== icons
def _avg(a, b):
    """The colour halfway between two #rrggbb colours."""
    x, y = int(a[1:], 16), int(b[1:], 16)
    return "#%02x%02x%02x" % tuple(((x >> s & 255) + (y >> s & 255)) // 2 for s in (16, 8, 0))


def app_icon(name, top, bottom, glyph, extra_defs=""):
    """App icon: a flat rounded square in one colour (no gradients or shine), soft shadow."""
    flat = _avg(top, bottom)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <!-- Credo icon theme: {name} -->
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{flat}"/><stop offset="1" stop-color="{flat}"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#d9b44f"/><stop offset="1" stop-color="#d9b44f"/>
    </linearGradient>
    <linearGradient id="silver" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#eceef2"/><stop offset="1" stop-color="#eceef2"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.22"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    {extra_defs}
  </defs>
  <rect x="50" y="62" width="412" height="412" rx="94" fill="#000" fill-opacity="0.22"/>
  <rect x="50" y="46" width="412" height="412" rx="94" fill="url(#bg)"/>
  {glyph}
</svg>
"""


def cross(cx, cy, h, w, t, fill="url(#gold)"):
    """Latin cross centred on (cx, cy): height h, arm width w, thickness t; arms at 1/3 height."""
    top = cy - h / 2
    return (f'<rect x="{f(cx - t / 2)}" y="{f(top)}" width="{f(t)}" height="{f(h)}" rx="{f(t / 5)}" fill="{fill}"/>'
            f'<rect x="{f(cx - w / 2)}" y="{f(top + h * 0.28 - t / 2)}" width="{f(w)}" height="{f(t)}" '
            f'rx="{f(t / 5)}" fill="{fill}"/>')


def gear(cx, cy, r_out, r_in, teeth, fill):
    pts = []
    for i in range(teeth * 4):
        r = r_out if i % 4 in (1, 2) else r_in
        pts.append(polar(cx, cy, r, i * 360 / (teeth * 4)))
    return f'<path d="M{" L".join(f"{f(x)} {f(y)}" for x, y in pts)} Z" fill="{fill}"/>'


def glyphs():
    g = {}
    # --- Credo apps -------------------------------------------------------
    chi = (LOGOS / "chirho.svg").read_text(encoding="utf-8")
    inner = chi.split("<g fill=\"currentColor\">", 1)[1].rsplit("</g>", 1)[0].replace("currentColor", "url(#gold)")
    medal = (f'<g transform="translate(96 86) scale(0.625)"><circle cx="256" cy="256" r="236" fill="none" '
             f'stroke="url(#gold)" stroke-width="14"/><g fill="url(#gold)">{inner}</g></g>')
    g["credo"] = ("#3b342a", "#16130f", medal)

    g["credo-today"] = ("#3f8a4a", "#1d4d25", """
  <rect x="128" y="118" width="256" height="282" rx="30" fill="#fffdf6"/>
  <path d="M128 148 a30 30 0 0 1 30 -30 h196 a30 30 0 0 1 30 30 v42 h-256 Z" fill="#b3262e"/>
  <text x="256" y="174" text-anchor="middle" """ + SANS + """ font-size="40" font-weight="700" fill="#fff" letter-spacing="3">HODIE</text>
  """ + cross(256, 292, 150, 96, 24, "#2b2417") + """
  <circle cx="186" cy="118" r="10" fill="#7a1a20"/><circle cx="326" cy="118" r="10" fill="#7a1a20"/>""")

    g["credo-mass"] = ("#8e1d27", "#4a0b12", """
  <circle cx="256" cy="150" r="62" fill="#fffaf0"/>
  <circle cx="256" cy="150" r="62" fill="none" stroke="#d9cfb8" stroke-width="4"/>
  """ + cross(256, 150, 70, 46, 10, "#c9b98f") + """
  <path d="M156 232 h200 c0 70 -40 112 -82 122 v42 c0 14 30 18 52 30 h-140 c22 -12 52 -16 52 -30 v-42 c-42 -10 -82 -52 -82 -122 Z" fill="url(#gold)"/>
  <rect x="150" y="224" width="212" height="16" rx="8" fill="#f6dc86"/>
  <rect x="200" y="420" width="112" height="14" rx="7" fill="#b98f2c"/>""")

    beads = []
    for i in range(30):
        x, y = polar(256, 210, 116, i * 12)
        big = i % 10 == 0
        beads.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{13 if big else 9}" fill="url(#silver)"/>')
    tail = "".join(f'<circle cx="256" cy="{344 + k * 22}" r="9" fill="url(#silver)"/>' for k in range(2))
    g["credo-rosary"] = ("#3a6fc4", "#173a78", "".join(beads) + tail + cross(256, 414, 76, 50, 12))

    g["credo-prayers"] = ("#7a2730", "#3d1016", """
  <path d="M256 168 C214 140 160 136 112 146 V376 C160 366 214 370 256 396 Z" fill="#fbf3df"/>
  <path d="M256 168 C298 140 352 136 400 146 V376 C352 366 298 370 256 396 Z" fill="#fffaf0"/>
  <path d="M256 168 V396" stroke="#d6c7a3" stroke-width="4"/>
  """ + cross(184, 248, 96, 60, 14, "#b3262e") + """
  <g stroke="#b8ab8c" stroke-width="7" stroke-linecap="round">
    <path d="M292 206 H368"/><path d="M292 236 H368"/><path d="M292 266 H368"/><path d="M292 296 H368"/><path d="M292 326 H350"/>
  </g>
  <path d="M300 150 v170 l16 -14 l16 14 v-176" fill="#c9302c"/>""")

    g["credo-examen"] = ("#5b2a86", "#2b0f45", """
  <circle cx="256" cy="168" r="96" fill="#ffd36b" fill-opacity="0.18"/>
  <circle cx="256" cy="168" r="56" fill="#ffd36b" fill-opacity="0.22"/>
  <path d="M256 92 C288 140 290 170 274 192 C268 200 262 204 256 206 C250 204 244 200 238 192 C222 170 224 140 256 92 Z" fill="#ffb02e"/>
  <path d="M256 132 C272 160 270 178 262 190 C258 194 254 194 250 190 C242 178 240 160 256 132 Z" fill="#fff3b0"/>
  <rect x="252" y="200" width="8" height="18" fill="#3a2a1a"/>
  <rect x="210" y="214" width="92" height="196" rx="12" fill="url(#silver)"/>
  <path d="M210 232 q20 10 26 32 v20 q4 -26 -2 -50" fill="#e8e2d6"/>
  <rect x="176" y="404" width="160" height="20" rx="10" fill="url(#gold)"/>""")

    books = [("#7a1f2b", 150, 230), ("#1f4a7a", 196, 200), ("#2e5e2e", 236, 250), ("#6b4a1f", 282, 214),
             ("#3a2a5e", 326, 236)]
    shelf = "".join(f'<rect x="{x}" y="{402 - h}" width="40" height="{h}" rx="6" fill="{c}"/>'
                    f'<rect x="{x + 6}" y="{402 - h + 20}" width="28" height="6" fill="#e9c46a"/>'
                    f'<rect x="{x + 6}" y="{402 - h + 34}" width="28" height="4" fill="#e9c46a"/>'
                    for c, x, h in books)
    g["credo-library"] = ("#a8743e", "#5c3a17", shelf + cross(256, 300, 70, 44, 10) +
                          '<rect x="128" y="400" width="256" height="18" rx="6" fill="#3b240d"/>')

    g["credo-center"] = ("#5b5a57", "#262523",
                         gear(256, 252, 150, 122, 10, "url(#silver)") +
                         '<circle cx="256" cy="252" r="78" fill="#2f2d2a"/>' + cross(256, 252, 104, 66, 16))

    g["credo-browser"] = ("#2d5fa0", "#132c52", """
  <circle cx="256" cy="282" r="128" fill="none" stroke="url(#gold)" stroke-width="20"/>
  <path d="M128 282 H384 M256 154 V410" stroke="url(#gold)" stroke-width="18"/>
  <ellipse cx="256" cy="282" rx="62" ry="128" fill="none" stroke="#f6dc86" stroke-opacity="0.55" stroke-width="7"/>
  <path d="M146 222 H366 M146 342 H366" stroke="#f6dc86" stroke-opacity="0.55" stroke-width="7"/>
  """ + cross(256, 112, 96, 70, 20))

    g["credo-console"] = ("#2a2722", "#0f0e0c", """
  <rect x="96" y="96" width="320" height="300" rx="22" fill="#000" fill-opacity="0.35"/>
  <path d="M136 196 L212 252 L136 308" fill="none" stroke="#e8e0d0" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="236" y="290" width="128" height="28" rx="9" fill="#c9a85a"/>
  """ + cross(366, 142, 56, 38, 11))

    g["credo-bible"] = ("#26324f", "#0e1424", """
  <rect x="154" y="104" width="214" height="300" rx="14" fill="#e9e1cc"/>
  <rect x="142" y="96" width="210" height="300" rx="16" fill="#1b1b1f"/>
  <rect x="142" y="96" width="24" height="300" rx="10" fill="#0d0d10"/>
  """ + cross(258, 230, 150, 96, 22) + """
  <text x="258" y="356" text-anchor="middle" """ + SERIF + """ font-size="30" letter-spacing="4" fill="#d9b85a">BIBLIA</text>
  <path d="M300 396 v40 l12 -10 l12 10 v-40" fill="#b3262e"/>""")

    # Mac apps helper: a box arriving at a cross-marked home ("bring your Mac apps over")
    g["credo-macapps"] = ("#9aa3ad", "#4d5560", """
  <rect x="112" y="140" width="288" height="210" rx="34" fill="#f5f5f7"/>
  <rect x="112" y="140" width="288" height="210" rx="34" fill="none" stroke="#d0d3d9" stroke-width="6"/>
  <path d="M188 214 h40 M188 252 h70" stroke="#9aa3ad" stroke-width="16" stroke-linecap="round"/>
  <path d="M300 300 l40 -40 l-40 -40" fill="none" stroke="#3a6fc4" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>
  """ + cross(256, 400, 70, 48, 14))

    # Windows apps helper: a four-pane window on teal, with a small gold cross
    g["credo-winapps"] = ("#2f9e9a", "#17605e", """
  <rect x="120" y="128" width="272" height="236" rx="30" fill="#f5f7f7"/>
  <rect x="146" y="176" width="100" height="78" rx="8" fill="#3a86c4"/>
  <rect x="266" y="176" width="100" height="78" rx="8" fill="#3a86c4"/>
  <rect x="146" y="272" width="100" height="70" rx="8" fill="#3a86c4"/>
  <rect x="266" y="272" width="100" height="70" rx="8" fill="#3a86c4"/>
  <circle cx="152" cy="152" r="8" fill="#ff5f57"/><circle cx="176" cy="152" r="8" fill="#febc2e"/>
  <circle cx="200" cy="152" r="8" fill="#28c840"/>
  """ + cross(256, 410, 60, 42, 12))

    # FSSP app (prayer card, Cum Petro): the Fraternity's arms on a blue box: two crossed gold keys
    # (bits up, ornate bows down) and three white drops.
    gold = "#f2c41c"
    key = (f'<rect x="-9" y="-150" width="18" height="300" rx="6" fill="{gold}"/>'          # shaft
           f'<path d="M-9 -150 h-58 v22 h14 v16 h-14 v20 h58 Z" fill="{gold}"/>'              # bit (wards)
           f'<rect x="-20" y="108" width="40" height="14" rx="5" fill="{gold}"/>'             # collar
           f'<circle cx="0" cy="168" r="40" fill="none" stroke="{gold}" stroke-width="15"/>'  # bow
           f'<circle cx="-30" cy="196" r="12" fill="{gold}"/><circle cx="30" cy="196" r="12" fill="{gold}"/>'
           f'<circle cx="-40" cy="150" r="11" fill="{gold}"/><circle cx="40" cy="150" r="11" fill="{gold}"/>'
           f'<circle cx="0" cy="168" r="9" fill="{gold}"/>')
    drop = 'd="M0 -24 C9 -8 15 2 15 9 a15 15 0 0 1 -30 0 C-15 2 -9 -8 0 -24 Z" fill="#ffffff"'
    g["credo-fssp"] = ("#2235a6", "#2235a6", f"""
  <g transform="translate(256 226) rotate(-40)">{key}</g>
  <g transform="translate(256 226) scale(-1 1) rotate(-40)">{key}</g>
  <path transform="translate(146 246)" {drop}/>
  <path transform="translate(366 246)" {drop}/>
  <path transform="translate(256 408)" {drop}/>""")

    # --- common apps --------------------------------------------------------
    g["files"] = files_design(dark=True)

    sliders = ""
    for i, (x, knob) in enumerate(((176, 210), (256, 300), (336, 180))):
        sliders += (f'<rect x="{x - 7}" y="128" width="14" height="260" rx="7" fill="#9aa0aa"/>'
                    f'<circle cx="{x}" cy="{knob}" r="28" fill="url(#silver)"/>'
                    f'<circle cx="{x}" cy="{knob}" r="28" fill="none" stroke="#8a8f98" stroke-width="3"/>')
    g["settings"] = ("#8c9098", "#4a4e56", sliders)

    g["store"] = ("#2bb3a3", "#106e66", """
  <path d="M146 196 h220 l-18 210 h-184 Z" fill="#ffffff"/>
  <path d="M204 196 v-34 a52 52 0 0 1 104 0 v34" fill="none" stroke="#ffffff" stroke-width="18"/>
  <path d="M256 238 v108 M216 308 l40 40 l40 -40" fill="none" stroke="#14857a" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>""")

    g["editor"] = ("#f7e7b0", "#e0c26b", """
  <rect x="136" y="104" width="220" height="296" rx="14" fill="#fffdf6"/>
  <g stroke="#cbbf9f" stroke-width="8" stroke-linecap="round">
    <path d="M168 164 H322"/><path d="M168 200 H322"/><path d="M168 236 H300"/><path d="M168 272 H322"/><path d="M168 308 H280"/>
  </g>
  <path d="M398 118 C340 150 286 230 258 330 L274 336 C300 250 352 176 410 132 Z" fill="#3a2a1a"/>
  <path d="M258 330 l-8 34 l24 -28 Z" fill="#1b1b1f"/>""")

    g["reader"] = ("#e8553d", "#a4261a", """
  <path d="M142 104 h160 l70 70 v226 a14 14 0 0 1 -14 14 h-216 a14 14 0 0 1 -14 -14 v-282 a14 14 0 0 1 14 -14 Z" fill="#ffffff"/>
  <path d="M302 104 v56 a14 14 0 0 0 14 14 h56" fill="#e7e2da"/>
  <g stroke="#d4cfc6" stroke-width="8" stroke-linecap="round"><path d="M170 210 H330"/><path d="M170 246 H330"/><path d="M170 282 H290"/></g>
  <circle cx="300" cy="330" r="50" fill="none" stroke="#2b2b2b" stroke-width="16"/>
  <path d="M336 366 l44 44" stroke="#2b2b2b" stroke-width="22" stroke-linecap="round"/>""")

    g["photos"] = ("#5ab0f0", "#2770c2", """
  <rect x="110" y="132" width="292" height="232" rx="22" fill="#ffffff"/>
  <rect x="130" y="152" width="252" height="192" rx="10" fill="#bfe3ff"/>
  <circle cx="320" cy="200" r="24" fill="#ffd54f"/>
  <path d="M130 344 l76 -96 l56 66 l34 -40 l86 70 Z" fill="#3a8f4a"/>""")

    g["music"] = ("#ff5a6e", "#b5173a", """
  <path d="M206 140 l156 -36 v220" fill="none" stroke="#fff" stroke-width="22" stroke-linejoin="round"/>
  <path d="M206 140 v220" stroke="#fff" stroke-width="22"/>
  <ellipse cx="176" cy="362" rx="44" ry="34" fill="#fff"/><ellipse cx="332" cy="326" rx="44" ry="34" fill="#fff"/>
  <path d="M206 176 l156 -36" stroke="#fff" stroke-width="22"/>""")

    g["video"] = ("#5b3fa8", "#2a1660", """
  <rect x="112" y="150" width="288" height="210" rx="26" fill="#1b1430"/>
  <g fill="#ffffff" fill-opacity="0.6">""" + "".join(
        f'<rect x="{126 + k * 52}" y="160" width="30" height="16" rx="4"/>'
        f'<rect x="{126 + k * 52}" y="334" width="30" height="16" rx="4"/>' for k in range(6)) + """</g>
  <path d="M226 206 L318 256 L226 306 Z" fill="#ffffff"/>""")

    keys = "".join(f'<rect x="{150 + c * 56}" y="{232 + r * 46}" width="44" height="36" rx="9" '
                   f'fill="{"#ff9f0a" if c == 3 else "#5b5b5f"}"/>' for r in range(4) for c in range(4))
    g["calculator"] = ("#3a3a3c", "#1c1c1e", '<rect x="136" y="110" width="240" height="320" rx="26" fill="#101012"/>'
                      '<rect x="150" y="128" width="212" height="84" rx="12" fill="#d8e8c8"/>'
                      f'<text x="346" y="190" text-anchor="end" {SANS} font-size="46" fill="#1c2a14">MCMLIV</text>' + keys)

    g["screenshot"] = ("#4b6584", "#22324a", """
  <g fill="none" stroke="#ffffff" stroke-width="22" stroke-linecap="round">
    <path d="M128 196 V140 H184"/><path d="M328 140 H384 V196"/><path d="M384 316 V372 H328"/><path d="M184 372 H128 V316"/>
  </g>
  <circle cx="256" cy="256" r="56" fill="#ffffff"/><circle cx="256" cy="256" r="30" fill="#4b6584"/>""")

    g["archive"] = ("#c28a4a", "#7a4f1f", """
  <rect x="120" y="150" width="272" height="230" rx="16" fill="#e8c38f"/>
  <rect x="108" y="122" width="296" height="62" rx="14" fill="#f1d3a6"/>
  <rect x="246" y="122" width="20" height="258" fill="#8a5a24"/>
  <g fill="#f1d3a6">""" + "".join(f'<rect x="{240 if k % 2 else 258}" y="{196 + k * 24}" width="14" height="12"/>'
                                   for k in range(7)) + "</g>")

    g["monitor"] = ("#1f2a24", "#0a100c", """
  <rect x="104" y="128" width="304" height="236" rx="18" fill="#0d1a12" stroke="#2f4a38" stroke-width="4"/>
  <g stroke="#2f4a38" stroke-width="3"><path d="M104 188 H408 M104 248 H408 M104 308 H408"/></g>
  <path d="M120 320 L176 268 L220 296 L272 198 L320 246 L392 168" fill="none" stroke="#46e07a" stroke-width="14" stroke-linejoin="round" stroke-linecap="round"/>""")
    return g


# icon name -> design key
APP_NAMES = {
    "credo": ["credo", "start-here", "start-here-kde", "start-here-kde-plasma", "credo-os",
              # KDE / Plasma logos shown by the desktop (About, Welcome, menus): the Credo logo instead
              "kde", "plasma", "start-here-kde-symbolic", "start-here-kde-plasma-symbolic",
              "start-here-symbolic", "distributor-logo", "org.kde.plasma-welcome", "plasma-welcome"],
    "credo-today": ["credo-today", "credo-chirho"],
    "credo-mass": ["credo-mass", "credo-ihs"],
    "credo-rosary": ["credo-rosary", "credo-marian"],
    "credo-prayers": ["credo-prayers", "credo-cross"],
    "credo-examen": ["credo-examen", "credo-sacredheart"],
    "credo-library": ["credo-library", "credo-keys"],
    "credo-center": ["credo-center"],
    "launchpad": ["credo-launchpad", "launchpad"],
    "credo-macapps": ["credo-macapps"],
    "credo-winapps": ["credo-winapps", "com.usebottles.bottles", "wine", "winboat"],
    "credo-fssp": ["credo-fssp"],
    "credo-browser": ["credo-browser"],
    "credo-console": ["credo-console", "utilities-terminal", "org.kde.konsole", "konsole", "terminal"],
    "credo-bible": ["xiphos", "bibletime", "info.bibletime.BibleTime", "credo-bible"],
    "files": ["system-file-manager", "org.kde.dolphin", "dolphin", "file-manager"],
    "settings": ["preferences-system", "systemsettings", "org.kde.systemsettings", "preferences-desktop"],
    "store": ["org.kde.discover", "plasmadiscover", "system-software-install", "system-software-update"],
    "editor": ["accessories-text-editor", "org.kde.kate", "kate", "org.kde.kwrite", "kwrite", "text-editor"],
    "reader": ["org.kde.okular", "okular", "accessories-document-viewer", "document-viewer"],
    "photos": ["org.kde.gwenview", "gwenview", "image-viewer", "multimedia-photo-viewer"],
    "music": ["org.kde.elisa", "elisa", "multimedia-audio-player", "audio-player"],
    "video": ["org.kde.haruna", "haruna", "multimedia-video-player", "video-player", "mpv"],
    "calculator": ["accessories-calculator", "org.kde.kcalc", "kcalc", "calculator"],
    "screenshot": ["org.kde.spectacle", "spectacle", "applets-screenshooter", "screenshot"],
    "archive": ["org.kde.ark", "ark", "utilities-file-archiver", "file-roller"],
    "monitor": ["org.kde.plasma-systemmonitor", "utilities-system-monitor", "ksysguard", "system-monitor"],
}


def folder_icon(emblem=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="front" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#6fb8f4"/><stop offset="1" stop-color="#6fb8f4"/>
    </linearGradient>
  </defs>
  <path d="M40 120 a28 28 0 0 1 28 -28 h128 a28 28 0 0 1 22 10 l28 34 h198 a28 28 0 0 1 28 28 v40 h-432 Z" fill="#4a95e0"/>
  <rect x="40" y="168" width="432" height="282" rx="28" fill="url(#front)"/>
  <rect x="40" y="168" width="432" height="8" rx="4" fill="#ffffff" fill-opacity="0.45"/>
  {emblem}
</svg>
"""


E = 'fill="#3d86d4" fill-opacity="0.85"'
FOLDER_EMBLEMS = {
    "folder": "", "inode-directory": "", "folder-blue": "",
    "user-home": f'<path d="M256 236 l-86 70 h24 v74 h46 v-50 h32 v50 h46 v-74 h24 Z" {E}/>',
    "user-desktop": f'<rect x="176" y="250" width="160" height="104" rx="10" {E}/><rect x="236" y="354" width="40" height="18" {E}/>',
    "folder-documents": f'<path d="M206 240 h70 l36 36 v100 h-106 Z" {E}/>',
    "folder-download": f'<path d="M256 238 v96 M212 300 l44 44 l44 -44" fill="none" stroke="#3d86d4" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"/>',
    "folder-downloads": f'<path d="M256 238 v96 M212 300 l44 44 l44 -44" fill="none" stroke="#3d86d4" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"/>',
    "folder-music": f'<path d="M232 250 l70 -16 v96" fill="none" stroke="#3d86d4" stroke-width="16"/><path d="M232 250 v100" stroke="#3d86d4" stroke-width="16"/><ellipse cx="216" cy="352" rx="24" ry="18" {E}/><ellipse cx="286" cy="332" rx="24" ry="18" {E}/>',
    "folder-pictures": f'<path d="M180 366 l50 -70 l36 44 l24 -28 l46 54 Z" {E}/><circle cx="300" cy="266" r="16" {E}/>',
    "folder-videos": f'<path d="M224 252 L310 304 L224 356 Z" {E}/>',
    "folder-templates": f'<path d="M196 250 h120 v26 h-46 v96 h-28 v-96 h-46 Z" {E}/>',
    "folder-publicshare": f'<circle cx="226" cy="276" r="24" {E}/><circle cx="292" cy="276" r="24" {E}/><path d="M184 366 a42 42 0 0 1 84 0 Z M250 366 a42 42 0 0 1 84 0 Z" {E}/>',
}


def trash_icon(full):
    paper = ('<path d="M196 130 l30 -30 l40 24 l30 -20 l26 30 Z" fill="#fffdf6" stroke="#c9c2b2" stroke-width="4"/>'
             if full else "")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#e4e7ec"/><stop offset="1" stop-color="#e4e7ec"/>
  </linearGradient></defs>
  {paper}
  <path d="M128 142 h256 l-26 318 a20 20 0 0 1 -20 18 h-164 a20 20 0 0 1 -20 -18 Z" fill="url(#b)" stroke="#a9afb8" stroke-width="5"/>
  <rect x="112" y="122" width="288" height="30" rx="12" fill="#e9ecf0" stroke="#a9afb8" stroke-width="5"/>
  <g stroke="#b9bec6" stroke-width="9" stroke-linecap="round"><path d="M206 190 l8 236"/><path d="M256 190 v236"/><path d="M306 190 l-8 236"/></g>
  {cross(256, 300, 70, 44, 10, "#c9a227")}
</svg>
"""


def files_design(dark):
    """Files (Dolphin): the Credo logo (Chi-Rho in its ring) large on a folder face with a tab on top.
    Dark theme: black with a white logo; light theme: white with a dark logo."""
    ring = ROOT / "overlay/usr/share/credo/logos/chirho-ring.svg"
    bg, tab, face, ink = (("#141414", "#3a3a3a", "#232323", "#ffffff") if dark
                          else ("#f4f4f2", "#cfcfcb", "#e6e6e3", "#1a1a1a"))
    seal = ""
    if ring.exists():
        body = re.search(r"<svg[^>]*>(.*)</svg>", ring.read_text(encoding="utf-8"), re.S).group(1)
        body = re.sub(r"<!--.*?-->", "", body).replace("currentColor", ink)
        seal = f'<g transform="translate(124 120) scale(0.515625)">{body}</g>'      # 264 px, centred on the box
    return (bg, bg, "\n  " + seal)                     # just the box and the logo, no folder shape


def write_light_icons(dark_base, base):
    """Credo-Light: the Credo icons with light-mode versions where they differ (Files), over Breeze's
    light symbolic icons."""
    if base.exists():
        shutil.rmtree(base)
    shutil.copytree(dark_base, base)
    svg = app_icon("files", *files_design(dark=False))
    for n in APP_NAMES["files"]:
        (base / "scalable/apps" / f"{n}.svg").write_text(svg, encoding="utf-8")
    (base / "index.theme").write_text(index_theme("Credo Light", "breeze,hicolor"), encoding="utf-8")


def write_icons(base):
    apps = base / "scalable/apps"
    places = base / "scalable/places"
    mimes = base / "scalable/mimetypes"
    for d in (apps, places, mimes):
        d.mkdir(parents=True, exist_ok=True)
    designs = glyphs()
    designs["launchpad"] = LAUNCHPAD
    for key, names in APP_NAMES.items():
        top, bottom, glyph = designs[key]
        svg = app_icon(key, top, bottom, glyph)
        for n in names:
            (apps / f"{n}.svg").write_text(svg, encoding="utf-8")
    for name, emblem in FOLDER_EMBLEMS.items():
        target = mimes if name == "inode-directory" else places
        (target / f"{name}.svg").write_text(folder_icon(emblem), encoding="utf-8")
    (places / "user-trash.svg").write_text(trash_icon(False), encoding="utf-8")
    (places / "user-trash-full.svg").write_text(trash_icon(True), encoding="utf-8")
    (places / "start-here.svg").write_text(app_icon("credo", *designs["credo"]), encoding="utf-8")
    (base / "index.theme").write_text(index_theme("Credo", "breeze-dark,breeze,hicolor"), encoding="utf-8")
    return sum(1 for _ in base.rglob("*.svg"))


def index_theme(name, inherits):
    dirs = ["scalable/apps", "scalable/places", "scalable/mimetypes"]
    ctx = {"apps": "Applications", "places": "Places", "mimetypes": "MimeTypes"}
    out = [f"[Icon Theme]\nName={name}\nComment=Credo OS icons in the style of macOS, with Credo symbols\n"
           f"Inherits={inherits}\nExample=credo\nDirectories={','.join(dirs)}\n"]
    for d in dirs:
        out.append(f"[{d}]\nSize=64\nMinSize=8\nMaxSize=512\nType=Scalable\nContext={ctx[d.split('/')[1]]}\n")
    return "\n".join(out)


# =========================================================================== window decoration
def deco_theme(name, dark):
    """Aurorae theme: traffic-light buttons, rounded top corners, soft shadow drawn in the padding."""
    _, p = palettes.resolve("monastic" if dark else "ivory")
    # The title bar is the window's own colour (one unified glass sheet, as in the design).
    title_bg = p["bg"] if dark else "#efeae0"
    title_inactive = "#141c18" if dark else "#f6f2ea"
    border = "#34423a" if dark else "#cfc8ba"
    P, R = 16, 12                  # shadow padding, corner radius (Tahoe-like)
    RB = 10                        # bottom corner radius: drawn in a bottom strip below the content
    S = P + R + 2                  # corner piece size
    C = 100 - 2 * S                # centre size in the 100x100 canvas

    def stops(strength, inner=0.0):
        """Shadow fall-off as gradient stops; inner = offset where the window edge is."""
        out = []
        for k in range(7):
            t = k / 6                                  # 0 at the window edge, 1 at the outer edge
            a = strength * (1 - t) ** 2.4
            out.append(f'<stop offset="{inner + (1 - inner) * t:.4f}" stop-color="#000" stop-opacity="{a:.3f}"/>')
        return "".join(out)

    def pieces(prefix, bg, strength):
        """Frame pieces: a smooth gradient shadow in the padding, the title-bar colour, and a hairline
        border placed on the same half-pixel line along the straight edges and around the corners."""
        out, defs = [], []

        def group(id_, x, y, w, h, body):
            out.append(f'<g id="{prefix}-{id_}"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#000" '
                       f'fill-opacity="0"/>{body}</g>')

        def corner(id_, ox, oy, sx, sy, radius):
            gid = f"{prefix}-{id_}-shadow"
            x, y = min(ox, ox + sx * S), min(oy, oy + sy * S)
            ex, ey = ox + sx * P, oy + sy * P                       # window edge lines
            cx, cy = ex + sx * radius, ey + sy * radius            # centre of the corner arc
            ix, iy = ox + sx * S, oy + sy * S                      # inner edges of the piece
            # The shadow curves around the piece's inner corner so it meets the straight edge shadows
            # exactly (for square corners too); the window body itself is drawn on top.
            sr = radius if radius else S - P
            scx, scy = ex + sx * sr, ey + sy * sr
            defs.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{scx}" cy="{scy}" '
                        f'r="{sr + P}">{stops(strength, sr / (sr + P))}</radialGradient>')
            body = [f'<rect x="{x}" y="{y}" width="{S}" height="{S}" fill="url(#{gid})"/>']
            sweep = 1 if sx * sy > 0 else 0
            # Border and body are filled shapes (no strokes): Qt counts half a stroke in an element's
            # bounds, which made corner pieces 0.5 px larger than the edges and left visible seams.
            if radius:
                ri = radius - 1
                body.append(f'<path d="M{ex} {iy} V{cy} A{radius} {radius} 0 0 {sweep} {cx} {ey} H{ix} V{iy} Z" '
                            f'fill="{border}"/>')
                body.append(f'<path d="M{ex + sx} {iy} V{cy} A{ri} {ri} 0 0 {sweep} {cx} {ey + sy} H{ix} V{iy} Z" '
                            f'fill="{bg}"/>')
            else:
                x0, y0 = min(ex, ix), min(ey, iy)
                body.append(f'<rect x="{x0}" y="{y0}" width="{S - P}" height="{S - P}" fill="{border}"/>')
                body.append(f'<rect x="{x0 + (1 if sx > 0 else 0)}" y="{y0 + (1 if sy > 0 else 0)}" '
                            f'width="{S - P - 1}" height="{S - P - 1}" fill="{bg}"/>')
            group(id_, x, y, S, S, "".join(body))

        corner("topleft", 0, 0, 1, 1, R)
        corner("topright", 100, 0, -1, 1, R)
        corner("bottomleft", 0, 100, 1, -1, RB)
        corner("bottomright", 100, 100, -1, -1, RB)

        def edge(id_, x, y, w, h, axis, outward):
            gid = f"{prefix}-{id_}-shadow"
            if axis == "y":
                edge_pos = y + P if outward < 0 else y + h - P            # the window edge
                outer = y if outward < 0 else y + h
                defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{edge_pos}" '
                            f'x2="0" y2="{outer}">{stops(strength)}</linearGradient>')
                sy = y if outward < 0 else edge_pos
                body = [f'<rect x="{x}" y="{sy}" width="{w}" height="{P}" fill="url(#{gid})"/>']
                by = edge_pos if outward < 0 else y
                body.append(f'<rect x="{x}" y="{by}" width="{w}" height="{S - P}" fill="{bg}"/>')
                ly = edge_pos if outward < 0 else edge_pos - 1
                body.append(f'<rect x="{x}" y="{ly}" width="{w}" height="1" fill="{border}"/>')
            else:
                edge_pos = x + P if outward < 0 else x + w - P
                outer = x if outward < 0 else x + w
                defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{edge_pos}" y1="0" '
                            f'x2="{outer}" y2="0">{stops(strength)}</linearGradient>')
                sx_ = x if outward < 0 else edge_pos
                body = [f'<rect x="{sx_}" y="{y}" width="{P}" height="{h}" fill="url(#{gid})"/>']
                bx = edge_pos if outward < 0 else x
                body.append(f'<rect x="{bx}" y="{y}" width="{S - P}" height="{h}" fill="{bg}"/>')
                lx = edge_pos if outward < 0 else edge_pos - 1
                body.append(f'<rect x="{lx}" y="{y}" width="1" height="{h}" fill="{border}"/>')
            group(id_, x, y, w, h, "".join(body))

        edge("top", S, 0, C, S, "y", -1)
        edge("bottom", S, 100 - S, C, S, "y", 1)
        edge("left", 0, S, S, C, "x", -1)
        edge("right", 100 - S, S, S, C, "x", 1)
        out.append(f'<rect id="{prefix}-center" x="{S}" y="{S}" width="{C}" height="{C}" fill="{bg}"/>')
        return ["<defs>" + "".join(defs) + "</defs>"] + out

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">']
    svg += pieces("decoration", title_bg, 0.34)
    svg += pieces("decoration-inactive", title_inactive, 0.20)
    svg.append("</svg>")

    def button(color, edge_color, glyph):
        inactive = "#4a4640" if dark else "#d3cdc2"

        def state(id_, fill, stroke, mark, opacity=1):
            return (f'<g id="{id_}"><rect width="16" height="16" fill="#000" fill-opacity="0"/>'
                    f'<circle cx="8" cy="8" r="6.5" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" '
                    f'stroke-width="0.75"/>{mark}</g>')
        mark = f'<path d="{glyph}" fill="none" stroke="#4d0000" stroke-opacity="0.65" stroke-width="1.4" stroke-linecap="round"/>'
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
                + state("active-center", color, edge_color, "")
                + state("hover-center", color, edge_color, mark)
                + state("pressed-center", color, edge_color, mark, 0.75)
                + state("inactive-center", inactive, inactive, "")
                + state("deactivated-center", inactive, inactive, "", 0.5)
                + "</svg>")

    d = SHARE / "aurorae/themes" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "decoration.svg").write_text("\n".join(svg), encoding="utf-8")
    (d / "close.svg").write_text(button("#ff5f57", "#e0443e", "M5.5 5.5 L10.5 10.5 M10.5 5.5 L5.5 10.5"), encoding="utf-8")
    (d / "minimize.svg").write_text(button("#febc2e", "#dea123", "M4.8 8 H11.2"), encoding="utf-8")
    (d / "maximize.svg").write_text(button("#28c840", "#1aab29", "M8 4.8 V11.2 M4.8 8 H11.2"), encoding="utf-8")
    (d / "restore.svg").write_text(button("#28c840", "#1aab29", "M5.2 8 H10.8"), encoding="utf-8")
    for extra in ("alldesktops", "keepabove", "keepbelow", "shade", "help"):
        (d / f"{extra}.svg").write_text(button("#8e8a84", "#77736d", "M6 8 H10"), encoding="utf-8")
    fg = "232,224,208" if dark else "43,36,23"
    fg_in = "140,132,118" if dark else "140,132,118"
    (d / f"{name}rc").write_text(f"""[General]
ActiveTextColor={fg}
InactiveTextColor={fg_in}
TitleAlignment=Center
TitleVerticalAlignment=Center
Animation=150
Shadow=false
UseTextShadow=false
LeftButtons=XIA
RightButtons=

[Layout]
PaddingTop={P}
PaddingBottom={P}
PaddingLeft={P}
PaddingRight={P}
BorderLeft=1
BorderRight=1
BorderBottom={RB}
TitleEdgeTop=5
TitleEdgeBottom=5
TitleEdgeLeft=10
TitleEdgeRight=10
TitleEdgeTopMaximized=5
TitleEdgeBottomMaximized=5
TitleEdgeLeftMaximized=10
TitleEdgeRightMaximized=10
TitleBorderLeft=6
TitleBorderRight=6
TitleHeight=20
ButtonWidth=16
ButtonHeight=16
ButtonSpacing=6
ButtonMarginTop=2
ExplicitButtonSpacer=8
""", encoding="utf-8")
    pretty = name.replace("-", " ")
    (d / "metadata.desktop").write_text(f"""[Desktop Entry]
Name={pretty}
Comment=Credo OS window decoration with traffic-light buttons
X-KDE-PluginInfo-Author=Credo OS
X-KDE-PluginInfo-Name={name}
X-KDE-PluginInfo-Version=1.0
X-KDE-PluginInfo-License=CC-BY-SA-4.0
X-KDE-PluginInfo-EnabledByDefault=true
""", encoding="utf-8")


# =========================================================================== GTK
def gtk_theme(name, dark):
    _, p = palettes.resolve("monastic" if dark else "ivory")
    acc = p["accent"]
    base3 = "Adwaita/gtk-contained-dark.css" if dark else "Adwaita/gtk-contained.css"
    base4 = "Default/Default-dark.css" if dark else "Default/Default-light.css"
    colors = f"""
@define-color accent_color {acc};
@define-color accent_bg_color {acc};
@define-color accent_fg_color #ffffff;
@define-color theme_selected_bg_color {acc};
@define-color theme_selected_fg_color #ffffff;
@define-color window_bg_color {p['bg']};
@define-color window_fg_color {p['fg']};
@define-color theme_bg_color {p['bg']};
@define-color theme_fg_color {p['fg']};
@define-color theme_base_color {p['view']};
@define-color theme_text_color {p['fg']};
@define-color view_bg_color {p['view']};
@define-color view_fg_color {p['fg']};
@define-color headerbar_bg_color {p['bg_alt']};
@define-color headerbar_fg_color {p['fg']};
@define-color insensitive_fg_color {p['fg_dim']};
"""
    common = f"""
/* Credo: rounded, quiet, macOS-like details */
window, .background {{ background-color: {p['bg']}; color: {p['fg']}; }}
headerbar, .titlebar {{ background: {p['bg_alt']}; color: {p['fg']}; min-height: 38px; border: none;
  box-shadow: inset 0 -1px {p['bg_alt']}; }}
button {{ border-radius: 8px; }}
entry, spinbutton {{ border-radius: 8px; }}
selection, *:selected {{ background-color: {acc}; color: #ffffff; }}
scrollbar slider {{ border-radius: 99px; }}
/* traffic-light window buttons (client-side decorations: Firefox, GNOME apps) */
windowcontrols button, button.titlebutton {{ min-width: 14px; min-height: 14px; padding: 0; margin: 0 4px;
  border-radius: 99px; border: none; box-shadow: none; color: transparent; }}
windowcontrols button image, button.titlebutton image {{ opacity: 0; }}
windowcontrols button.close, button.titlebutton.close {{ background: #ff5f57; }}
windowcontrols button.minimize, button.titlebutton.minimize {{ background: #febc2e; }}
windowcontrols button.maximize, button.titlebutton.maximize {{ background: #28c840; }}
windowcontrols button:hover image, button.titlebutton:hover image {{ opacity: 0.6; color: #4d0000; }}
window:backdrop windowcontrols button, window:backdrop button.titlebutton {{ background: {p['fg_dim']}; }}
"""
    d = SHARE / "themes" / name
    for ver, base in (("gtk-3.0", base3), ("gtk-4.0", base4)):
        (d / ver).mkdir(parents=True, exist_ok=True)
        (d / ver / "gtk.css").write_text(
            f'@import url("resource:///org/gtk/libgtk/theme/{base}");\n{colors}{common}', encoding="utf-8")
    (d / "index.theme").write_text(f"""[Desktop Entry]
Type=X-GNOME-Metatheme
Name={name}
Comment=Credo OS GTK theme ({'dark' if dark else 'light'})
Encoding=UTF-8

[X-GNOME-Metatheme]
GtkTheme={name}
IconTheme=Credo
""", encoding="utf-8")


# =========================================================================== Plasma style (Liquid Glass)
def glass_frame(prefixes, radius, fill, border, highlight, size=100, margin=None, ox0=0):
    """A Plasma FrameSvg with rounded corners. prefixes: element prefixes ('' for none).
    Every element group carries an invisible rect that fixes its bounds (Qt SVG measures groups).
    margin: optional content margin (hint-*-margin elements) smaller than the corner radius.
    Returns the inner SVG markup when ox0 is given as part of a multi-frame file (see frames())."""
    r, S = radius, size
    C = S - 2 * r
    X = 0              # frames for different prefixes may overlap: Plasma draws each element by id

    def F(c):          # (hex, opacity) -> fill attributes; crisp edges avoid seams between pieces
        return f'fill="{c[0]}" fill-opacity="{c[1]}"'

    def S_(c):
        return f'stroke="{c[0]}" stroke-opacity="{c[1]}"'
    parts = []
    for pfx in prefixes:
        p = f"{pfx}-" if pfx else ""

        def g(name, x, y, w, h, body):
            parts.append(f'<g id="{p}{name}"><rect x="{x}" y="{y}" width="{w}" '
                         f'height="{h}" fill="#000" fill-opacity="0"/>{body}</g>')
        if margin is not None:
            for name, w_, h_ in (("hint-top-margin", 1, margin), ("hint-bottom-margin", 1, margin),
                                 ("hint-left-margin", margin, 1), ("hint-right-margin", margin, 1)):
                parts.append(f'<rect id="{p}{name}" x="{X}" y="{S + 10}" width="{w_}" height="{h_}" '
                             f'fill="#000" fill-opacity="0"/>')
        # corners: quarter discs plus a border arc (a top-edge highlight on the top corners)
        for name, ox, oy, sx, sy in (("topleft", 0, 0, 1, 1), ("topright", S, 0, -1, 1),
                                     ("bottomleft", 0, S, 1, -1), ("bottomright", S, S, -1, -1)):
            cx, cy = ox + sx * r, oy + sy * r
            a, b = (ox, cy), (cx, oy)
            sweep = 1 if sx * sy > 0 else 0
            line = highlight if sy > 0 else border
            ri = max(r - 1, 0)
            # fill + a 1 px ring as a filled shape (strokes would enlarge the element's bounds)
            body = (f'<path d="M{a[0]} {a[1]} A{r} {r} 0 0 {sweep} {b[0]} {b[1]} L{cx} {cy} Z" {F(fill)}/>'
                    f'<path d="M{a[0]} {a[1]} A{r} {r} 0 0 {sweep} {b[0]} {b[1]} L{b[0]} {b[1] + sy} '
                    f'A{ri} {ri} 0 0 {1 - sweep} {a[0] + sx} {a[1]} Z" {F(line)}/>')
            g(name, min(ox, cx), min(oy, cy), r, r, body)
        g("top", r, 0, C, r, f'<rect x="{r}" y="0" width="{C}" height="{r}" {F(fill)}/>'
                              f'<rect x="{r}" y="0" width="{C}" height="1" {F(highlight)}/>')
        g("bottom", r, S - r, C, r, f'<rect x="{r}" y="{S - r}" width="{C}" height="{r}" {F(fill)}/>'
                                    f'<rect x="{r}" y="{S - 1}" width="{C}" height="1" {F(border)}/>')
        g("left", 0, r, r, C, f'<rect x="0" y="{r}" width="{r}" height="{C}" {F(fill)}/>'
                              f'<rect x="0" y="{r}" width="1" height="{C}" {F(border)}/>')
        g("right", S - r, r, r, C, f'<rect x="{S - r}" y="{r}" width="{r}" height="{C}" {F(fill)}/>'
                                   f'<rect x="{S - 1}" y="{r}" width="1" height="{C}" {F(border)}/>')
        parts.append(f'<rect id="{p}center" x="{X + r}" y="{r}" width="{C}" height="{C}" {F(fill)} '
                     f'shape-rendering="crispEdges"/>')
    if ox0:
        return "\n".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S + 30}">\n' + "\n".join(parts)
            + "\n</svg>\n")


def frames(specs, size=100):
    """Several frames (each with its own radius/colours) in one SVG, side by side.
    specs: [(prefixes, radius, fill, border, highlight, margin)]"""
    body = []
    for i, (prefixes, radius, fill, border, highlight, margin) in enumerate(specs):
        body.append(glass_frame(prefixes, radius, fill, border, highlight, size, margin, ox0=1))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size + 30}">\n'
            + "\n".join(body) + "\n</svg>\n")


# KWin blurs/tints the area given by the panel's "mask-" elements. An empty mask means "the whole
# panel", which would tint a rectangle around the dock; so the dock's mask is one opaque pixel row
# at the very bottom (hidden under the pill) - effectively no blur, no tint.
def _mask(prefix, r):
    S, C = 100, 100 - 2 * r
    pieces = (("topleft", 0, 0, r, r), ("top", r, 0, C, r), ("topright", S - r, 0, r, r),
              ("left", 0, r, r, C), ("right", S - r, r, r, C), ("bottomleft", 0, S - r, r, r),
              ("bottom", r, S - r, C, r), ("bottomright", S - r, S - r, r, r))
    # Fully opaque: Plasma uses this mask as the panel's INPUT region too. (A mask that was only a
    # bottom pixel row made the dock ignore the pointer everywhere except under the icons.)
    # Corners are quarter discs, so the blur KWin draws behind the dock is a rounded pill, not a box.
    out = ""
    for n, x, y, w, h in pieces:
        if n in ("topleft", "topright", "bottomleft", "bottomright"):
            cx = x + w if "left" in n else x
            cy = y + h if "top" in n else y
            ax, ay = (x, cy) if "left" in n else (x + w, cy)
            bx, by = (cx, y) if "top" in n else (cx, y + h)
            sweep = 1 if n in ("topleft", "bottomright") else 0
            out += (f'<g id="mask-{prefix}{n}"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#000" '
                    f'fill-opacity="0"/><path d="M{ax} {ay} A{r} {r} 0 0 {sweep} {bx} {by} L{cx} {cy} Z" '
                    f'fill="#000"/></g>')
        else:
            out += f'<rect id="mask-{prefix}{n}" x="{x}" y="{y}" width="{w}" height="{h}" fill="#000"/>'
    return out + f'<rect id="mask-{prefix}center" x="{r}" y="{r}" width="{C}" height="{C}" fill="#000"/>\n'


DOCK_RADIUS = 26                     # = the glass pill's radius in the Credo Dock widget
DOCK_MASK = _mask("floating-", DOCK_RADIUS) + _mask("", 3)


def plasma_style(name="Credo"):
    """Plasma style: glass menu bar, popups, tooltips and desktop widgets. Anything not
    provided here falls back to Breeze. KWin blurs what is behind the translucent parts."""
    d = SHARE / "plasma/desktoptheme" / name
    (d / "widgets").mkdir(parents=True, exist_ok=True)
    (d / "dialogs").mkdir(parents=True, exist_ok=True)
    # Plasma draws a floating panel (the dock) from the "floating-" elements and an attached panel
    # (the menu bar) from the plain ones. Menu bar: almost clear, like Tahoe. Dock: a glass pill.
    (d / "widgets/panel-background.svg").write_text(frames([
        # Fully clear, like Tahoe's menu bar. (Plasma may also draw a floating dock with these plain
        # elements, so any tint here would show as a box around the dock.)
        (["", "translucent", "thick"], 3, ("#000000", 0.0), ("#ffffff", 0.0), ("#ffffff", 0.0), 2),   # clear: the top bar draws its own band (org.credo.menu)
        # the dock panel is transparent: the Credo Dock widget draws its own glass pill
        (["floating"], DOCK_RADIUS, ("#000000", 0.0), ("#000000", 0.0), ("#000000", 0.0), 0),
    ]).replace("</svg>", DOCK_MASK + "</svg>"), encoding="utf-8")
    # "solid" variant: used while a window is maximized (adaptive opacity) - darker bar, still clear dock
    (d / "solid/widgets").mkdir(parents=True, exist_ok=True)
    (d / "solid/widgets/panel-background.svg").write_text(frames([
        (["", "translucent", "thick"], 3, ("#000000", 0.0), ("#ffffff", 0.0), ("#ffffff", 0.0), 2),
        (["floating"], 8, ("#000000", 0.0), ("#000000", 0.0), ("#000000", 0.0), 0),
    ]), encoding="utf-8")
    # Popups (menus, calendar, tray): dark frosted glass.
    (d / "dialogs/background.svg").write_text(
        glass_frame([""], 16, ("#17211c", 0.92), ("#ffffff", 0.16), ("#ffffff", 0.34)),
        encoding="utf-8")
    # Desktop widgets and tooltips: lighter glass cards.
    (d / "widgets/background.svg").write_text(
        glass_frame([""], 22, ("#ffffff", 0.14), ("#ffffff", 0.22), ("#ffffff", 0.45)),
        encoding="utf-8")
    (d / "widgets/tooltip.svg").write_text(
        glass_frame([""], 10, ("#17211c", 0.82), ("#ffffff", 0.14), ("#ffffff", 0.28)),
        encoding="utf-8")
    (d / "metadata.json").write_text("""{
    "KPackageStructure": "Plasma/Theme",
    "KPlugin": {
        "Authors": [{ "Name": "Credo OS" }],
        "Description": "Liquid-glass panels and popups for Credo OS",
        "Id": "%s",
        "License": "CC-BY-SA-4.0",
        "Name": "Credo Glass",
        "Version": "1.0"
    },
    "X-Plasma-API-Minimum-Version": "6.0"
}
""" % name, encoding="utf-8")
    (d / "plasmarc").write_text("[ContrastEffect]\nenabled=false\n\n"
                                "[BlurBehindEffect]\nenabled=false\n\n[AdaptiveTransparency]\nenabled=false\n",
                                encoding="utf-8")


LAUNCHPAD = ("#f2f2f7", "#c3c3cf", "".join(
    f'<rect x="{126 + c * 92}" y="{120 + r * 92}" width="76" height="76" rx="20" fill="{col}"/>'
    for r, row in enumerate((("#ff5f57", "#febc2e", "#28c840"), ("#3a6fc4", "#c9a227", "#8e1d27"),
                             ("#5b2a86", "#2bb3a3", "#e8553d")))
    for c, col in enumerate(row)))


# =========================================================================== package
INSTALL = r"""#!/bin/sh
# Install the Credo desktop theme for this user (or system-wide with --system).
#   sh install.sh            install and apply (dark)
#   sh install.sh --light    install and apply the light variants
#   sh install.sh --system   install into /usr/share for every user (needs sudo)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
VARIANT=Credo
DEST="${XDG_DATA_HOME:-$HOME/.local/share}"
THEMES="$HOME/.themes"
for a in "$@"; do
  case "$a" in
    --light) VARIANT=Credo-Light ;;
    --system) DEST=/usr/share; THEMES=/usr/share/themes ;;
  esac
done
SUDO=""; [ "$DEST" = /usr/share ] && [ "$(id -u)" != 0 ] && SUDO=sudo

echo "Installing icons, window decoration and GTK theme into $DEST ..."
$SUDO mkdir -p "$DEST/icons" "$DEST/aurorae/themes" "$DEST/plasma/desktoptheme" "$THEMES"
$SUDO rm -rf "$DEST/plasma/desktoptheme/Credo"
$SUDO cp -r "$HERE/share/plasma/desktoptheme/Credo" "$DEST/plasma/desktoptheme/"
$SUDO rm -rf "$DEST/icons/Credo" "$DEST/icons/Credo-Light"
$SUDO cp -r "$HERE/share/icons/Credo" "$DEST/icons/"
# Credo-Light: the light-mode icons (e.g. a white Files icon) over Breeze's light symbolic icons
$SUDO cp -r "$HERE/share/icons/Credo-Light" "$DEST/icons/"
for t in Credo Credo-Light; do
  $SUDO rm -rf "$DEST/aurorae/themes/$t" "$THEMES/$t"
  $SUDO cp -r "$HERE/share/aurorae/themes/$t" "$DEST/aurorae/themes/"
  $SUDO cp -r "$HERE/share/themes/$t" "$THEMES/"
done
# App icons also go to hicolor, so Credo apps keep their icons under any icon theme.
$SUDO mkdir -p "$DEST/icons/hicolor/scalable/apps"
for f in "$HERE"/share/icons/Credo/scalable/apps/credo*.svg; do $SUDO cp "$f" "$DEST/icons/hicolor/scalable/apps/"; done
command -v gtk-update-icon-cache >/dev/null && $SUDO gtk-update-icon-cache -qf "$DEST/icons/hicolor" 2>/dev/null || true

echo "Applying $VARIANT ..."
KW=$(command -v kwriteconfig6 || command -v kwriteconfig5 || true)
if [ -n "$KW" ]; then
  $KW --file kdeglobals --group Icons --key Theme "$VARIANT"
  $KW --file kwinrc --group org.kde.kdecoration2 --key library org.kde.kwin.aurorae
  $KW --file kwinrc --group org.kde.kdecoration2 --key theme "__aurorae__svg__$VARIANT"
  $KW --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnLeft XIA
  $KW --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnRight ""
  # The theme's own borders: rounded bottom corners live in a thin bottom strip.
  $KW --file kwinrc --group org.kde.kdecoration2 --key BorderSize Normal
  $KW --file kwinrc --group org.kde.kdecoration2 --key BorderSizeAuto false
  $KW --file plasmarc --group Theme --key name Credo
  $KW --file plasmanotifyrc --group Notifications --key PopupPosition TopRight
fi
for v in 3.0 4.0; do
  mkdir -p "$HOME/.config/gtk-$v"
  INI="$HOME/.config/gtk-$v/settings.ini"
  [ -f "$INI" ] || printf '[Settings]\n' > "$INI"
  for kv in "gtk-theme-name=$VARIANT" "gtk-icon-theme-name=$VARIANT" "gtk-decoration-layout=close,minimize,maximize:"; do
    k=${kv%%=*}
    if grep -q "^$k=" "$INI"; then sed -i "s|^$k=.*|$kv|" "$INI"; else printf '%s\n' "$kv" >> "$INI"; fi
  done
done
if command -v gsettings >/dev/null; then
  gsettings set org.gnome.desktop.interface gtk-theme "$VARIANT" 2>/dev/null || true
  gsettings set org.gnome.desktop.interface icon-theme "$VARIANT" 2>/dev/null || true
  gsettings set org.gnome.desktop.wm.preferences button-layout "close,minimize,maximize:" 2>/dev/null || true
fi
# Apply now, without logging out.
command -v plasma-apply-desktoptheme >/dev/null && plasma-apply-desktoptheme Credo >/dev/null 2>&1 || true
[ -x /usr/libexec/plasma-changeicons ] && /usr/libexec/plasma-changeicons "$VARIANT" 2>/dev/null || true
# KWin keeps a decoration theme loaded (and its rendered SVG cached) until the theme changes, so
# switch to Breeze for a moment and back: open windows then pick up the new frame at once.
reconf() {
  # (qdbus6 is often not installed; dbus-send needs --type=method_call, or it only sends a signal)
  dbus-send --session --type=method_call --dest=org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null || true
}
rm -rf "$HOME/.cache/ksvg-elements"* "$HOME/.cache/aurorae"* 2>/dev/null || true
if [ -n "$KW" ]; then
  $KW --file kwinrc --group org.kde.kdecoration2 --key library org.kde.breeze
  $KW --file kwinrc --group org.kde.kdecoration2 --key theme Breeze
  reconf; sleep 1
  $KW --file kwinrc --group org.kde.kdecoration2 --key library org.kde.kwin.aurorae
  $KW --file kwinrc --group org.kde.kdecoration2 --key theme "__aurorae__svg__$VARIANT"
fi
reconf
echo "Done. Restart open apps to see the new icons everywhere."
"""


def package():
    dist = ROOT / "dist" / "credo-theme"
    if dist.exists():
        shutil.rmtree(dist)
    for rel in ("icons/Credo", "icons/Credo-Light", "aurorae/themes/Credo", "aurorae/themes/Credo-Light", "themes/Credo",
                "themes/Credo-Light", "plasma/desktoptheme/Credo"):
        shutil.copytree(SHARE / rel, dist / "share" / rel)
    (dist / "install.sh").write_bytes(INSTALL.encode("utf-8"))
    (dist / "README.txt").write_text(
        "Credo desktop theme: macOS-style icons with Credo symbols, traffic-light window buttons,\n"
        "and a matching GTK theme.\n\n  sh install.sh           dark\n  sh install.sh --light   light\n"
        "  sh install.sh --system  for every user (sudo)\n", encoding="utf-8")
    tgz = ROOT / "dist" / "credo-theme.tar.gz"
    with tarfile.open(tgz, "w:gz") as tar:
        tar.add(dist, arcname="credo-theme",
                filter=lambda ti: (setattr(ti, "mode", 0o755 if ti.name.endswith(".sh") or ti.isdir() else 0o644)
                                   or ti))
    return tgz


if __name__ == "__main__":
    n = write_icons(SHARE / "icons/Credo")
    write_light_icons(SHARE / "icons/Credo", SHARE / "icons/Credo-Light")
    deco_theme("Credo", True)
    deco_theme("Credo-Light", False)
    gtk_theme("Credo", True)
    gtk_theme("Credo-Light", False)
    plasma_style("Credo")
    tgz = package()
    print(f"icons: {n} files Â· decorations: Credo, Credo-Light Â· GTK: Credo, Credo-Light")
    print(f"package: {tgz} ({tgz.stat().st_size // 1024} KB)")
