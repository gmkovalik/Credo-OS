"""Import your own files (HTML, TXT, Markdown, PDF) into the library."""
import os
import pathlib
import re
import shutil
import subprocess

from . import db, netutil

EXTS = {".html", ".htm", ".txt", ".md", ".pdf"}


def read_file(p):
    ext = p.suffix.lower()
    if ext in (".html", ".htm"):
        raw = p.read_bytes().decode("utf-8", errors="replace")
        title, blocks = netutil.extract(raw)
        return title or p.stem, netutil.blocks_to_html(blocks), "\n\n".join(t for _, t in blocks)
    if ext == ".pdf":
        if not shutil.which("pdftotext"):
            raise RuntimeError("pdftotext (poppler-utils) is not installed")
        text = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True,
                              text=True, check=True).stdout
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
    return p.stem.replace("_", " "), netutil.plaintext_to_html(text), text


def run(conn, directory, collection="imported", author=None, lang="en", log=print):
    root = pathlib.Path(directory).expanduser().resolve()
    total = 0
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            p = pathlib.Path(dirpath) / f
            if p.suffix.lower() not in EXTS:
                continue
            try:
                title, body_html, body_text = read_file(p)
            except Exception as e:
                log(f"  skipped {p}: {e}")
                continue
            if len(body_text.strip()) < 50:
                continue
            a = author or (p.parent.name if p.parent != root else None)
            db.upsert(conn, collection=collection, author=a, title=re.sub(r"\s+", " ", title)[:300],
                      lang=lang, ref=None, source=p.as_uri(), body_html=body_html, body_text=body_text)
            total += 1
            if total % 50 == 0:
                conn.commit()
                log(f"  {total} files")
    conn.commit()
    log(f"Imported {total} files from {root}")
    return total
