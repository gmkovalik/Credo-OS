#!/bin/bash
# Pull the exact source strings of KDE's catalogs (via Fedora's Italian translations) for
# tools/make_latin.py. Run on Fedora (or Fedora WSL) as root:
#   sudo bash tools/fetch_kde_strings.sh /tmp/kde-strings && python3 tools/make_latin.py /tmp/kde-strings
set -eu
OUT=${1:-/tmp/kde-strings}
mkdir -p "$OUT"
rpm -q gettext >/dev/null || dnf -y -q install gettext
D=$(mktemp -d); cd "$D"
dnf -q download plasma-desktop plasma-workspace dolphin kf6-kxmlgui kf6-kconfigwidgets >/dev/null
for r in *.rpm; do rpm2cpio "$r" | cpio -idm --quiet 2>/dev/null; done
for dom in plasma_applet_org.kde.plasma.kickoff plasma_applet_org.kde.plasma.digitalclock \
           plasma_applet_org.kde.plasma.taskmanager plasma_applet_org.kde.plasma.systemtray \
           dolphin kxmlgui6 kconfigwidgets6; do
    mo=$(find . -path "*/locale/it/LC_MESSAGES/$dom.mo" | head -1)
    [ -n "$mo" ] && msgunfmt "$mo" > "$OUT/$dom.it.po" && echo "$dom"
done
rm -rf "$D"
