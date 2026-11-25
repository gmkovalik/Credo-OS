# Credo OS

*Credo in unum Deum.*

Credo OS is an independent Linux distribution based on Fedora Linux and KDE Plasma: a calm,
Catholic computer for prayer, study and everyday work. It is tuned for the Lenovo ThinkPad X1
Carbon Gen 11 and runs on most 64-bit PCs.

> Credo OS is not affiliated with, sponsored by or endorsed by the Fedora Project or Red Hat, and
> is not an official product of the Catholic Church. See [NOTICE.txt](NOTICE.txt).

## What's in it

**Prayer and the liturgy (1954 Missal and Breviary)**
- **Today**: the feast and liturgical colour, the saint's life (Matins lessons, Latin and English),
  the propers of the saint's Mass, fasting and abstinence, and the coming feasts.
- **Mass of the Day**, a liturgical calendar for any year, and the Ordinary of the Mass.
- **Holy Rosary** prayed bead by bead, **Prayers**, **Examination of Conscience**, and an
  **Angelus reminder** (Regina Cæli in Eastertide).
- Desktop widgets: Today, the day's Rosary mysteries, and a clock with Roman numerals.

**The Church's library**
- **Catholic Library**: papal documents before Vatican II, writings of the saints, the Roman
  Catechism and the 1954 Missal, downloaded on request, with full-text search.
- Bible study (Xiphos, BibleTime), e-books (Calibre, Foliate), a dictionary, notes and sacred-music tools.

**A calm desktop**
- A menu bar with the Credo menu and the liturgical day, a dock, and an app grid (**Apps**).
- Dark green glass or warm ivory themes; Credo icons, window style and wallpapers; plain app
  names (Files, Terminal, Music…).
- **Credo Browser** (with tracker blocking), **Credo Console**, **Credo Center** (settings,
  devotions, study, appearance, ThinkPad tuning), and **Welcome**, a first-run tour.
- English or **Latin** for the whole desktop.

**Other systems' programs**
- **Windows apps**: everyday programs through Bottles; large ones (SolidWorks, Adobe, AutoCAD)
  in real Windows through WinBoat.
- **Mac apps**: finds the Linux version or a close equivalent.

**Safe and private**
- No telemetry and no accounts. **Security Check** audits the firewall, encryption, updates,
  open ports, Secure Boot and more, and explains how to fix what it finds.

## Install

1. Download the ISO from [Releases](https://github.com/gmkovalik/Credo-OS/releases) and check its
   SHA-256 checksum.
2. Write it to a USB stick (Fedora Media Writer, balenaEtcher or Ventoy).
3. Boot from the stick (ThinkPad: F12 at power-on) and choose **Install to Hard Drive**.
   Tick disk encryption in the installer.

## Build it yourself

On a Fedora machine with SELinux enabled (a public build refuses WSL or containers):

```sh
CREDO_PUBLIC=1 sudo ./build/build.sh --out out/release
bash tools/fetch_sources.sh out/release/Credo-OS-45-x86_64.iso.packages.tsv out/release/sources
```

On an installed Credo OS you can also use **Make Credo ISO** (installer: `dist/ISO-Builder.sh`
from a release), which builds an ISO of the Credo version on that computer into Downloads.

| Folder | What |
|--------|------|
| `kickstart/` | The system recipe: packages and setup (`credo-os.ks`, `packages.ks`, `post.ks`) |
| `overlay/` | Credo's own files, copied into the system (apps in `usr/lib/credo`, widgets, theme…) |
| `build/` | `build.sh` (livemedia-creator) and the Windows/WSL wrapper |
| `tools/` | Generators for logos, icons, themes, saints' lives, updates and source downloads |
| `docs/` | [Compliance](docs/COMPLIANCE.md) and [distribution plan](docs/DISTRIBUTION.md) |
| `design/` | Design mockups and previews |

## Licence and source code

Credo OS's own code is free software under the **GNU GPL, version 3 or later** ([LICENSE](LICENSE)).
Every other component keeps its own licence: see [NOTICE.txt](NOTICE.txt) and
[CREDITS.md](CREDITS.md). Each release lists the licence of every package and publishes the
corresponding source code.

*Ad maiorem Dei gloriam.*
