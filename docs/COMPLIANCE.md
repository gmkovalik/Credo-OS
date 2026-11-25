# Credo OS release compliance

How Credo OS meets each point of the release checklist, and what still needs doing before a
public release. (General guidance, not legal advice.)

**How it's built:** a *custom Fedora installer image*. `build/build.sh` runs Fedora's own tools
(livemedia-creator/lorax + Anaconda) on the kickstarts in `kickstart/`, using **unmodified Fedora
packages** from Fedora's repositories, plus Credo's own files (`overlay/`). No Fedora package is
patched or rebuilt.

| # | Checklist item | Status | How |
|---|----------------|--------|-----|
| 1 | Remove Fedora logos, wallpapers, boot graphics | ✅ Done | `fedora-logos(-httpd)` replaced by `generic-logos(-httpd)` (`kickstart/packages.ks`); Credo wallpaper, Credo Plymouth splash, Credo Plasma splash, Breeze login (not Fedora's). `/usr/libexec/credo/rebrand` does the same on installed systems. |
| 2 | Replace Fedora branding in installer and bootloader | ✅ Done | Installer product name "Credo OS" (`--project "Credo OS"`); ISO label `CREDO-OS-45`; boot entries and `GRUB_DISTRIBUTOR` say "Credo OS" (`rebrand`). |
| 3 | Replace Fedora release identification | ✅ Done (in the next ISO build) | `fedora-release*` replaced by `generic-release*`; `/usr/lib/os-release`: `NAME="Credo OS"`, `ID=credo`, `ID_LIKE=fedora`, `LOGO=credo`, no Fedora URLs; `/etc/system-release` → "Credo OS release 45". |
| 4 | Check every RPM's licence | ✅ Automated | Each build writes the licence of every installed package to `/usr/share/doc/credo-os/package-licenses.tsv` (in the system) and `out/…/Credo-OS-45-x86_64.iso.packages.tsv` (published with the ISO). All come from Fedora's main repositories, which only accept free, redistributable licences. |
| 5 | Include copyright and licence notices | ✅ Done | Every package keeps its own `/usr/share/licenses/<pkg>/` files (nothing is stripped). Credo adds `/usr/share/doc/credo-os/NOTICE.txt`, `CREDITS.md` and `licenses/` (GPL-3.0, Divinum Officium MIT). |
| 6 | Provide corresponding source for GPL binaries | ✅ Tool ready; do it each release | `tools/fetch_sources.sh <packages.tsv> <folder>` downloads the matching source RPMs (several GB) right after building; publish them next to the ISO with `SHA256SUMS`. Credo's own sources = this repository (kickstarts, overlay, tools). |
| 7 | Third-party repos, drivers, firmware, codecs | ✅ OK | Only Fedora's repositories are used. No RPM Fusion, no proprietary drivers or codecs in the ISO (Credo Center can *enable* RPM Fusion on request; the user downloads it). Firmware = Fedora's `linux-firmware` (redistributable, licences in `/usr/share/licenses/linux-firmware`). Flathub is only *configured*, no apps are shipped. |
| 8 | Credo's own software and artwork redistributable | ⚠️ One item | Code: GPL-3.0-or-later (`LICENSE`). Chi-Rho and artwork: original to the Credo OS author. Divinum Officium data: MIT (notice included). **FSSP emblem: needs the Fraternity's permission**; public builds (`CREDO_PUBLIC=1`) use a neutral icon instead. Personal wallpapers are excluded (`.gitignore`, never in the overlay). |
| 9 | Legal notices page on the website | 📝 Text ready | Publish `NOTICE.txt` and `CREDITS.md` as the website's "Legal" page. |
| 10 | Statement of independence from Fedora and Red Hat | ✅ Done | In `NOTICE.txt`, plus "not an official product of the Catholic Church". Describe it as "an independent Linux distribution based on Fedora Linux". |
| 11 | Test the ISO and installation | ⬜ Each release | Build with `CREDO_PUBLIC=1` on a Fedora machine (the build refuses WSL, so SELinux is enforcing). Then:<br>1. Install in a VM (UEFI + Secure Boot) and on real hardware.<br>2. Run `sudo credo-security-check`.<br>3. Check that no Fedora logo appears (boot menu, splash, installer, login, About). |

## Also changed for trademarks
- Apple: "Launchpad" renamed **Apps** everywhere users see it; "Finder" was already **Files**.
  (Internal file names such as `credo-launchpad` are not shown to users.)
- KDE: KDE's Welcome Center is hidden and replaced by Credo Welcome; KDE/Plasma logo icons show
  the Credo logo. KDE's name stays where it is a factual credit (e.g. "KDE Plasma version").

## Release steps
1. `CREDO_PUBLIC=1 sudo ./build/build.sh --out out/release` on a Fedora machine with SELinux.
2. `bash tools/fetch_sources.sh out/release/Credo-OS-45-x86_64.iso.packages.tsv out/release/sources`
3. Sign `SHA256SUMS` (ISO + sources) with your GPG or minisign key.
4. Publish:
   - the ISO, `.sha256`, `.packages.tsv` and `sources/`;
   - this repository (without `out/`, `dist/`, `personal-wallpapers/`);
   - `NOTICE.txt` and `CREDITS.md` as the website's Legal page.
