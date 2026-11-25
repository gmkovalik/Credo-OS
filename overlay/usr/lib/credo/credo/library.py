"""credo-library: Catholic offline library.

  credo-library open [PATH]            start the local server if needed and open the browser
  credo-library serve [--port N]       run the server in the foreground
  credo-library fetch all|papal|saints|missal|catechism [--limit N] [--id ARCHIVE_ID]
  credo-library import DIR [--collection imported] [--author NAME] [--lang en]
  credo-library stats
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.request

from . import config, db


def port():
    return config.load().getint("library", "port", fallback=8754)


def running(p):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{p}/health", timeout=1) as r:
            return r.read() == b"ok"
    except Exception:
        return False


def cmd_open(path="/"):
    p = port()
    if not running(p):
        env = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        subprocess.Popen([sys.executable, "-m", "credo.library", "serve", "--port", str(p)],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        for _ in range(50):
            if running(p):
                break
            time.sleep(0.1)
    url = f"http://127.0.0.1:{p}{path if path.startswith('/') else '/' + path}"
    import shutil
    opener = ["credo-browser", url] if shutil.which("credo-browser") else ["xdg-open", url]
    subprocess.Popen(opener, start_new_session=True)
    print(url)


def cmd_fetch(what, limit=None, identifier=None):
    conn = db.connect()
    from . import fetch_catechism, fetch_gutenberg, fetch_missal, fetch_vatican
    order = ["missal", "catechism", "papal", "saints"] if what == "all" else [what]
    for w in order:
        try:
            if w == "missal":
                fetch_missal.run(conn)
            elif w == "catechism":
                fetch_catechism.run(conn, identifier)
            elif w == "papal":
                fetch_vatican.run(conn)
            elif w == "saints":
                fetch_gutenberg.run(conn, limit)
            db.set_meta(conn, f"fetched_{w}", time.strftime("%Y-%m-%d %H:%M"))
        except KeyboardInterrupt:
            conn.commit()
            print("\nStopped; everything downloaded so far is saved. Run again to resume.")
            return 1
        except Exception as e:
            conn.commit()
            print(f"{w}: failed: {e}", file=sys.stderr)
    conn.execute("INSERT INTO docs_fts(docs_fts) VALUES('optimize')")
    conn.commit()
    cmd_stats()


def cmd_stats():
    conn = db.connect()
    st = db.stats(conn)
    if not st:
        print("Library is empty.")
    for k, (en, _) in db.COLLECTIONS.items():
        if k in st:
            parts = ", ".join(f"{l}: {n}" for l, n in sorted(st[k].items()))
            print(f"{en:28} {parts}")
    print(f"Database: {db.path()}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="credo-library", description="Credo OS Catholic library")
    sub = ap.add_subparsers(dest="cmd")
    o = sub.add_parser("open"); o.add_argument("path", nargs="?", default="/")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int)
    f = sub.add_parser("fetch")
    f.add_argument("what", choices=["all", "papal", "saints", "missal", "catechism"])
    f.add_argument("--limit", type=int, help="max books for 'saints'")
    f.add_argument("--id", help="archive.org identifier for 'catechism'")
    i = sub.add_parser("import"); i.add_argument("directory")
    i.add_argument("--collection", default="imported", choices=list(db.COLLECTIONS))
    i.add_argument("--author"); i.add_argument("--lang", default="en", choices=["en", "la"])
    sub.add_parser("stats")
    a = ap.parse_args(argv)

    if a.cmd == "open":
        return cmd_open(a.path)
    if a.cmd == "serve":
        from . import server
        return server.serve(a.port or port())
    if a.cmd == "fetch":
        return cmd_fetch(a.what, a.limit, a.id)
    if a.cmd == "import":
        from . import importer
        return importer.run(db.connect(), a.directory, a.collection, a.author, a.lang)
    if a.cmd == "stats":
        return cmd_stats()
    ap.print_help()


if __name__ == "__main__":
    sys.exit(main())
