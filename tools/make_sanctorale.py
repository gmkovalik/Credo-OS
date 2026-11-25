"""Build overlay/usr/share/credo/sanctorale.json: the feast of each calendar day (Proper of the
Saints, Latin and English) from the Divinum Officium Missal data, so the Today widget and
page can name the saint without the Missal being downloaded.

    python tools/make_sanctorale.py PATH/TO/divinum-officium/web/www/missa
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "overlay/usr/lib/credo"))
from credo.fetch_missal import Missal  # noqa: E402

OUT = ROOT / "overlay/usr/share/credo/sanctorale.json"


def main(root):
    m = Missal(root)
    out = {}
    for p in sorted((pathlib.Path(root) / "Latin" / "Sancti").glob("*.txt")):
        if not re.fullmatch(r"\d\d-\d\d", p.stem):
            continue                                  # skip variants like 01-14t, 05-01c
        ref = f"Sancti/{p.stem}"
        la, en = m.title("Latin", ref), m.title("English", ref)
        if la and la != ref:
            out[p.stem] = {"la": la, "en": en if en and en != ref else la}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    print(f"{len(out)} days -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
