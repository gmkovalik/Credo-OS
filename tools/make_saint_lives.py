"""Build overlay/usr/share/credo/saint-lives.json: each saint's life as read at Matins (the lessons
of the 2nd nocturn, Lectio 4-6, of the Roman Breviary) in Latin and English, from the Divinum
Officium project's Breviary files. Shipped with Credo so the Today page can show it offline.

    python tools/make_saint_lives.py [PATH/TO/divinum-officium]   (downloads the files if no path)
"""
import io
import json
import pathlib
import re
import sys
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "overlay/usr/share/credo/saint-lives.json"
TARBALL = "https://github.com/DivinumOfficium/divinum-officium/archive/HEAD.tar.gz"
LANGS = {"la": "Latin", "en": "English"}
SEC = re.compile(r"^\[([^\]]+)\]\s*(\(.*\))?\s*$")


def fetch():
    """{(lang_dir, 'Sancti/MM-DD'): text} for the Breviary's Sancti (and Commune) files."""
    files = {}
    req = urllib.request.Request(TARBALL, headers={"User-Agent": "Credo-OS-build"})
    with urllib.request.urlopen(req, timeout=300) as r, tarfile.open(fileobj=r, mode="r|gz") as tar:
        for m in tar:
            parts = m.name.split("/")
            # <repo>-<sha>/web/www/horas/<Lang>/<Sancti|Commune>/<file>.txt
            if (m.isfile() and len(parts) == 7 and parts[1:4] == ["web", "www", "horas"]
                    and parts[4] in LANGS.values() and parts[5] in ("Sancti", "Commune")
                    and parts[6].endswith(".txt")):
                files[(parts[4], f"{parts[5]}/{parts[6][:-4]}")] = tar.extractfile(m).read().decode("utf-8", "replace")
    return files


def sections(text):
    """{name: lines}; the plain (Divino Afflatu / 1954) form wins over later-rubric variants."""
    out, cur, plain = {}, None, set()
    for line in text.splitlines():
        m = SEC.match(line.strip())
        if m:
            name, note = m.group(1).strip(), m.group(2) or ""
            later = re.search(r"1955|1960|196[0-9]|Monastic|Ordo Praedicatorum|Cist", note)
            if later or (note and name in plain):
                cur = None                              # skip variants for later rubrics
                continue
            cur = name
            out[cur] = []
            if not note:
                plain.add(name)
            continue
        if cur is not None:
            out[cur].append(line)
    return out


def resolve(files, lang, ref, name, depth=0):
    """Text lines of one section, following Divinum Officium's @-references."""
    text = files.get((lang, ref))
    if text is None or depth > 4:
        return []
    secs = sections(text)
    lines = secs.get(name)
    if lines is None:
        # whole-file reference at the top, e.g. "@Sancti/11-24" in [Rule] - not followed
        return []
    out = []
    for line in lines:
        s = line.strip()
        m = re.fullmatch(r"@([^:]*)(?::(.+?))?(?::.*)?", s)
        if m:
            tref = m.group(1) or ref
            tname = (m.group(2) or name).strip()
            out += resolve(files, lang, tref, tname, depth + 1)
        else:
            out.append(line)
    return out


def clean(lines):
    """Paragraphs of plain text: drop rubrics, macros and verse markers."""
    paras, buf = [], []
    for line in lines:
        s = line.strip()
        if not s:
            if buf:
                paras.append(" ".join(buf))
                buf = []
            continue
        if s[0] in "!&$#" or s.startswith(("R.", "V.", "r.", "v.")) and len(s) < 4:
            continue                                     # citations, macros, responsory markers
        s = re.sub(r"^\s*v\.\s*", "", s)
        s = s.replace("_", "").replace("~", "")
        buf.append(s)
    if buf:
        paras.append(" ".join(buf))
    return [p for p in paras if len(p) > 30]


def main():
    files = fetch()
    print(len(files), "Breviary files")
    out = {}
    for (lang_dir, ref) in sorted(files):
        if lang_dir != "Latin" or not re.fullmatch(r"Sancti/\d\d-\d\d", ref):
            continue
        day = ref.split("/")[1]
        entry = {}
        for code, ld in LANGS.items():
            paras = []
            for n in ("Lectio4", "Lectio5", "Lectio6"):
                paras += clean(resolve(files, ld, ref, n))
            if paras:
                entry[code] = paras
        if entry:
            out[day] = entry
    OUT.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"{len(out)} days -> {OUT} ({OUT.stat().st_size // 1024} KB)")
    for d in ("11-24", "12-08", "06-29"):
        e = out.get(d, {})
        print(d, "|", (e.get("en") or ["-"])[0][:140])


if __name__ == "__main__":
    main()
