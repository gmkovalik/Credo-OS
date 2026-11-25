"""Turn the 'Church Wallpapers' folder into KDE wallpaper packages for PERSONAL builds only.

The photos come from the churches' own websites for personal use; public builds (CREDO_PUBLIC=1)
never include them. Output: personal-wallpapers/packages/<Id>/{metadata.json,contents/images/WxH.jpg}

    python tools/make_personal_wallpapers.py ["path/to/Church Wallpapers"]
"""
import json
import pathlib
import re
import shutil
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "Church Wallpapers"
OUT = ROOT / "personal-wallpapers" / "packages"
SOURCES = {"FSSP - All Saints, Minneapolis": "fsspminneapolis.org",
           "Vatican - St Peter's Basilica": "basilicasanpietro.va",
           "Italy - Basilica of St Francis, Assisi": "basilica.sanfrancesco.org",
           "Italy - Montecassino Abbey": "abbaziamontecassino.it",
           "Italy - St Mark's Basilica, Venice": "basilicasanmarco.it",
           "Italy - Milan Cathedral": "duomomilano.it"}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    n = 0
    for folder in sorted(p for p in SRC.iterdir() if p.is_dir()):
        place = folder.name.split(" - ", 1)[-1]
        for img in sorted(folder.glob("*.jpg")):
            words = img.stem.replace("-", " ").replace("fssp", "FSSP").strip()
            name = f"{place}: {words[:1].upper() + words[1:]}"
            pid = "Credo-" + re.sub(r"[^A-Za-z0-9]+", "-", f"{place}-{img.stem}").strip("-")
            with Image.open(img) as im:
                w, h = im.size
            d = OUT / pid / "contents" / "images"
            d.mkdir(parents=True)
            shutil.copy(img, d / f"{w}x{h}.jpg")
            meta = {"KPlugin": {"Id": pid, "Name": name,
                                "Description": f"Photo: {SOURCES.get(folder.name, place)} (personal use)",
                                "Authors": [{"Name": SOURCES.get(folder.name, place)}]}}
            (OUT / pid / "metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
            n += 1
    print(f"{n} wallpaper packages in {OUT}")


if __name__ == "__main__":
    main()
