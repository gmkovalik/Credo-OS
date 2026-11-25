"""Build dist/credo-update.tar.gz: brings a running Credo OS up to date without a new ISO.

It carries the overlay's programs and data (no /etc), the desktop theme installer, and
update.sh, which installs the extra Fedora packages, copies the files, builds the Latin
locale, and applies the theme and the new dock for the current user.

    python tools/make_update.py
"""
import pathlib
import shutil
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
PKG = DIST / "credo-update"

UPDATE = r"""#!/bin/sh
# Credo OS update: new apps (Credo Browser, Credo Console), macOS-style theme, Latin.
#   sh update.sh            install everything and apply the theme for you
#   sh update.sh --latin    ...and switch the whole desktop to Latin (from the next login)
#   sh update.sh --light    ...use the light theme variants
#   sh update.sh --refresh-desktop   ...also rebuild the menu bar, dock and widgets (resets their
#                                     positions and settings; normally your desktop is left as it is)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SUDO=""; [ "$(id -u)" != 0 ] && SUDO=sudo
LATIN=0; THEME_ARGS=""; REFRESH=0
for a in "$@"; do
  case "$a" in --latin) LATIN=1 ;; --light) THEME_ARGS="--light" ;; --refresh-desktop) REFRESH=1 ;; esac
done

echo "== 1/5 Installing packages (needs the internet) ..."
$SUDO dnf -y install python3-pyte qt6-qtwebengine python3-pyside6 glibc-locale-source rsms-inter-fonts libnotify \
  || echo "   (some packages could not be installed; continuing)"

echo "== 2/5 Copying Credo files ..."
# Older versions installed some folders as links (e.g. icons/Credo-Light/scalable); cp cannot copy a
# folder over a link, so remove any link standing where this update has a real folder.
(cd "$HERE/usr" && find . -type d) | while read -r d; do
  t="/usr/${d#./}"
  if [ -L "$t" ] || { [ -e "$t" ] && [ ! -d "$t" ]; }; then $SUDO rm -f "$t"; fi
done
$SUDO cp -r "$HERE/usr/." /usr/
$SUDO chmod 0755 /usr/bin/credo-* /usr/libexec/credo/* 2>/dev/null || true
$SUDO find /usr/lib/credo -type f -exec chmod 0644 {} +
$SUDO cp -f /usr/share/icons/Credo/scalable/apps/credo*.svg /usr/share/icons/hicolor/scalable/apps/ 2>/dev/null || true
$SUDO gtk-update-icon-cache -qf /usr/share/icons/hicolor 2>/dev/null || true
command -v update-desktop-database >/dev/null && $SUDO update-desktop-database -q /usr/share/applications || true
command -v restorecon >/dev/null && $SUDO restorecon -RF /usr/lib/credo /usr/bin /usr/share/icons /usr/share/aurorae \
  /usr/share/themes /usr/share/locale/la /usr/share/applications /usr/share/plasma 2>/dev/null || true

# Plain app names (Files, Terminal, Music...) and the Finder-like Files settings.
$SUDO env PYTHONPATH=/usr/lib/credo python3 -m credo.appnames >/dev/null 2>&1 || true
$SUDO cp -f "$HERE/etc/xdg/dolphinrc" /etc/xdg/dolphinrc 2>/dev/null || true
for kv in General:ShowStatusBar:Disabled General:ShowZoomSlider:false General:ShowSpaceInfo:false \
          General:BrowseThroughArchives:true MainWindow:MenuBar:Disabled IconsMode:IconSize:64 \
          DetailsMode:ExpandableFolders:true; do
  IFS=: read -r g k v <<EOF
$kv
EOF
  "$(command -v kwriteconfig6 || command -v kwriteconfig5)" --file dolphinrc --group "$g" --key "$k" "$v"
done
# A Launchpad left stuck by an older version would swallow every dock click: end it.
pkill -9 -f credo.launchpad 2>/dev/null || true
# App style: flat Breeze in Credo colours, frosted menus (the Kvantum glass style had gradient buttons).
KW=$(command -v kwriteconfig6 || command -v kwriteconfig5)
$KW --file kdeglobals --group KDE --key widgetStyle Breeze
$KW --file breezerc --group Style --key MenuOpacity 82
$KW --file breezerc --group Style --key ToolBarDrawItemSeparator false
$KW --file breezerc --group Style --key ViewDrawFrame false
$KW --file breezerc --group Style --key SidePanelDrawFrame false

echo "== 3/5 Building the Latin locale (la_VA.UTF-8) ..."
$SUDO localedef -i la_VA -f UTF-8 la_VA.UTF-8 && echo "   ok" || echo "   (could not build the Latin locale)"

echo "== 4/5 Applying the Credo theme (icons, window buttons, GTK) ..."
sh "$HERE/theme/install.sh" $THEME_ARGS

echo "== 5/5 Finishing (your menu bar, dock and widgets are left as they are) ..."
pkill -x crystal-dock 2>/dev/null || true                     # from an earlier Credo update
rm -rf "$HOME/.crystal-dock-2" "$HOME/.config/autostart/crystal-dock.desktop"
if [ "$REFRESH" = 1 ]; then
  # Only on request: restart Plasma and rebuild the menu bar, dock and widgets from scratch.
  systemctl --user restart plasma-plasmashell.service 2>/dev/null \
    || { kquitapp6 plasmashell 2>/dev/null; sleep 2; (kstart plasmashell >/dev/null 2>&1 &); }
  sleep 8
  CREDO_REBUILD_PANELS=1 credo-theme --motto no --quiet || true
fi
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now credo-angelus.timer 2>/dev/null || true
if [ "$LATIN" = 1 ]; then
  KW=$(command -v kwriteconfig6 || command -v kwriteconfig5)
  $KW --file plasma-localerc --group Formats --key LANG la_VA.UTF-8
  $KW --file plasma-localerc --group Translations --key LANGUAGE la:en_US
  PYTHONPATH=/usr/lib/credo python3 -c "from credo import config; config.set_value('general','language','la')"
  echo "   Latin is set: log out and back in to see the desktop in Latin."
fi
echo
echo "Done. Log out and back in once to see every change (your widgets and settings are kept)."
"""


