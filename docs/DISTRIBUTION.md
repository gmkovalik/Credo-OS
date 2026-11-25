# Distributing Credo OS: plan

Credo OS today is a working personal build: an ISO (`out/v3/Credo-OS-45-x86_64.iso`, 5.5 GB), installers in
`dist/` (`Credo-Update.sh`, `FSSP-App.sh`, `Today-Saints.sh`, `Security-Check.sh`), and the sources in this
folder. This plan takes it from there to something other people can download, trust, and keep updated.

The order matters: **phase 1 is required before anyone else gets a copy.**

---

## Phase 1. Make it legal to share (blockers)

| # | Item | Why | What to do |
|---|------|-----|------------|
| 1 | **Fedora trademarks** | The ISO still ships Fedora's `fedora-logos` and `fedora-release` packages. Fedora lets you share a derived system only as a *Remix* with Fedora's own marks removed, and the name must not suggest it *is* Fedora. | In `kickstart/packages.ks`: add `-fedora-logos -fedora-release* -fedora-release-notes` and `generic-logos generic-release generic-release-notes`. Describe it as "Credo OS, a Fedora Remix" (allowed by the [Fedora trademark guidelines](https://docs.fedoraproject.org/ga/legal/trademarks/); see also the [Remix design guidelines](https://fedoraproject.org/wiki/Legal:Secondary_trademark_usage_guidelines)). Rebuild and check that no Fedora logo appears in boot, login or About. |
| 2 | **Apple names and looks** | "Finder" is already renamed to Files. **"Launchpad"** is also an Apple trademark, as is "Liquid Glass". | Rename Launchpad (e.g. "Apps" or "All Apps"). Don't call Credo "macOS-like" in public material; say "a calm, modern desktop". Keep our own icons (none copy Apple artwork). |
| 3 | **FSSP emblem** | The FSSP app icon is the Fraternity's coat of arms. | Ask FSSP for written permission (fssp.org / fssp.com contact) before public release; until then ship a neutral icon (keys without the arms layout) in public builds. Don't imply FSSP endorses Credo unless they say so. |
| 4 | **Chi-Rho artwork** | The Credo logo uses your Chi-Rho drawing (`tools/assets/chirho-art.svg`, from `Chi_rho.svg`). | Confirm where it came from and its licence (e.g. Wikimedia "public domain" or CC); record it in `CREDITS.md`. If unknown, redraw it. |
| 5 | **Texts and data** | Missal and Breviary texts (Mass propers, saints' lives) come from the Divinum Officium project, which is MIT-licensed ([repository](https://github.com/DivinumOfficium/divinum-officium), [credits](https://divinumofficium.com/www/horas/Help/credits.html)). Vatican documents and catechisms are downloaded by the user, not shipped. | Add `CREDITS.md` with Divinum Officium's MIT notice, Inter (SIL OFL), Breeze/KDE (GPL/LGPL), and every other bundled source. Keep downloaded content downloaded on demand. |
| 6 | **Personal wallpapers** | The St. Peter's and church photos were downloaded for **personal use only**. | Never put them in the ISO or updates. Public builds keep only Credo's own generated wallpapers. To ship church photos, ask each church in writing (many will say yes). |
| 7 | **Credo's own licence** | Others need permission to use and share Credo's code. | Add a `LICENSE` (GPL-3.0-or-later fits a Linux distribution; MIT is simpler). Put a short header in each source file. |
| 8 | **Name check** | "Credo" is used by other companies. | Search USPTO/EUIPO for "Credo OS" in software classes. If it conflicts, choose a variant (e.g. "Credo Linux", "Credo Catholic OS"). Register the domain you'll use. |
| 9 | **Church disclaimer** | People may assume Church approval. | On the website and in About: "Credo OS is an independent project. It is not an official product of the Catholic Church or any religious order." |

## Phase 2. Make it trustworthy

- **Signed releases:** publish `SHA256SUMS` for every ISO and sign it (GPG or minisign). Put the public key on the website and in the README.
- **Security baseline (checked by `credo-security-check`):** SELinux enforcing, firewall on with nothing open, disk encryption on by default in the installer, Secure Boot working (Fedora's signed shim and kernel are used unchanged), automatic security updates, root locked, screen lock on.
  - Run `sudo credo-security-check --html report.html` on a fresh install of every release, and publish the report.
- **Reproducible builds:** the build already runs from a kickstart (`build/build.sh`). Pin the Fedora release, keep the build log, and record the package list (`rpm -qa`) for each ISO.
- **Privacy:** no telemetry, no accounts. Write it down in a one-page privacy statement.
- **Testing before each release:**
  - Boot and install in a VM (UEFI and Secure Boot) and on the ThinkPad X1 Carbon Gen 11.
  - Check the installer (with encryption), update path, Latin, the light theme, the dock, Launchpad, Credo Center, Browser, Console, Today and FSSP.

## Phase 3. Updates the normal way (replace `Credo-Update.sh`)

The `.sh` updater works for one laptop, but public users need updates through the normal software tools.

1. **Package Credo as RPMs**:
   - `credo-desktop`: plasmoids, theme, look-and-feel, icons.
   - `credo-apps`: Center, Browser, Console, Launchpad, FSSP, Security Check.
   - `credo-library`: library server, saints' lives, calendar.
   - `credo-release`: branding, `/etc/os-release`, repository file.
   - Each needs a `.spec` file.
2. **Host them on Fedora COPR** (free build and hosting for Fedora packages). `credo-release` installs the COPR repository file, so Discover and `dnf` bring Credo updates together with Fedora updates.
3. **Per-user changes** (panels, Plasma settings) go in `/etc/xdg` defaults plus a small one-time "migration" script run at login. It runs once per version and **never rebuilds the user's panels** (the lesson from the widget reset).
4. **Version scheme:** `Credo OS 45.1`, `45.2`, … following the Fedora base. Move to each new Fedora release about a month after it comes out; Fedora supports each release for about 13 months.

## Phase 4. Hosting and download

- **ISO hosting:** the ISO (about 5.5 GB) is too big for a single GitHub release file (2 GB limit). Use one of:
  - **SourceForge**: free for open-source projects, worldwide mirrors, download counts.
  - **Internet Archive (archive.org)**: free and permanent.
  - **Cloudflare R2 or Backblaze B2** behind your own domain: cheap, no download fees on R2.
  - Also publish a **torrent** (magnet link) to share load.
- **Shrinking the ISO (optional):** use a live image without the offline installer extras, and make large apps (Calibre, MuseScore, LilyPond, BibleTime) optional installs in Credo Center. A smaller ISO would fit GitHub (under 2 GB per file) or a 4 GB USB stick.
- **Source code:** a public Git repository (GitHub or Codeberg) with the kickstarts, overlay, tools, `LICENSE`, `CREDITS.md`, build instructions and issue tracker.
- **Website** (a simple static site, e.g. GitHub Pages or Codeberg Pages):
  - home with screenshots
  - download page with checksums and signature
  - how to make a USB stick (Fedora Media Writer, balenaEtcher, Ventoy)
  - install guide, FAQ, privacy statement, disclaimer, donation link

## Phase 5. Launch and community

1. **Private beta:**
   - 5–10 people (family, parish friends) on different laptops.
   - Collect problems through the issue tracker or a simple form.
   - Fix the top issues.
2. **Public 1.0:**
   - Announce on the website, r/Fedora and r/Catholicism (respecting their self-promotion rules), and Catholic tech communities.
   - Contact Catholic schools and homeschool groups, who may value a free, distraction-free study computer.
3. **Ongoing:**
   - **Help:** a place for questions, e.g. a Matrix room or Discourse forum.
   - **Releases:** a release every Fedora cycle, with release notes.
   - **Support costs:** donations (Liberapay, Open Collective) for hosting.
4. **Partnerships:** ask FSSP, dioceses or Catholic publishers before naming them. With permission they can contribute wallpapers, texts or apps.

## Checklist summary

- [ ] Remove Fedora logos/release packages; label as "a Fedora Remix"
- [ ] Rename Launchpad; drop "macOS" wording
- [ ] FSSP permission or neutral icon
- [ ] Chi-Rho artwork licence confirmed
- [ ] `LICENSE` + `CREDITS.md`; personal wallpapers excluded
- [ ] Name/trademark search; domain
- [ ] Signed checksums; security-check report per release
- [ ] RPM packages on COPR; login migration instead of panel rebuilds
- [ ] Hosting (SourceForge/archive.org/R2) + torrent; website
- [ ] Private beta, then public 1.0
