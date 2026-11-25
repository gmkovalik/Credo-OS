# 1) Copy the Credo OS overlay (prepared by build.sh) into the image.
%post --nochroot --erroronfail
set -e
ROOT="${ANA_INSTALL_PATH:-${INSTALL_ROOT:-/mnt/sysroot}}"
tar --no-same-owner -xzf /tmp/credo-overlay.tar.gz -C "$ROOT"
if [ -f /tmp/credo-library.tar.gz ]; then
    tar --no-same-owner -xzf /tmp/credo-library.tar.gz -C "$ROOT"
fi
%end

# 2) Configure the system inside the image.
%post --erroronfail
set -e

# --- permissions (overlay is authored on any OS, so set modes explicitly) ---
chmod 0755 /usr/bin/credo-* /usr/libexec/credo/*
find /usr/lib/credo -type d -exec chmod 0755 {} +
find /usr/lib/credo -type f -exec chmod 0644 {} +
chown -R root:root /usr/lib/credo /usr/share/credo /etc/credo

# --- live session (Fedora livesys) ---
systemctl enable livesys.service livesys-late.service || true
if [ -f /etc/sysconfig/livesys ]; then
    sed -i 's/^livesys_session=.*/livesys_session="kde"/' /etc/sysconfig/livesys
else
    echo 'livesys_session="kde"' > /etc/sysconfig/livesys
fi
systemctl set-default graphical.target

# --- branding ---
OSR=/usr/lib/os-release
sed -i -e 's/^NAME=.*/NAME="Credo OS"/' \
       -e 's/^PRETTY_NAME=.*/PRETTY_NAME="Credo OS \$VERSION_ID"/' \
       -e '/^VARIANT=/d' -e '/^VARIANT_ID=/d' -e '/^LOGO=/d' "$OSR"
VER=$(. "$OSR"; echo "$VERSION_ID")
sed -i "s/\\\$VERSION_ID/$VER/" "$OSR"
printf 'VARIANT="Credo OS"\nVARIANT_ID=credo\nLOGO=credo\n' >> "$OSR"
# Our own identity, declared compatible with Fedora (software that checks for Fedora keeps working);
# no Fedora web links, which would suggest an official Fedora product.
sed -i -e 's/^ID=.*/ID=credo/' -e '/^ID_LIKE=/d' -e '/^HOME_URL=/d' -e '/^SUPPORT_URL=/d' \
       -e '/^BUG_REPORT_URL=/d' -e '/^DOCUMENTATION_URL=/d' -e '/^REDHAT_/d' -e '/^SUPPORT_END=/d' \
       -e '/^CPE_NAME=/d' -e '/^DEFAULT_HOSTNAME=/d' "$OSR"
printf 'ID_LIKE=fedora\nDEFAULT_HOSTNAME=credo\n' >> "$OSR"
printf 'Credo OS release %s\n' "$VER" > /etc/credo-release
ln -sfn credo-release /etc/system-release
# Legal notices, licence texts and the installed packages' licences (see docs/COMPLIANCE.md)
mkdir -p /usr/share/doc/credo-os
rpm -qa --qf '%{NAME}\t%{VERSION}-%{RELEASE}\t%{LICENSE}\t%{SOURCERPM}\t%{URL}\n' | sort \
    > /usr/share/doc/credo-os/package-licenses.tsv
# App icons: gold copies of the logos (the originals use currentColor, which icon
# themes would draw black).
mkdir -p /usr/share/icons/hicolor/scalable/apps
for f in /usr/share/credo/logos/*.svg; do
    n=$(basename "$f" .svg)
    sed 's/currentColor/#c9a227/g' "$f" > "/usr/share/icons/hicolor/scalable/apps/credo-$n.svg"
done
# The Credo icon theme's app icons (macOS style) also go to hicolor, so Credo apps keep
# their icons under any icon theme. They replace the plain logos above where names match.
cp -f /usr/share/icons/Credo/scalable/apps/credo*.svg /usr/share/icons/hicolor/scalable/apps/
# Credo-Light (light-mode icons) comes ready-made in the overlay, from tools/make_theme.py.
for t in hicolor Credo Credo-Light; do gtk-update-icon-cache -qf "/usr/share/icons/$t" || true; done

# GTK apps: Credo GTK theme, icons, and macOS button order by default.
for v in 3.0 4.0; do
    mkdir -p "/etc/gtk-$v"
    printf '[Settings]\ngtk-theme-name=Credo\ngtk-icon-theme-name=Credo\ngtk-decoration-layout=close,minimize,maximize:\ngtk-font-name=Inter 10\n' \
        > "/etc/gtk-$v/settings.ini"
done


# --- Latin: system locale la_VA.UTF-8 (KDE catalogs for "la" ship in the overlay) ---
localedef -i la_VA -f UTF-8 la_VA.UTF-8 || echo "warning: Latin locale not built"

# --- artwork: color schemes, wallpaper, boot splash, login screen ---
PYTHONPATH=/usr/lib/credo python3 -m credo.theme --system-default

cp -n /usr/share/plymouth/themes/spinner/*.png /usr/share/plymouth/themes/credo/ 2>/dev/null || true
PYTHONPATH=/usr/lib/credo python3 -m credo.theme --system-boot chirho monastic
plymouth-set-default-theme credo || true

mkdir -p /etc/sddm.conf.d
printf '[Theme]\nCurrent=breeze\n' > /etc/sddm.conf.d/10-credo.conf

# Credo Center is the welcome app; don't also open KDE's Welcome Center.
rm -f /etc/xdg/autostart/org.kde.plasma-welcome.desktop

# --- services ---
systemctl enable credo-thinkpad.service tuned.service thermald.service || true
systemctl --global enable credo-season.timer credo-angelus.timer || true

# --- Flathub for extra apps in Discover ---
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || true

# --- Credo branding everywhere Fedora's would show (boot titles, GRUB name, splash, login) ---
sh /usr/libexec/credo/rebrand || true

# --- Plain app names (Files, Terminal, Music...), as copies in /usr/local/share/applications ---
PYTHONPATH=/usr/lib/credo python3 -m credo.appnames || true

# --- SELinux labels for files added by the overlay ---
restorecon -RF /usr/bin /usr/lib/credo /usr/libexec/credo /usr/share/credo /usr/share/plasma \
    /usr/share/plymouth /usr/share/wallpapers /usr/share/color-schemes /etc/credo /etc/xdg \
    /usr/share/icons /usr/share/aurorae /usr/share/themes /usr/share/locale/la /usr/share/i18n \
    /usr/lib/systemd /usr/share/polkit-1 /usr/share/applications /usr/local/share/applications \
    2>/dev/null || true

# --- live image hygiene ---
rm -f /var/lib/systemd/random-seed
rm -f /etc/machine-id && touch /etc/machine-id
rpm --rebuilddb || true
%end

# 3) Copy the package licence list out of the image, so the build can publish it next to the ISO.
%post --nochroot
ROOT="${ANA_INSTALL_PATH:-${INSTALL_ROOT:-/mnt/sysroot}}"
cp -f "$ROOT/usr/share/doc/credo-os/package-licenses.tsv" /tmp/credo-package-licenses.tsv 2>/dev/null || true
%end
