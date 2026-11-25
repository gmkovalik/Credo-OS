#!/usr/bin/env bash
# Build the Credo OS live ISO on a Fedora host (bare metal, VM, WSL or a privileged container).
#
#   sudo ./build/build.sh [--releasever 43] [--out DIR] [--with-library]
#
# --with-library downloads the Catholic library at build time and ships it inside the ISO
# (several hours and a few GB). Without it, the library is downloaded on first use
# from Credo Center -> Library.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASEVER="$(rpm -E %fedora 2>/dev/null || echo 43)"
OUT="$HERE/out"
WORK="/var/tmp/credo-build"
WITH_LIBRARY=0

while [ $# -gt 0 ]; do
    case "$1" in
        --releasever) RELEASEVER="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --with-library) WITH_LIBRARY=1; shift ;;
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

if [ "$EUID" -ne 0 ]; then
    exec sudo -E "$0" "$@"
fi

if ! grep -q '^ID=fedora' /etc/os-release; then
    echo "This must run on Fedora (use build/build-container.sh from other Linux hosts)." >&2
    exit 1
fi

echo "==> Installing build tools"
# policycoreutils: anaconda calls load_policy even when the host (WSL, containers) has no SELinux.
dnf -y install lorax lorax-lmc-novirt anaconda-tui pykickstart python3 librsvg2-tools git tar gzip \
    policycoreutils

SELINUX_MODE=enforcing
RESTORE_ENFORCE=0
if command -v selinuxenabled >/dev/null && selinuxenabled; then
    if [ "$(getenforce)" = "Enforcing" ]; then
        setenforce 0
        RESTORE_ENFORCE=1
    fi
else
    echo "==> Host has no SELinux (WSL/container); image will boot SELinux permissive."
    SELINUX_MODE=permissive
fi
# Public releases must protect users fully: build them on a Fedora machine with SELinux, so files
# get correct security labels and the system runs SELinux enforcing.
if [ "${CREDO_PUBLIC:-0}" = 1 ] && [ "$SELINUX_MODE" != enforcing ]; then
    echo "!! CREDO_PUBLIC=1 needs a Fedora build host with SELinux enabled (not WSL or a container)." >&2
    exit 1
fi
cleanup() {
    [ "$RESTORE_ENFORCE" = 1 ] && setenforce 1 || true
    rm -f /tmp/credo-overlay.tar.gz /tmp/credo-library.tar.gz
}
trap cleanup EXIT

rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"
# A failed anaconda run leaves /run/anaconda/installation-error-msg behind; the next
# run then believes the install already failed and has no tasks ("list index out of range").
rm -rf /run/anaconda
if ! pgrep -x anaconda >/dev/null; then
    rm -f /run/user/0/anaconda.pid /var/run/anaconda.pid      # stale after an interrupted run
fi

echo "==> Preparing overlay"
cp -a "$HERE/overlay" "$WORK/overlay"
cp -a "$HERE/kickstart" "$WORK/kickstart"
# Strip Windows line endings in case the tree was edited on Windows.
find "$WORK/overlay" "$WORK/kickstart" -type f \
    \( -name '*.py' -o -name '*.sh' -o -name '*.ks' -o -name '*.desktop' -o -name '*.conf' \
       -o -name '*.service' -o -name '*.timer' -o -name '*.js' -o -name '*.qml' -o -name '*.json' \
       -o -name '*.svg' -o -name '*.plymouth' -o -name '*.policy' -o -name 'defaults' \
       -o -name 'kdeglobals' -o -name 'kxkbrc' -o -name '*rc' -o -path '*/usr/bin/*' -o -path '*/libexec/*' \) \
    -exec sed -i 's/\r$//' {} +
# The FSSP app is not part of Credo OS itself (installed separately with FSSP-App.sh).
rm -f "$WORK/overlay/usr/lib/credo/credo/fssp.py" "$WORK/overlay/usr/bin/credo-fssp" \
      "$WORK/overlay/usr/share/applications/credo-fssp.desktop" \
      "$WORK/overlay/usr/share/icons/Credo/scalable/apps/credo-fssp.svg" \
      "$WORK/overlay/usr/share/icons/Credo-Light/scalable/apps/credo-fssp.svg"
