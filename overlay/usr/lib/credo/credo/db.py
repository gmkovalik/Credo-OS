"""SQLite + FTS5 store for the Credo library (~/.local/share/credo/library.db)."""
import shutil
import sqlite3

from . import config

SEED_DB = config.SHARE / "library" / "library.db"   # optional, shipped by --with-library builds

COLLECTIONS = {
    # key: (English, Latin)
    "papal": ("Papal Documents", "Documenta Pontificia"),
    "saints": ("Writings of the Saints", "Scripta Sanctorum"),
    "missal": ("Roman Missal (1954)", "Missale Romanum (1954)"),
    "catechism": ("Roman Catechism", "Catechismus Romanus"),
    "scripture": ("Sacred Scripture", "Sacra Scriptura"),
    "imported": ("Imported", "Importata"),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(
    id INTEGER PRIMARY KEY,
    collection TEXT NOT NULL,
    author TEXT,
    title TEXT NOT NULL,
    date TEXT,
    lang TEXT,
    ref TEXT,
    source TEXT NOT NULL UNIQUE,
    body_html TEXT,
    body_text TEXT,
    added TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS docs_coll ON docs(collection, author, date);
CREATE INDEX IF NOT EXISTS docs_ref ON docs(ref, lang);
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    title, author, body_text, content='docs', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON docs BEGIN
    INSERT INTO docs_fts(rowid, title, author, body_text) VALUES (new.id, new.title, new.author, new.body_text);
END;
CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, title, author, body_text) VALUES ('delete', old.id, old.title, old.author, old.body_text);
END;
CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON docs BEGIN
    INSERT INTO docs_fts(docs_fts, rowid, title, author, body_text) VALUES ('delete', old.id, old.title, old.author, old.body_text);
    INSERT INTO docs_fts(rowid, title, author, body_text) VALUES (new.id, new.title, new.author, new.body_text);
END;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""


def path():
    return config.DATA_DIR / "library.db"


def connect():
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() and SEED_DB.exists():
        shutil.copy2(SEED_DB, p)
    conn = sqlite3.connect(p, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def upsert(conn, *, collection, title, source, body_html, body_text,
           author=None, date=None, lang=None, ref=None):
    conn.execute(
        """INSERT INTO docs(collection, author, title, date, lang, ref, source, body_html, body_text)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(source) DO UPDATE SET collection=excluded.collection, author=excluded.author,
               title=excluded.title, date=excluded.date, lang=excluded.lang, ref=excluded.ref,
               body_html=excluded.body_html, body_text=excluded.body_text""",
        (collection, author, title, date, lang, ref, source, body_html, body_text))


def has_source(conn, source):
    return conn.execute("SELECT 1 FROM docs WHERE source=?", (source,)).fetchone() is not None


def stats(conn):
    rows = conn.execute("SELECT collection, lang, COUNT(*) n FROM docs GROUP BY collection, lang").fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["collection"], {})[r["lang"] or "?"] = r["n"]
    return out


def set_meta(conn, key, value):
    conn.execute("INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, str(value)))
    conn.commit()


def get_meta(conn, key, default=None):
    r = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default
