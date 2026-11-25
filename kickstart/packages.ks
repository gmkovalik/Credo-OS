# --ignoremissing keeps the build going if Fedora renames or drops a package
# between releases; check the build log for "No match for" warnings.
%packages --ignoremissing

# ---------- Base desktop: KDE Plasma ----------
@^kde-desktop-environment
@kde-apps
@kde-media
@firefox
@fonts
@hardware-support
@multimedia
@networkmanager-submodules
@printing

# ---------- Branding: no Fedora logos (Fedora Remix trademark rules) ----------
generic-logos
generic-logos-httpd
-fedora-logos
-fedora-logos-httpd
# release identity: Fedora's own release packages -> the neutral "generic" set (provides system-release)
generic-release
generic-release-common
generic-release-notes
-fedora-release
-fedora-release-common
-fedora-release-kde
-fedora-release-identity-kde
-fedora-release-identity-basic
-fedora-release-notes

# ---------- Live image + installer ----------
anaconda-live
anaconda-install-env-deps
@anaconda-tools
livesys-scripts
dracut-live
dracut-config-generic
kernel
kernel-modules
kernel-modules-extra
grub2-efi-x64
grub2-efi-x64-cdboot
grub2-pc
grub2-pc-modules
grub2-tools
grub2-tools-extra
shim-x64
efibootmgr
syslinux
syslinux-nonlinux
memtest86+
glibc-all-langpacks
# sources for building the Credo Latin locale (la_VA) in post.ks
glibc-locale-source

# ---------- ThinkPad X1 Carbon Gen 11 hardware ----------
linux-firmware
iwlwifi-mvm-firmware
alsa-sof-firmware
alsa-ucm
intel-gpu-firmware
fprintd
fprintd-pam
fwupd
fwupd-plugin-uefi-capsule-data
tuned
tuned-ppd
thermald
powertop
libcamera
libcamera-tools
pipewire-plugin-libcamera
bluez
iio-sensor-proxy
smartmontools
nvme-cli
lm_sensors

# ---------- Bundled applications ----------
firefox
thunderbird
dolphin
konsole
kate
okular
gwenview
ark
spectacle
kcalc
kcharselect
elisa-player
haruna
mpv
libreoffice-writer
libreoffice-calc
libreoffice-impress
gimp
inkscape
keepassxc
kiwix-desktop
kiwix-tools
xiphos
kde-partitionmanager
filelight
kdeconnectd
kwalletmanager
plasma-discover
plasma-discover-flatpak
plasma-systemmonitor
flatpak
htop
btop
fastfetch
git
wget2-wget
unzip
p7zip
poppler-utils

# ---------- Catholic study ----------
# Bible: SWORD apps; Credo Center -> Study downloads the Douay-Rheims and Vulgate modules.
bibletime
sword-utils
# Books, dictionaries, notes
calibre
foliate
goldendict-ng
xournalpp
Zim
# Sacred music
musescore
frescobaldi
lilypond
audacity

# ---------- Credo OS runtime ----------
python3
python3-pyside6
# Credo Browser (Chromium engine) and Credo Console (terminal emulation)
qt6-qtwebengine
python3-pyte
librsvg2-tools
plymouth-plugin-two-step
plymouth-theme-spinner
glib2
sqlite
google-noto-serif-fonts
google-noto-sans-fonts
liberation-serif-fonts
dejavu-serif-fonts
# macOS-like look: Inter UI font; notifications from scripts (Angelus reminder)
rsms-inter-fonts
libnotify

# ---------- Trim ----------
-@dial-up
-@input-methods
-kmahjongg
-kmines
-kpat
-dragon
-akregator
-kontact
-kmail
-korganizer

%end