# Personal builds only: the church photos (personal-use downloads) as wallpapers, St. Peter's
# statue as the default. Public builds (CREDO_PUBLIC=1) never include them.
WP="$HERE/personal-wallpapers/packages"
if [ "${CREDO_PUBLIC:-0}" != 1 ] && [ -d "$WP" ]; then
  echo "==> Personal build: adding $(ls "$WP" | wc -l) church wallpapers (St. Peter's statue as default)"
  mkdir -p "$WORK/overlay/usr/share/wallpapers"
  cp -r "$WP"/. "$WORK/overlay/usr/share/wallpapers/"
  DEFAULT_WP="/usr/share/wallpapers/Credo-St-Peter-s-Basilica-st-peter-statue/"
  sed -i "s|file:///usr/share/wallpapers/Credo/contents/images/2880x1800.png|file://$DEFAULT_WP|" \
    "$WORK/overlay/usr/share/plasma/look-and-feel/org.credo.desktop/contents/layouts/org.kde.plasma.desktop-layout.js"
  # keep Credo's generated wallpaper from replacing it
  sed -i 's/^wallpaper = true/wallpaper = false/' "$WORK/overlay/etc/credo/defaults.conf"
fi
# Standard permissions (files copied from Windows can arrive writable by everyone).
find "$WORK/overlay" -type d -exec chmod 0755 {} +
find "$WORK/overlay" -type f -exec chmod 0644 {} +
chmod 0755 "$WORK/overlay"/usr/bin/* "$WORK/overlay"/usr/libexec/credo/* 2>/dev/null || true
tar -C "$WORK/overlay" --owner=0 --group=0 -czf /tmp/credo-overlay.tar.gz .

if [ "$WITH_LIBRARY" = 1 ]; then
    echo "==> Downloading the Catholic library (this takes a long time)"
    mkdir -p "$WORK/libdata" "$WORK/libroot/usr/share/credo/library"
    XDG_DATA_HOME="$WORK/libdata" PYTHONPATH="$WORK/overlay/usr/lib/credo" \
        python3 -m credo.library fetch all
    cp "$WORK/libdata/credo/library.db" "$WORK/libroot/usr/share/credo/library/library.db"
    tar -C "$WORK/libroot" --owner=0 --group=0 -czf /tmp/credo-library.tar.gz .
fi

echo "==> Flattening kickstart"
sed -i "s/@SELINUX@/$SELINUX_MODE/" "$WORK/kickstart/credo-os.ks"
(cd "$WORK/kickstart" && ksflatten -c credo-os.ks -o "$WORK/credo-os-flat.ks")

echo "==> Building ISO for Fedora $RELEASEVER (30-60 minutes)"
ISO="Credo-OS-$RELEASEVER-x86_64.iso"
livemedia-creator \
    --make-iso --no-virt --iso-only \
    --ks "$WORK/credo-os-flat.ks" \
    --resultdir "$WORK/result" \
    --logfile "$WORK/lmc.log" \
    --project "Credo OS" \
    --releasever "$RELEASEVER" \
    --volid "CREDO-OS-$RELEASEVER" \
    --iso-name "$ISO" \
    --nomacboot

mv "$WORK/result/$ISO" "$OUT/$ISO"
(cd "$OUT" && sha256sum "$ISO" > "$ISO.sha256")
# Licences of every package in the image (publish with the ISO; tools/fetch_sources.sh uses it)
[ -f /tmp/credo-package-licenses.tsv ] && cp -f /tmp/credo-package-licenses.tsv "$OUT/$ISO.packages.tsv"
echo "==> Done: $OUT/$ISO"
echo "    Write it to a USB stick with Fedora Media Writer, then boot the X1 with F12."
