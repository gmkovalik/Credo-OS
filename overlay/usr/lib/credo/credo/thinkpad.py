"""Read-only ThinkPad status (battery health, thresholds, fan, temperatures, power profile)."""
import configparser
import pathlib
import shutil
import subprocess

PS = pathlib.Path("/sys/class/power_supply")
CONF = pathlib.Path("/etc/credo/thinkpad.conf")


def _read(p, default=None):
    try:
        return pathlib.Path(p).read_text().strip()
    except OSError:
        return default


def battery():
    bats = sorted(PS.glob("BAT*"))
    if not bats:
        return None
    b = bats[0]
    full = _read(b / "energy_full") or _read(b / "charge_full")
    design = _read(b / "energy_full_design") or _read(b / "charge_full_design")
    health = round(100 * int(full) / int(design), 1) if full and design and int(design) else None
    return {
        "name": b.name,
        "capacity": _read(b / "capacity"),
        "status": _read(b / "status"),
        "cycles": _read(b / "cycle_count"),
        "health": health,
        "start": _read(b / "charge_control_start_threshold"),
        "stop": _read(b / "charge_control_end_threshold"),
        "model": _read(b / "model_name"),
        "thresholds_supported": (b / "charge_control_end_threshold").exists(),
    }


def fan():
    t = _read("/proc/acpi/ibm/fan", "")
    info = dict(line.split(":", 1) for line in t.splitlines() if ":" in line)
    return {k.strip(): v.strip() for k, v in info.items()}


def temperatures():
    out = []
    for hw in pathlib.Path("/sys/class/hwmon").glob("hwmon*"):
        name = _read(hw / "name", hw.name)
        for t in sorted(hw.glob("temp*_input")):
            v = _read(t)
            label = _read(str(t).replace("_input", "_label"), t.stem)
            if v and v.lstrip("-").isdigit() and int(v) > 0:
                out.append((f"{name} {label}", int(v) / 1000))
    return out


def power_profile():
    if shutil.which("powerprofilesctl"):
        r = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True)
        return r.stdout.strip() or None
    return None


def set_power_profile(profile):
    return subprocess.run(["powerprofilesctl", "set", profile], capture_output=True, text=True).returncode == 0


def configured_thresholds():
    cp = configparser.ConfigParser()
    cp.read(CONF)
    s = cp["battery"] if cp.has_section("battery") else {}
    return (s.get("enabled", "true") == "true", int(s.get("start", 75)), int(s.get("stop", 90)))


def product():
    return " ".join(filter(None, (_read("/sys/class/dmi/id/sys_vendor"),
                                  _read("/sys/class/dmi/id/product_version"))))
