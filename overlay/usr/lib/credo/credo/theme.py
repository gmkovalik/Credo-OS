"""Credo OS theme engine.

Generates KDE color schemes, wallpapers, colored logos, the panel layout, the boot
splash and the login-screen background from a variant + logo choice.

User:   credo-theme [--variant V] [--logo L] [--panel-position P] [--panel-height N]
                    [--floating yes|no] [--login] [--list]
Root:   python3 -m credo.theme --system-default
        python3 -m credo.theme --system-boot LOGO VARIANT
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

from . import config, liturgy, palettes

WALL_W, WALL_H = 2880, 1800          # X1 Carbon Gen 11 2.8K OLED; scales cleanly to 1920x1200
SYSTEM_WALLPAPER = pathlib.Path("/usr/share/wallpapers/Credo/contents/images/2880x1800.png")
PLYMOUTH_DIR = pathlib.Path("/usr/share/plymouth/themes/credo")
SDDM_USER_CONF = pathlib.Path("/usr/share/sddm/themes/breeze/theme.conf.user")
SPLASH_LOGO = pathlib.Path("/usr/share/credo/theme/splash-logo.svg")


# ---------------------------------------------------------------- helpers
def _rgb(hexcolor):
    h = hexcolor.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def _mix(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    out = [round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (0, 2, 4)]
    return "#" + "".join(f"{v:02x}" for v in out)


def _run(cmd, check=False):
    if shutil.which(cmd[0]) is None:
        return None
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def logo_svg(logo, color):
    path = config.SHARE / "logos" / f"{logo}.svg"
    if not path.exists():
        path = config.SHARE / "logos" / "chirho.svg"
    return path.read_text(encoding="utf-8").replace("currentColor", color)


def svg_to_png(svg_text, out_png, width, height):
    out_png = pathlib.Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_png.with_suffix(".svg")
    tmp.write_text(svg_text, encoding="utf-8")
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-w", str(width), "-h", str(height),
                        "-o", str(out_png), str(tmp)], check=True)
        tmp.unlink()
        return out_png
    return tmp  # fall back to the SVG itself (Plasma can display SVG wallpapers)


# ---------------------------------------------------------------- color scheme
def color_scheme(name, p):
    acc, bg, alt, view, fg, dim = p["accent"], p["bg"], p["bg_alt"], p["view"], p["fg"], p["fg_dim"]
    neg, neu, pos = "#c0392b", "#d68910", "#27ae60"
    link = _mix(acc, fg, 0.15)
    visited = _mix(acc, "#7b1fa2", 0.5)
    hover = _mix(acc, "#ffffff", 0.25)

    def block(section, back, back_alt, fore, inactive=dim):
        return (f"[Colors:{section}]\n"
                f"BackgroundAlternate={_rgb(back_alt)}\nBackgroundNormal={_rgb(back)}\n"
                f"DecorationFocus={_rgb(acc)}\nDecorationHover={_rgb(hover)}\n"
                f"ForegroundActive={_rgb(acc)}\nForegroundInactive={_rgb(inactive)}\n"
                f"ForegroundLink={_rgb(link)}\nForegroundNegative={_rgb(neg)}\n"
                f"ForegroundNeutral={_rgb(neu)}\nForegroundNormal={_rgb(fore)}\n"
                f"ForegroundPositive={_rgb(pos)}\nForegroundVisited={_rgb(visited)}\n\n")

    # Dark: toolbars share the window colour, so title bar + toolbar read as one glass sheet.
    header = bg if p["dark"] else _mix(bg, acc, 0.10)
    comp_bg = _mix(bg, "#000000", 0.35) if p["dark"] else _mix(bg, acc, 0.06)
    text = (block("Button", _mix(bg, fg, 0.06), _mix(bg, fg, 0.10), fg)
            + block("Complementary", comp_bg, _mix(comp_bg, fg, 0.06), fg)
            + block("Header", header, _mix(header, fg, 0.05), fg)
            + block("Header][Inactive", bg, alt, fg)
            + block("Selection", acc, _mix(acc, "#000000", 0.15), p["accent_fg"], _mix(p["accent_fg"], acc, 0.4))
            + block("Tooltip", _mix(bg, fg, 0.04), alt, fg)
            + block("View", view, _mix(view, acc, 0.05), fg)
            + block("Window", bg, alt, fg))
    text += (f"[General]\nColorScheme=Credo{name}\nName=Credo {name}\n"
             f"shadeSortColumn=true\nAccentColor={_rgb(acc)}\n\n"
             f"[KDE]\ncontrast=4\n\n"
             f"[WM]\nactiveBackground={_rgb(header)}\nactiveBlend={_rgb(fg)}\n"
             f"activeForeground={_rgb(fg)}\ninactiveBackground={_rgb(bg)}\n"
             f"inactiveBlend={_rgb(dim)}\ninactiveForeground={_rgb(dim)}\n")
    return text


def write_scheme(name, pal, directory):
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"Credo{name}.colors"
    path.write_text(color_scheme(name, pal), encoding="utf-8")
    return path


# ---------------------------------------------------------------- wallpaper
def wallpaper_svg(pal, logo, motto=True, w=WALL_W, h=WALL_H):
    """Liquid wallpaper (macOS 26 style): soft colour fields of the season, a glowing logo.
    Only gradients are used, so Qt SVG (Credo Center's preview) draws it like librsvg does."""
    uid = hashlib.sha1(f"{pal}{logo}{w}".encode()).hexdigest()[:6]
    cx, cy = w / 2, h * 0.46
    size = h * 0.30
    light = _mix(pal["wall_a"], "#ffffff", 0.18)
    warm = _mix(pal["logo"], pal["wall_a"], 0.45)
    deep = _mix(pal["wall_b"], "#000000", 0.25)
    # (gradient id, centre x, centre y, radius x, radius y, colour, opacity) as fractions of the screen
    fields = [("a", 0.80, 0.05, 0.62, 0.48, light, 0.85), ("b", 0.08, 0.92, 0.60, 0.50, pal["wall_a"], 0.9),
              ("c", 0.50, 0.58, 0.42, 0.30, warm, 0.40), ("d", 0.18, 0.18, 0.40, 0.32, deep, 0.7),
              ("e", 0.95, 0.85, 0.35, 0.30, light, 0.35)]
    field_defs = "".join(
        f'<radialGradient id="f{k}{uid}" cx="{x * w:.0f}" cy="{y * h:.0f}" r="{rx * w:.0f}" '
        f'gradientUnits="userSpaceOnUse" gradientTransform="translate({x * w:.0f} {y * h:.0f}) '
        f'scale(1 {ry * h / (rx * w):.3f}) translate({-x * w:.0f} {-y * h:.0f})">'
        f'<stop offset="0" stop-color="{c}" stop-opacity="{o}"/>'
        f'<stop offset="0.55" stop-color="{c}" stop-opacity="{o * 0.45:.2f}"/>'
        f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>'
        for k, x, y, rx, ry, c, o in fields)
    rays = [f'<rect width="{w}" height="{h}" fill="url(#f{k}{uid})"/>' for k, *_ in fields]
    # Inline the logo as a scaled group: Qt SVG (Credo Center's preview) skips nested <svg>.
    inner = logo_svg(logo, pal["logo"])
    inner = re.sub(r"<\?xml[^>]*>", "", inner)
    inner = re.sub(r"<svg\b[^>]*>", "", inner, count=1).replace("</svg>", "")
    scale = size / 512
    inner = (f'<g transform="translate({cx - size / 2:.1f} {cy - size / 2:.1f}) scale({scale:.4f})">'
             f'{inner}</g>')
    motto_text = ""
    if motto and pal.get("motto"):
        esc = pal["motto"].upper().replace("&", "&amp;").replace("<", "&lt;")
        motto_text = (f'<text x="{cx}" y="{cy + size * 0.82}" text-anchor="middle" '
                      f'font-family="Noto Serif, DejaVu Serif, Liberation Serif, Times New Roman, serif" '
                      f'font-size="{h * 0.032:.0f}" '
                      f'letter-spacing="{h * 0.008:.0f}" fill="{pal["logo"]}" fill-opacity="0.85">{esc}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <radialGradient id="bg{uid}" cx="50%" cy="46%" r="75%">
      <stop offset="0" stop-color="{pal['wall_a']}"/>
      <stop offset="1" stop-color="{pal['wall_b']}"/>
    </radialGradient>
    <radialGradient id="glow{uid}" cx="50%" cy="46%" r="22%">
      <stop offset="0" stop-color="{pal['logo']}" stop-opacity="0.16"/>
      <stop offset="1" stop-color="{pal['logo']}" stop-opacity="0"/>
    </radialGradient>
    {field_defs}
  </defs>
  <rect width="{w}" height="{h}" fill="url(#bg{uid})"/>
  {''.join(rays)}
  <rect width="{w}" height="{h}" fill="url(#glow{uid})"/>
  <g opacity="0.2">{inner}</g>
  {motto_text}
</svg>"""


# ---------------------------------------------------------------- Plasma
def plasma_script(js):
    """Run a Plasma desktop script in the running plasmashell."""
    return _run(["gdbus", "call", "--session", "--dest", "org.kde.plasmashell",
                 "--object-path", "/PlasmaShell", "--method",
                 "org.kde.PlasmaShell.evaluateScript", js])


LAYOUTS = {
    # key: (English, Latin)
    "mac": ("Menu bar and dock (like macOS)", "Taenia superior et navale"),
    "classic": ("Single taskbar", "Taenia una"),
}

# Same order as the approved design (design/credo-desktop-mockup.html)
DOCK_LAUNCHERS = ["applications:org.kde.dolphin.desktop", "applications:credo-launchpad.desktop",
                  "applications:credo-browser.desktop", "applications:credo-today.desktop",
                  "applications:credo-mass.desktop", "applications:credo-rosary.desktop",
                  "applications:credo-prayers.desktop", "applications:credo-library.desktop",
                  "applications:xiphos.desktop", "applications:org.kde.elisa.desktop",
                  "applications:org.kde.gwenview.desktop", "applications:credo-console.desktop",
                  "applications:credo-center.desktop"]

# The dock: a transparent floating panel holding the Credo Dock widget (glass pill + magnification),
# tall enough for icons to grow upwards.
DOCK_JS = """
var dock = new Panel; dock.location = "bottom";
dock.height = 80;
try {{ dock.floating = true; }} catch (e) {{}}
try {{ dock.lengthMode = "fit"; }} catch (e) {{}}
try {{ dock.alignment = "center"; }} catch (e) {{}}
var t = dock.addWidget("org.credo.dock"); t.currentConfigGroup = ["General"];
t.writeConfig("launchers", {launcher_array});
"""

_MENU_TYPES = '["org.kde.plasma.kickoff", "org.kde.plasma.kicker", "org.kde.plasma.kickerdash"]'


def build_js(layout, icon_path, position, height, floating):
    """Remove every panel and create the chosen layout from scratch."""
    icon = json.dumps(str(icon_path))
    launchers = json.dumps(",".join(DOCK_LAUNCHERS))
    js = "var old = panels(); for (var i = 0; i < old.length; i++) old[i].remove();\n"
    if layout == "mac":
        # Menu bar (almost clear) + floating glass dock: the Plasma style draws the bar from the
        # plain panel elements and the dock from the "floating-" ones.
        js += f"""
var bar = new Panel; bar.location = "top"; bar.height = 32;
try {{ bar.floating = false; }} catch (e) {{}}
try {{ bar.opacity = "translucent"; }} catch (e) {{}}
bar.addWidget("org.credo.menu"); bar.addWidget("org.credo.appname");
bar.addWidget("org.kde.plasma.appmenu"); bar.addWidget("org.kde.plasma.panelspacer");
bar.addWidget("org.credo.liturgicalday"); bar.addWidget("org.kde.plasma.systemtray");
var c = bar.addWidget("org.kde.plasma.digitalclock"); c.currentConfigGroup = ["Appearance"];
c.writeConfig("showDate", "true"); c.writeConfig("dateFormat", "custom");
c.writeConfig("customDateFormat", "ddd d MMM"); c.writeConfig("dateDisplayFormat", 1);
// The date and time in the menu font (Inter, menu size), like macOS, not Plasma's large auto size.
c.writeConfig("autoFontAndSize", "false"); c.writeConfig("fontFamily", "Inter");
c.writeConfig("fontSize", 10); c.writeConfig("fontWeight", 500); c.writeConfig("boldText", "false");
var ds = desktops();
if (ds.length) {{
  // (re)place the Today and Rosary widgets at the bottom left, as in the design
  var d0 = ds[0], ws0 = d0.widgets();
  for (var j = 0; j < ws0.length; j++)
    if (["org.credo.today", "org.credo.rosary", "org.credo.clock"].indexOf(ws0[j].type) >= 0) ws0[j].remove();
  var sg = screenGeometry(d0.screen), wy = sg.height - 330;
  var place = [["org.credo.today", 40, 300], ["org.credo.rosary", 372, 170], ["org.credo.clock", 590, 170]];
  for (var k = 0; k < place.length; k++) {{
    var w = d0.addWidget(place[k][0], place[k][1], wy, place[k][2], 170);
    try {{ w.geometry = new QRectF(place[k][1], wy, place[k][2], 170); }} catch (e) {{}}
  }}
}}
""" + DOCK_JS.format(launcher_array=json.dumps(DOCK_LAUNCHERS))
        return js + adjust_js(layout, icon_path, position, height, floating)
    else:
        js += f"""
var p = new Panel;
var m = p.addWidget("org.kde.plasma.kickoff"); m.currentConfigGroup = ["General"]; m.writeConfig("icon", {icon});
var t = p.addWidget("org.kde.plasma.icontasks"); t.currentConfigGroup = ["General"];
t.writeConfig("launchers", {launchers});
p.addWidget("org.kde.plasma.marginsseparator"); p.addWidget("org.credo.liturgicalday");
p.addWidget("org.kde.plasma.systemtray"); p.addWidget("org.kde.plasma.digitalclock");
p.addWidget("org.kde.plasma.showdesktop");
"""
    return js + adjust_js(layout, icon_path, position, height, floating)


def adjust_js(layout, icon_path, position, height, floating):
    """Update the dock/taskbar and the menu icon without touching the user's widgets.
    A panel holding the global menu (appmenu) is the menu bar and stays at the top."""
    if layout == "mac" and position == "top":
        position = "bottom"                 # the menu bar owns the top edge
    length = "fit" if layout == "mac" else "fill"
    icon_size = int(height)
    if layout == "mac":
        # In the mac layout "height" is the dock's icon size; the panel must also hold the
        # magnified icon (x1.45) and the glass pill's padding.
        icon_size = max(36, min(int(height), 96))
        height = icon_size + 20      # just the glass pill: no room for magnification (off by default)
    return f"""
var ps = panels();
for (var i = 0; i < ps.length; i++) {{
  var p = ps[i], ws = p.widgets(), isBar = false;
  for (var j = 0; j < ws.length; j++) if (ws[j].type == "org.kde.plasma.appmenu") isBar = true;
  for (var j = 0; j < ws.length; j++) {{
    if ({_MENU_TYPES}.indexOf(ws[j].type) >= 0) {{
      ws[j].currentConfigGroup = ["General"];
      ws[j].writeConfig("icon", {json.dumps(str(icon_path))});
      ws[j].reloadConfig();
    }}
  }}
  if (isBar) continue;
  for (var j = 0; j < ws.length; j++) {{
    if (ws[j].type == "org.credo.dock") {{
      ws[j].currentConfigGroup = ["General"];
      ws[j].writeConfig("iconSize", {icon_size});
      ws[j].reloadConfig();
    }}
  }}
  p.location = {json.dumps(position)};
  p.height = {int(height)};
  try {{ p.floating = {str(bool(floating)).lower()}; }} catch (e) {{}}
  try {{ p.lengthMode = {json.dumps(length)}; }} catch (e) {{}}
  try {{ p.alignment = "center"; }} catch (e) {{}}
}}
"""


def wait_for_plasma(timeout=90):
    """At login, plasmashell may not be on the session bus yet; scripts sent too early are lost."""
    import time
    end = time.time() + timeout
    while time.time() < end:
        r = _run(["gdbus", "call", "--session", "--dest", "org.freedesktop.DBus",
                  "--object-path", "/org/freedesktop/DBus", "--method",
                  "org.freedesktop.DBus.NameHasOwner", "org.kde.plasmashell"])
        if r is None:
            return False
        if "true" in (r.stdout or ""):
            time.sleep(2)               # let it finish loading the desktop containments
            return True
        time.sleep(1)
    return False


def current_settings():
    cp = config.load()
    a = cp["appearance"]
    return dict(variant=a.get("variant"), logo=a.get("logo"), layout=a.get("layout", "mac"),
                panel_position=a.get("panel_position"), panel_height=a.getint("panel_height"),
                panel_floating=a.getboolean("panel_floating"), wallpaper=a.getboolean("wallpaper"),
                motto=a.getboolean("motto"))


def apply_user(quiet=False):
    """Apply the current user's Credo theme to the running Plasma session."""
    s = current_settings()
    day = liturgy.today()
    name, pal = palettes.resolve(s["variant"], day)
    data = config.DATA_DIR / "theme"
    schemes = pathlib.Path(os.environ.get("XDG_DATA_HOME") or config.HOME / ".local/share") / "color-schemes"
    write_scheme(name, pal, schemes)

    # "v2": the liquid wallpaper design; bump when the artwork changes so caches are redrawn
    key = hashlib.sha1(f"v4{name}{s['logo']}{s['motto']}{pal['motto']}".encode()).hexdigest()[:10]
    icon = data / f"logo-{s['logo']}-{key}.svg"
    icon.parent.mkdir(parents=True, exist_ok=True)
    for old in data.glob(f"logo-*.svg"):
        if old != icon:
            old.unlink(missing_ok=True)
    icon.write_text(logo_svg(s["logo"], pal["logo"]), encoding="utf-8")

    # plasma-apply-colorscheme ignores a scheme that is already set, even when its colours changed;
    # apply another one first so the new colours always reach the open apps.
    _run(["plasma-apply-colorscheme", "BreezeDark" if pal["dark"] else "BreezeLight"])
    _run(["plasma-apply-colorscheme", f"Credo{name}"])
    if s["wallpaper"]:
        wp = data / f"wallpaper-{key}.png"
        if not wp.exists():
            for old in data.glob("wallpaper-*"):
                old.unlink(missing_ok=True)
            wp = svg_to_png(wallpaper_svg(pal, s["logo"], s["motto"]), wp, WALL_W, WALL_H)
        _run(["plasma-apply-wallpaperimage", str(wp)])
    # The look-and-feel package lays out the "mac" desktop, so a fresh account counts as "mac".
    applied = config.load().get("appearance", "applied_layout", fallback="mac")
    if os.environ.get("CREDO_REBUILD_PANELS"):        # credo-update: new dock launchers
        applied = ""
    args = (s["layout"], icon, s["panel_position"], s["panel_height"], s["panel_floating"])
    plasma_script(build_js(*args) if s["layout"] != applied else adjust_js(*args))
    config.set_value("appearance", "applied_layout", s["layout"])
    try:
        from . import dock
        dock.stop_crystal_dock()
    except Exception:
        pass
    config.set_value("appearance", "applied_scheme", f"Credo{name}")
    if not quiet:
        print(f"Applied Credo {name} with the {s['logo']} logo.")
    return name


# ---------------------------------------------------------------- system (root)
def system_default():
    """Called from the kickstart %post: install all schemes and the default artwork."""
    for v in palettes.STATIC:
        name, pal = palettes.resolve(v)
        write_scheme(name, pal, "/usr/share/color-schemes")
    for c, pal in palettes.LITURGICAL.items():
        write_scheme(f"Liturgical{c.capitalize()}", pal, "/usr/share/color-schemes")
    _, pal = palettes.resolve("monastic")
    pal["motto"] = "Credo in unum Deum"
    svg_to_png(wallpaper_svg(pal, "chirho", False), SYSTEM_WALLPAPER, WALL_W, WALL_H)
    svg_to_png(wallpaper_svg(pal, "chirho", False, 1920, 1200),
               SYSTEM_WALLPAPER.with_name("1920x1200.png"), 1920, 1200)
    SPLASH_LOGO.parent.mkdir(parents=True, exist_ok=True)
    SPLASH_LOGO.write_text(logo_svg("chirho", pal["logo"]), encoding="utf-8")


def system_boot(logo, variant, rebuild_initrd=False):
    """Boot splash watermark + login screen background (needs root)."""
    if logo not in palettes.LOGOS or variant not in palettes.VARIANTS:
        raise SystemExit("unknown logo or variant")
    _, pal = palettes.resolve(variant)
    PLYMOUTH_DIR.mkdir(parents=True, exist_ok=True)
    svg_to_png(logo_svg(logo, pal["logo"]), PLYMOUTH_DIR / "watermark.png", 220, 220)
    SPLASH_LOGO.parent.mkdir(parents=True, exist_ok=True)
    SPLASH_LOGO.write_text(logo_svg(logo, pal["logo"]), encoding="utf-8")
    login = pathlib.Path("/usr/share/wallpapers/Credo/contents/images/login.png")
    svg_to_png(wallpaper_svg(pal, logo, True), login, WALL_W, WALL_H)
    SDDM_USER_CONF.parent.mkdir(parents=True, exist_ok=True)
    SDDM_USER_CONF.write_text(f"[General]\nbackground={login}\ntype=image\n", encoding="utf-8")
    bg = pal["wall_b"].lstrip("#")
    conf = PLYMOUTH_DIR / "credo.plymouth"
    if conf.exists():
        t = conf.read_text(encoding="utf-8")
        t = re.sub(r"BackgroundStartColor=.*", f"BackgroundStartColor=0x{pal['wall_a'].lstrip('#')}", t)
        t = re.sub(r"BackgroundEndColor=.*", f"BackgroundEndColor=0x{bg}", t)
        conf.write_text(t, encoding="utf-8")
    if rebuild_initrd:
        _run(["plymouth-set-default-theme", "-R", "credo"])


# ---------------------------------------------------------------- Kvantum (glass app windows)
KVANTUM_DIR = pathlib.Path("/usr/share/Kvantum")


def kvantum_theme(root=KVANTUM_DIR, base="KvDark", name="CredoGlass"):
    """Build the 'CredoGlass' Kvantum theme from Fedora's dark Kvantum theme: translucent,
    blurred windows and menus (macOS-style glass) in Credo's colours. Needs root."""
    import configparser
    src = pathlib.Path(root) / base
    svg = src / f"{base}.svg"
    if not svg.exists():
        raise SystemExit(f"{svg} not found (install kvantum-data)")
    dest = pathlib.Path(root) / name
    dest.mkdir(parents=True, exist_ok=True)
    # KvDark draws buttons, tool bars and frames in neutral greys baked into its SVG: tint those
    # greys towards Credo's dark green glass so every widget matches the window colour.
    import re

    def tint(m):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        if max(r, g, b) - min(r, g, b) > 14 or max(r, g, b) > 200:   # leave colours and near-whites
            return m.group(0)
        r, g, b = r * 0.86, min(255, g * 1.03 + 3), b * 0.92
        return "#%02x%02x%02x" % (round(r), round(g), round(b))
    (dest / f"{name}.svg").write_text(
        re.sub(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", tint, svg.read_text(encoding="utf-8")),
        encoding="utf-8")
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read(src / f"{base}.kvconfig", encoding="utf-8")
    g = "%General"
    if not cp.has_section(g):
        cp.add_section(g)
    for k, v in {"author": "Credo OS (from Kvantum's KvDark)", "comment": "Credo glass",
                 "translucent_windows": "true", "blurring": "true", "popup_blurring": "true",
                 "reduce_window_opacity": "8", "reduce_menu_opacity": "22", "composite": "true",
                 "menu_shadow_depth": "8", "tooltip_shadow_depth": "6", "menubar_mouse_tracking": "true",
                 "x11drag": "menubar_and_primary_toolbar", "contrast": "1.00", "intensity": "1.00",
                 "saturation": "1.20"}.items():
        cp.set(g, k, v)
    if not cp.has_section("Hacks"):
        cp.add_section("Hacks")
    cp.set("Hacks", "transparent_dolphin_view", "false")     # file view: same tinted sheet, readable
    cp.set("Hacks", "blur_translucent", "true")
    # No dark boxes behind tool bars: the toolbar sits on the window's glass, like the design.
    for sec in ("Toolbar", "MenuBar"):
        if not cp.has_section(sec):
            cp.add_section(sec)
        cp.set(sec, "interior", "false")
        cp.set(sec, "frame", "false")
    _, p = palettes.resolve("monastic")
    colors = {"window.color": p["bg"], "base.color": p["view"], "alt.base.color": p["bg_alt"],
              "button.color": _mix(p["bg"], p["fg"], 0.08), "light.color": _mix(p["bg"], p["fg"], 0.16),
              "mid.light.color": _mix(p["bg"], p["fg"], 0.12), "dark.color": _mix(p["bg"], "#000000", 0.4),
              "mid.color": _mix(p["bg"], "#000000", 0.2), "highlight.color": p["accent"],
              "inactive.highlight.color": _mix(p["accent"], p["bg"], 0.4), "text.color": p["fg"],
              "window.text.color": p["fg"], "button.text.color": p["fg"], "disabled.text.color": p["fg_dim"],
              "tooltip.text.color": p["fg"], "highlight.text.color": "#ffffff", "link.color": p["logo"],
              "link.visited.color": _mix(p["logo"], p["accent"], 0.5), "progress.indicator.text.color": p["fg"]}
    if not cp.has_section("GeneralColors"):
        cp.add_section("GeneralColors")
    for k, v in colors.items():
        cp.set("GeneralColors", k, v)
    with open(dest / f"{name}.kvconfig", "w", encoding="utf-8") as fh:
        cp.write(fh, space_around_delimiters=False)
    return dest


def use_kvantum(home=None):
    """Select Kvantum + CredoGlass for a user (or /etc/skel when home is given)."""
    base = pathlib.Path(home) if home else pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or config.HOME / ".config")
    kv = base / "Kvantum"
    kv.mkdir(parents=True, exist_ok=True)
    (kv / "kvantum.kvconfig").write_text("[General]\ntheme=CredoGlass\n", encoding="utf-8")


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(prog="credo-theme", description="Credo OS appearance")
    ap.add_argument("--variant", choices=list(palettes.VARIANTS))
    ap.add_argument("--logo", choices=list(palettes.LOGOS))
    ap.add_argument("--layout", choices=list(LAYOUTS), help="mac: menu bar + dock; classic: one taskbar")
    ap.add_argument("--panel-position", choices=["bottom", "top", "left", "right"],
                    help="where the dock (or taskbar) sits")
    ap.add_argument("--panel-height", type=int)
    ap.add_argument("--floating", choices=["yes", "no"])
    ap.add_argument("--wallpaper", choices=["yes", "no"])
    ap.add_argument("--motto", choices=["yes", "no"])
    ap.add_argument("--login", action="store_true", help="session start: apply, open welcome on first run")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--system-default", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--system-boot", nargs=2, metavar=("LOGO", "VARIANT"), help=argparse.SUPPRESS)
    ap.add_argument("--rebuild-initrd", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--system-kvantum", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--glass-apps", action="store_true", help="use the Credo Glass app style (Kvantum)")
    a = ap.parse_args(argv)
    if a.system_kvantum:
        print(kvantum_theme())
        return
    if a.glass_apps:
        use_kvantum()
        _run(["kwriteconfig6", "--file", "kdeglobals", "--group", "KDE", "--key", "widgetStyle", "kvantum"])
        print("Credo Glass app style selected; restart apps to see it.")
        return

    if a.system_default:
        return system_default()
    if a.system_boot:
        return system_boot(*a.system_boot, rebuild_initrd=a.rebuild_initrd)
    if a.list:
        lang = config.language()
        i = 1 if lang == "la" else 0
        print("Variants:"); [print(f"  {k:12} {v[i]}") for k, v in palettes.VARIANTS.items()]
        print("Logos:"); [print(f"  {k:12} {v[i]}") for k, v in palettes.LOGOS.items()]
        print("Layouts:"); [print(f"  {k:12} {v[i]}") for k, v in LAYOUTS.items()]
        return

    changes = {"variant": a.variant, "logo": a.logo, "layout": a.layout, "panel_position": a.panel_position,
               "panel_height": a.panel_height,
               "panel_floating": None if a.floating is None else a.floating == "yes",
               "wallpaper": None if a.wallpaper is None else a.wallpaper == "yes",
               "motto": None if a.motto is None else a.motto == "yes"}
    cp = config.load()
    for k, v in changes.items():
        if v is not None:
            cp.set("appearance", k, str(v).lower() if isinstance(v, bool) else str(v))
    config.save(cp)

    if a.login:
        os.environ["CREDO_LOGIN"] = "1"
        wait_for_plasma()
    apply_user(quiet=a.quiet)

    if a.login and cp.getboolean("general", "first_run", fallback=True):
        config.set_value("general", "first_run", "false")
        if shutil.which("credo-center"):
            subprocess.Popen(["credo-center", "--welcome"], start_new_session=True)


if __name__ == "__main__":
    sys.exit(main())
