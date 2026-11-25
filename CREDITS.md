# Credo OS credits

Credo OS is built from Fedora Linux packages (each under its own licence; see
`package-licenses.tsv`) plus the original work and third-party content below.

## Original to Credo OS (GPL-3.0-or-later)

- Credo apps: Credo Center, Credo Browser, Credo Console, Apps (app grid), Welcome, FSSP reader,
  Security Check, Catholic Library server, liturgical calendar, devotions.
- Credo Plasma widgets (menu, dock, app name, liturgical day, Today, Rosary, Roman clock), the Credo
  Plasma style, icon themes, window decoration, GTK themes, colour schemes and generated wallpapers.
- Build scripts and kickstarts (`build/`, `kickstart/`, `tools/`).
- Artwork: the Chi-Rho logo and its variants, drawn by the Credo OS author (original work).

## Third-party content shipped in Credo OS

| What | Where | Source | Licence |
|------|-------|--------|---------|
| Missal propers (1954), Breviary lessons (saints' lives), the saints' calendar | `/usr/share/credo/saint-lives.json`, `/usr/share/credo/sanctorale.json`; Missal downloaded on request | Divinum Officium project, <https://github.com/DivinumOfficium/divinum-officium> | MIT (`licenses/Divinum-Officium-MIT.txt`) |
| Inter typeface | Fedora package `rsms-inter-fonts` | Rasmus Andersson | SIL Open Font License 1.1 |
| Breeze widgets, icons, cursors (fallbacks) | Fedora KDE packages | KDE e.V. | GPL / LGPL |
| Qt, PySide6, Qt WebEngine | Fedora packages | The Qt Company, Chromium authors | LGPL-3.0 / GPL; Chromium BSD |
| pyte (terminal emulation) | Fedora package `python3-pyte` | pyte authors | LGPL-3.0 |
| *(not included)* FSSP app and emblem | installed separately (FSSP-App.sh) | Priestly Fraternity of St. Peter | Not part of Credo OS |

## Downloaded on request (not shipped)

These are fetched by the user's own computer when asked, under their publishers' terms:
Vatican documents (vatican.va), catechisms, Project Gutenberg books, the full Divinum Officium Missal,
Bottles, WinBoat, Darling, Flathub apps and RPM Fusion (if enabled).

Personal wallpapers (photos from vatican.va, basilicasanpietro.va, parish and cathedral sites) are
**not** part of Credo OS; they were collected for personal use only.
