"""Roman Missal propers (Latin + English) from the Divinum Officium project data.

Divinum Officium (github.com/DivinumOfficium/divinum-officium) keeps every Mass of
the traditional Missal as plain-text files. We fetch only web/www/missa with a sparse
git clone, resolve its @-references, keep the pre-1955 (Divino Afflatu) form of
each section, and store one rendered document per Mass per language.
"""
import html
import pathlib
import re
import subprocess

from . import config, db

REPO = "https://github.com/DivinumOfficium/divinum-officium.git"
TARBALL = "https://github.com/DivinumOfficium/divinum-officium/archive/HEAD.tar.gz"
SUBDIR = "web/www/missa"
# The Mass texts of the Commons (C1…C11) are kept with the Office files.
COMMUNE_DIRS = ["web/www/horas/Latin/Commune", "web/www/horas/English/Commune"]
PATHS = [SUBDIR] + COMMUNE_DIRS
LANGS = {"la": "Latin", "en": "English"}
ORDER = ["Introitus", "Oratio", "Commemoratio Oratio", "Lectio", "Graduale", "Tractus",
         "Sequentia", "Evangelium", "Offertorium", "Secreta", "Commemoratio Secreta",
         "Prefatio", "Communio", "Postcommunio", "Commemoratio Postcommunio"]
SECTION_EN = {"Introitus": "Introit", "Oratio": "Collect", "Lectio": "Epistle", "Graduale": "Gradual",
              "Tractus": "Tract", "Sequentia": "Sequence", "Evangelium": "Gospel",
              "Offertorium": "Offertory", "Secreta": "Secret", "Prefatio": "Preface",
              "Communio": "Communion", "Postcommunio": "Postcommunion",
              "Commemoratio Oratio": "Commemoration (Collect)",
              "Commemoratio Secreta": "Commemoration (Secret)",
              "Commemoratio Postcommunio": "Commemoration (Postcommunion)"}
MACROS = {"Per Dominum": "Per Dominum nostrum Jesum Christum…", "Per eumdem": "Per eumdem Dominum…",
          "Qui vivis": "Qui vivis et regnas…", "Qui tecum": "Qui tecum vivit et regnat…",
          "Gloria": "Gloria Patri, et Filio, et Spiritui Sancto…", "Oremus": "Oremus."}
TRACT_NOTE = {"en": "After Septuagesima, the Alleluia and its verse are omitted and the Tract is said:",
              "la": "Post Septuagesimam, omissis Allelúja et versu sequenti, dicitur Tractus:"}
SEC_RE =re.compile(r"^\[([^\]]+)\]\s*(\(.*\))?\s*$")


def source_dir():
    return config.DATA_DIR / "sources" / "divinum-officium"


def sync_tarball(d, log=print):
    """No git: stream the GitHub archive and keep only SUBDIR (stdlib only)."""
    import shutil
    import tarfile
    import urllib.request
    from . import netutil
    log("Missal: git not found; downloading the Divinum Officium archive instead")
    tmp = d.with_name(d.name + ".partial")
    shutil.rmtree(tmp, ignore_errors=True)
    req = urllib.request.Request(TARBALL, headers={"User-Agent": netutil.USER_AGENT})
    n = 0
    with urllib.request.urlopen(req, timeout=120) as r, tarfile.open(fileobj=r, mode="r|gz") as tar:
        for member in tar:
            parts = member.name.split("/", 1)          # strip "<repo>-<sha>/"
            if len(parts) < 2 or not member.isfile() or not any(parts[1].startswith(p + "/") for p in PATHS):
                continue
            rel = pathlib.PurePosixPath(parts[1])
            if ".." in rel.parts:
                continue
            dest = tmp.joinpath(*rel.parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            n += 1
            if n % 2000 == 0:
                log(f"  {n} files")
    if not n:
        raise RuntimeError("archive contained no Missal files")
    shutil.rmtree(d, ignore_errors=True)
    tmp.rename(d)
    log(f"  {n} files")


def sync(log=print):
    import shutil
    d = source_dir()
    if not shutil.which("git"):
        if not all((d / p).is_dir() for p in [SUBDIR + "/Latin"] + COMMUNE_DIRS):
            d.parent.mkdir(parents=True, exist_ok=True)
            sync_tarball(d, log)
        else:
            log("Missal: using downloaded Divinum Officium data")
        return d / SUBDIR
    if (d / ".git").exists():
        log("Missal: updating Divinum Officium data")
        subprocess.run(["git", "-C", str(d), "sparse-checkout", "set", *PATHS], check=False)
        subprocess.run(["git", "-C", str(d), "pull", "--ff-only", "--depth", "1"], check=False)
    else:
        log("Missal: downloading Divinum Officium data (sparse clone, about 100 MB)")
        shutil.rmtree(d, ignore_errors=True)          # e.g. an earlier archive download
        d.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(d)], check=True)
        subprocess.run(["git", "-C", str(d), "sparse-checkout", "set", *PATHS], check=True)
    return d / SUBDIR