def sync_build_kit():
    """Copy the build recipe into the overlay (/usr/share/credo/build), for Make Credo ISO."""
    kit = ROOT / "overlay/usr/share/credo/build"
    if kit.exists():
        shutil.rmtree(kit)
    (kit / "build").mkdir(parents=True)
    (kit / "kickstart").mkdir()
    (kit / "tools/assets").mkdir(parents=True)
    shutil.copy(ROOT / "build/build.sh", kit / "build")
    for ks in (ROOT / "kickstart").glob("*.ks"):
        shutil.copy(ks, kit / "kickstart")
    shutil.copy(ROOT / "tools/assets/credo-fssp-public.svg", kit / "tools/assets")
    etc = sorted("/" + p.relative_to(ROOT / "overlay").as_posix() for p in (ROOT / "overlay/etc").rglob("*") if p.is_file())
    (kit / "etc-files.txt").write_text("\n".join(etc) + "\n", encoding="utf-8")


def main():
    sync_build_kit()
    if PKG.exists():
        shutil.rmtree(PKG)
    PKG.mkdir(parents=True)
    subprocess.run([sys.executable, str(ROOT / "tools/make_theme.py")], check=True)
    shutil.copytree(ROOT / "overlay/usr", PKG / "usr",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(DIST / "credo-theme", PKG / "theme")
    (PKG / "etc/xdg").mkdir(parents=True)
    shutil.copy(ROOT / "overlay/etc/xdg/dolphinrc", PKG / "etc/xdg/dolphinrc")
    (PKG / "update.sh").write_bytes(UPDATE.encode("utf-8"))
    out = DIST / "credo-update.tar.gz"

    def norm(ti):
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "root"
        executable = ti.isdir() or ti.name.endswith(".sh") or "/usr/bin/" in ti.name or "/libexec/" in ti.name
        ti.mode = 0o755 if executable else 0o644
        return ti
    with tarfile.open(out, "w:gz") as tar:
        tar.add(PKG, arcname="credo-update", filter=norm)
    print(f"{out} ({out.stat().st_size // 1024} KB)")

    # One self-installing file for an installed Credo OS: "sh Credo-Update.sh" (or open it in a
    # terminal). It unpacks the archive appended after the __ARCHIVE__ line and runs update.sh.
    head = (b"#!/bin/sh\n"
            b"# Credo OS update: brings an installed Credo OS up to date, no reinstall.\n"
            b"#   sh Credo-Update.sh          (add --latin or --light if you like)\n"
            b"[ -t 0 ] || exec konsole --hold -e sh \"$0\" \"$@\"\n"
            b"T=$(mktemp -d)\n"
            b"N=$(awk '/^__ARCHIVE__$/ { print NR + 1; exit }' \"$0\")\n"
            b"tail -n +\"$N\" \"$0\" | tar xz -C \"$T\" || { echo 'The update file is damaged.'; exit 1; }\n"
            b"sh \"$T/credo-update/update.sh\" \"$@\"\n"
            b"rc=$?\n"
            b"rm -rf \"$T\"\n"
            b"exit $rc\n"
            b"__ARCHIVE__\n")
    run = DIST / "Credo-Update.sh"
    run.write_bytes(head + out.read_bytes())
    print(f"{run} ({run.stat().st_size // 1024} KB)")
    make_app_installer("FSSP-App.sh", "the FSSP app (monthly prayer card and Cum Petro)", "credo-fssp",
                       ["usr/lib/credo/credo/fssp.py", "usr/bin/credo-fssp",
                        "usr/share/applications/credo-fssp.desktop",
                        "usr/share/icons/Credo/scalable/apps/credo-fssp.svg",
                        "usr/share/icons/Credo-Light/scalable/apps/credo-fssp.svg"],
                       after='echo "Installed. Find it in Launchpad or search: FSSP."')
    make_app_installer("Security-Check.sh", "Credo Security Check", "security-high",
                       ["usr/lib/credo/credo/securitycheck.py", "usr/bin/credo-security-check",
                        "usr/share/applications/credo-security-check.desktop"],
                       after='echo "Installed. Open Security Check from Launchpad, or run: credo-security-check (sudo for the full audit)."')
    make_app_installer("Credo-Branding.sh", "Credo OS branding in place of Fedora's logos and names", "credo",
                       ["usr/libexec/credo/rebrand"],
                       after='$SUDO sh /usr/libexec/credo/rebrand')
    make_app_installer("Credo-Welcome.sh", "the new Credo Welcome app and Credo logos in place of KDE's", "credo",
                       ["usr/lib/credo/credo/welcome.py", "usr/lib/credo/credo/appnames.py", "usr/bin/credo-welcome",
                        "usr/share/applications/credo-welcome.desktop", "etc/xdg/autostart/credo-welcome.desktop",
                        "usr/share/icons/Credo/scalable/apps/kde.svg", "usr/share/icons/Credo-Light/scalable/apps/kde.svg",
                        "usr/share/icons/Credo/scalable/apps/plasma.svg", "usr/share/icons/Credo-Light/scalable/apps/plasma.svg",
                        "usr/share/icons/Credo/scalable/apps/start-here-kde-symbolic.svg", "usr/share/icons/Credo-Light/scalable/apps/start-here-kde-symbolic.svg",
                        "usr/share/icons/Credo/scalable/apps/start-here-kde-plasma-symbolic.svg", "usr/share/icons/Credo-Light/scalable/apps/start-here-kde-plasma-symbolic.svg",
                        "usr/share/icons/Credo/scalable/apps/start-here-symbolic.svg", "usr/share/icons/Credo-Light/scalable/apps/start-here-symbolic.svg",
                        "usr/share/icons/Credo/scalable/apps/distributor-logo.svg", "usr/share/icons/Credo-Light/scalable/apps/distributor-logo.svg",
                        "usr/share/icons/Credo/scalable/apps/org.kde.plasma-welcome.svg", "usr/share/icons/Credo-Light/scalable/apps/org.kde.plasma-welcome.svg",
                        "usr/share/icons/Credo/scalable/apps/plasma-welcome.svg", "usr/share/icons/Credo-Light/scalable/apps/plasma-welcome.svg"],
                       after=('$SUDO env PYTHONPATH=/usr/lib/credo python3 -m credo.appnames >/dev/null 2>&1\n'
                              'kbuildsycoca6 >/dev/null 2>&1\n'
                              '(setsid credo-welcome >/dev/null 2>&1 < /dev/null &)\n'
                              'echo "Installed. Welcome is open now, and in the app grid any time."'))
    make_app_installer("ISO-Builder.sh", "Make Credo ISO (build an installable ISO of this Credo OS)", "credo",
                       ["usr/lib/credo/credo/makeiso.py",
                        "usr/bin/credo-make-iso",
                        "usr/share/applications/credo-make-iso.desktop",
                        "usr/libexec/credo/make-iso",
                        "usr/share/credo/build/build/build.sh",
                        "usr/share/credo/build/etc-files.txt",
                        "usr/share/credo/build/tools/assets/credo-fssp-public.svg",
                        "usr/share/credo/build/kickstart/credo-os.ks",
                        "usr/share/credo/build/kickstart/packages.ks",
                        "usr/share/credo/build/kickstart/post.ks"],
                       after=('$SUDO chmod 0755 /usr/libexec/credo/make-iso\n'
                              'echo "Installed. Open Make Credo ISO from Apps."'))
    make_app_installer("Today-Saints.sh", "the saint's life and propers on the Today page", "credo-today",
                       ["usr/lib/credo/credo/pages.py", "usr/share/credo/saint-lives.json"],
                       after=('pkill -f "credo.library serve" 2>/dev/null   # restarts with the new Today page\n'
                              'echo "Installed. Open Today (or reload it) to see the saint\'s life and propers."'))


def make_app_installer(name, what, icon, files, after=""):
    """A small self-installing file for one app: copies only its files, refreshes the app list and
    icon caches. It never restarts Plasma or touches the menu bar, dock, widgets or settings."""
    import io
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel in files:
            src = ROOT / "overlay" / rel
            ti = tar.gettarinfo(str(src), arcname=rel)
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = "root"
            ti.mode = 0o755 if rel.startswith("usr/bin/") else 0o644
            with open(src, "rb") as fh:
                tar.addfile(ti, fh)
    head = f"""#!/bin/sh
# Installs {what} on Credo OS. Your desktop, widgets and settings are not touched.
#   sh {name}
[ -t 0 ] || exec konsole --hold -e sh "$0" "$@"
SUDO=""; [ "$(id -u)" != 0 ] && SUDO=sudo
rpm -q python3-pyside6 qt6-qtwebengine >/dev/null 2>&1 || $SUDO dnf -y install python3-pyside6 qt6-qtwebengine
T=$(mktemp -d)
N=$(awk '/^__ARCHIVE__$/ {{ print NR + 1; exit }}' "$0")
tail -n +"$N" "$0" | tar xz -C "$T" || {{ echo "The installer file is damaged."; exit 1; }}
$SUDO cp -r "$T/usr/." /usr/
[ -d "$T/etc" ] && $SUDO cp -r "$T/etc/." /etc/
$SUDO chmod 0755 /usr/bin/credo-* 2>/dev/null
[ -f /usr/share/icons/Credo/scalable/apps/{icon}.svg ] && $SUDO cp -f /usr/share/icons/Credo/scalable/apps/{icon}.svg /usr/share/icons/hicolor/scalable/apps/
for t in hicolor Credo Credo-Light; do $SUDO gtk-update-icon-cache -qf /usr/share/icons/$t 2>/dev/null; done
command -v update-desktop-database >/dev/null && $SUDO update-desktop-database -q /usr/share/applications
command -v restorecon >/dev/null && $SUDO restorecon -RF /usr/lib/credo /usr/share/credo /usr/bin /usr/share/applications \\
  /usr/share/icons 2>/dev/null
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1      # show it in Launchpad / search now
rm -rf "$T"
{after}
exit 0
__ARCHIVE__
""".encode()
    out = DIST / name
    out.write_bytes(head + buf.getvalue())
    print(f"{out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
