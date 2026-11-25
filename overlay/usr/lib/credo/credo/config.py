"""Per-user settings (~/.config/credo/credo.conf) layered over /etc/credo/defaults.conf."""
import configparser
import os
import pathlib

HOME = pathlib.Path.home()
CONF_DIR = pathlib.Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config") / "credo"
DATA_DIR = pathlib.Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share") / "credo"
CONF = CONF_DIR / "credo.conf"
SYSTEM_DEFAULTS = pathlib.Path("/etc/credo/defaults.conf")
SHARE = pathlib.Path(os.environ.get("CREDO_SHARE", "/usr/share/credo"))
if not SHARE.exists():  # running from the source tree
    SHARE = pathlib.Path(__file__).resolve().parents[3] / "share" / "credo"

DEFAULTS = {
    "general": {"language": "en", "first_run": "true"},
    "appearance": {
        "variant": "liturgical",
        "logo": "chirho",
        "panel_position": "bottom",
        "panel_height": "44",
        "panel_floating": "true",
        "wallpaper": "true",
        "motto": "true",
    },
    "library": {"port": "8754"},
}


def load():
    cp = configparser.ConfigParser()
    cp.read_dict(DEFAULTS)
    cp.read([SYSTEM_DEFAULTS, CONF])
    return cp


def save(cp):
    CONF_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONF.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        cp.write(f)
    tmp.replace(CONF)


def language():
    lang = load().get("general", "language", fallback="en")
    return lang if lang in ("en", "la") else "en"


def set_value(section, key, value):
    cp = load()
    if not cp.has_section(section):
        cp.add_section(section)
    cp.set(section, key, str(value))
    save(cp)