class Missal:
    def __init__(self, root):
        self.root = pathlib.Path(root)                 # .../web/www/missa
        self.horas = self.root.parent / "horas"
        self._cache = {}

    def find(self, lang_dir, ref):
        path = self.root / lang_dir / f"{ref}.txt"
        if not path.exists() and ref.startswith("Commune/"):
            alt = self.horas / lang_dir / f"{ref}.txt"
            if alt.exists():
                return alt
        return path

    def load(self, lang_dir, ref):
        key = (lang_dir, ref)
        if key in self._cache:
            return self._cache[key]
        path = self.find(lang_dir, ref)
        if not path.exists() and lang_dir != "Latin":
            return self.load("Latin", ref)
        sections = {}
        if path.exists():
            cur = "__pre__"
            skipping = False
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                m = SEC_RE.match(line.strip())
                if m:
                    name, cond = m.group(1).strip(), m.group(2)
                    # A conditional duplicate like "[Oratio] (rubrica 1960)" is a later variant:
                    # keep the plain (pre-1955) section when both exist.
                    skipping = bool(cond) and name in sections
                    cur = name
                    if not skipping:
                        sections[cur] = []
                    continue
                if not skipping:
                    sections.setdefault(cur, []).append(line.rstrip())
        self._cache[key] = sections
        return sections

    def commune_fallback(self, sections, ref):
        """'vide C4a' -> Commune/C4a; 'vide Quadp1-0' -> same folder; 'ex Sancti/12-25' as is."""
        rule = "\n".join(sections.get("Rule", []))
        m = re.search(r"(?:vide|ex)\s+([A-Za-z][\w/-]*)", rule)
        if not m:
            return None
        t = m.group(1)
        if "/" in t:
            return t
        if re.match(r"C\d", t):
            return f"Commune/{t}"
        return f"{ref.split('/')[0]}/{t}"

    def redirect(self, sections, ref):
        pre = [l for l in sections.get("__pre__", []) if l.startswith("@")]
        return pre[0][1:].split(":")[0] if pre else self.commune_fallback(sections, ref)

    def section(self, lang_dir, ref, name, depth=0):
        if depth > 6:
            return []
        secs = self.load(lang_dir, ref)
        lines = secs.get(name)
        if lines is None and lang_dir != "Latin":
            # Translations often leave the @-references to the Latin file:
            # follow the Latin structure, but read the targets in this language.
            latin = self.load("Latin", ref).get(name)
            if latin and all(l.startswith("@") or not l.strip() for l in latin):
                lines = latin
        if lines is None:
            target = self.redirect(secs, ref)
            if not target and lang_dir != "Latin":
                target = self.redirect(self.load("Latin", ref), ref)
            if target == ref:
                target = None
            if target:
                return self.section(lang_dir, target, name, depth + 1)
            return []
        out = []
        for line in lines:
            if line.startswith("@"):
                spec = line[1:].split(":")
                tref = spec[0] or ref
                tsec = spec[1] if len(spec) > 1 and spec[1] else name
                out.extend(self.section(lang_dir, tref, tsec, depth + 1))
            else:
                out.append(line)
        return out

    def title(self, lang_dir, ref):
        secs = self.load(lang_dir, ref)
        for key in ("Officium", "Rank"):
            for line in secs.get(key, []):
                if line.strip():
                    return line.split(";;")[0].strip()
        return ref

    def render(self, lang_dir, ref, lang):
        parts = []
        lenten = re.match(r"Tempora/(Quadp|Quad)", ref)
        for sec in ORDER:
            if sec == "Tractus" and ref.startswith("Tempora/") and not lenten:
                continue                       # no Tract outside Septuagesima–Holy Week
            lines = self.section(lang_dir, ref, sec)
            body = render_lines(lines)
            if body:
                label = SECTION_EN.get(sec, sec) if lang == "en" else sec
                if sec == "Tractus" and not lenten:
                    body = (f'<p class="rubric">{html.escape(TRACT_NOTE[lang])}</p>' + body)
                parts.append((sec, f'<section class="mass-part"><h3>{html.escape(label)}</h3>{body}</section>'))
        return parts


def render_lines(lines):
    out = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("(") and line.endswith(")"):
            continue                                         # rubrical conditions
        if line == "_":
            out.append("<hr>")
            continue
        line = line.replace("+", "✠").replace("~", "")
        if line.startswith("!"):
            out.append(f'<p class="cit">{html.escape(line[1:].strip())}</p>')
        elif line[0] in "$&":
            key = line[1:].strip()
            out.append(f'<p class="macro">{html.escape(MACROS.get(key, key))}</p>')
        elif re.match(r"^[VR]\.\s", line):
            sym = "℣." if line[0] == "V" else "℟."
            out.append(f'<p class="vr">{sym} {html.escape(line[3:])}</p>')
        elif line.startswith("v. "):
            out.append(f"<p>{html.escape(line[3:])}</p>")
        else:
            out.append(f"<p>{html.escape(line)}</p>")
    return "\n".join(out)


def all_refs(root):
    refs = []
    latin = pathlib.Path(root) / "Latin"
    for sub in ("Tempora", "Sancti", "Commune", "Votive"):
        d = latin / sub
        if d.is_dir():
            refs += [f"{sub}/{p.stem}" for p in sorted(d.glob("*.txt"))]
    return refs


def ingest(conn, root, log=print):
    m = Missal(root)
    total = 0
    for ref in all_refs(root):
        before = total
        for lang, lang_dir in LANGS.items():
            parts = m.render(lang_dir, ref, lang)
            if not parts:
                continue
            body = "\n".join(h for _, h in parts)
            text = re.sub(r"<[^>]+>", " ", body)
            title = m.title(lang_dir, ref)
            db.upsert(conn, collection="missal", author="Missale Romanum", title=title,
                      date=None, lang=lang, ref=ref, source=f"do:{lang}:{ref}",
                      body_html=body, body_text=html.unescape(text))
            total += 1
        if total // 200 > before // 200:
            conn.commit()
            log(f"  {total} Masses")
    # Ordinary of the Mass
    for lang, lang_dir in LANGS.items():
        p = pathlib.Path(root) / lang_dir / "Ordo" / "Ordo.txt"
        if p.exists():
            secs = m.load(lang_dir, "Ordo/Ordo")
            body = "\n".join(f"<section class='mass-part'><h3>{html.escape(k)}</h3>{render_lines(v)}</section>"
                             for k, v in secs.items() if k != "__pre__")
            db.upsert(conn, collection="missal", author="Missale Romanum",
                      title="Ordo Missae" if lang == "la" else "Ordinary of the Mass",
                      lang=lang, ref="Ordo/Ordo", source=f"do:{lang}:Ordo/Ordo", body_html=body,
                      body_text=html.unescape(re.sub(r"<[^>]+>", " ", body)))
    conn.commit()
    log(f"Missal: {total} Mass propers stored")
    return total


def run(conn, log=print):
    root = sync(log)
    return ingest(conn, root, log)
