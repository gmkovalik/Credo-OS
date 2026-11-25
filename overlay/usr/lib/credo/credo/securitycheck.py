"""Credo Security Check: audits this Credo OS computer and explains how to fix what it finds.

It only reads the system (nothing is changed). Some checks need administrator rights; run
"sudo credo-security-check" for the full audit.

    credo-security-check                 checks, coloured summary in the terminal
    credo-security-check --html FILE     also write an HTML report
    credo-security-check --quick         skip the slow online checks (updates, firmware)
"""
import argparse
import datetime as dt
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

PASS, WARN, FAIL, INFO = "pass", "warn", "fail", "info"
ROOT = os.geteuid() == 0 if hasattr(os, "geteuid") else False


def run(*cmd, timeout=60):
    """(exit code, output) of a command, or (None, '') if it is not installed."""
    if not shutil.which(cmd[0]):
        return None, ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)


class Report:
    def __init__(self):
        self.items = []

    def add(self, area, title, status, detail, fix=""):
        self.items.append({"area": area, "title": title, "status": status, "detail": detail, "fix": fix})


# ------------------------------------------------------------------ checks
def check_selinux(r):
    code, out = run("getenforce")
    if code is None:
        return r.add("System", "SELinux", WARN, "getenforce not found.")
    if out == "Enforcing":
        r.add("System", "SELinux", PASS, "Enforcing: programs are confined by security policy.")
    else:
        r.add("System", "SELinux", FAIL, f"SELinux is {out or 'unknown'}.",
              "Set SELINUX=enforcing in /etc/selinux/config and restart.")


def check_firewall(r):
    code, out = run("firewall-cmd", "--state")
    if code is None:
        return r.add("Network", "Firewall", FAIL, "firewalld is not installed.", "sudo dnf install firewalld")
    if out != "running":
        return r.add("Network", "Firewall", FAIL, "The firewall is not running.",
                     "sudo systemctl enable --now firewalld")
    _, zone = run("firewall-cmd", "--get-default-zone")
    _, services = run("firewall-cmd", "--list-services")
    _, ports = run("firewall-cmd", "--list-ports")
    opened = f"services: {services or 'none'}" + (f"; ports: {ports}" if ports else "")
    risky = [s for s in services.split() if s in ("ssh", "samba", "vnc-server", "telnet", "ftp", "nfs", "rdp")]
    if risky:
        r.add("Network", "Firewall", WARN, f"Running (zone {zone}), but these are open to the network: "
              f"{', '.join(risky)} ({opened}).",
              "Close what you don't use: sudo firewall-cmd --permanent --remove-service=NAME && "
              "sudo firewall-cmd --reload")
    else:
        r.add("Network", "Firewall", PASS, f"Running (zone {zone}; {opened}).")


EXPECTED_PUBLIC = {"5353": "mDNS / network discovery", "1716": "KDE Connect (phone link)",
                   "546": "DHCPv6 client", "68": "DHCP client", "5355": "LLMNR (name lookup)"}


def check_listening(r):
    code, out = run("ss", "-tulnH")
    if code is None:
        return r.add("Network", "Open ports", WARN, "ss not found.")
    public, local = [], []
    for line in out.splitlines():
        cols = line.split()
        if len(cols) < 5:
            continue
        proto, addr = cols[0], cols[4]
        m = re.match(r"^(.*):(\d+)$", addr)
        if not m:
            continue
        host, port = m.group(1).strip("[]"), m.group(2)
        loopback = host.startswith("127.") or host in ("::1", "localhost") or host.endswith("%lo")
        (local if loopback else public).append((proto, host, port))
    unexpected = sorted({f"{p}/{port}" for p, h, port in public if port not in EXPECTED_PUBLIC})
    known = sorted({f"{port} ({EXPECTED_PUBLIC[port]})" for _, _, port in public if port in EXPECTED_PUBLIC})
    if unexpected:
        r.add("Network", "Open ports", WARN,
              "Listening to the network on: " + ", ".join(unexpected)
              + (f". Expected: {', '.join(known)}." if known else "."),
              "Find the program with: sudo ss -tulnp | grep PORT; stop it or keep it closed in the firewall.")
    else:
        r.add("Network", "Open ports", PASS, "Nothing unexpected is listening to the network"
              + (f" (expected: {', '.join(known)})." if known else "."))
    lib = [h for _, h, port in public if port == "8754"]
    if lib:
        r.add("Credo", "Credo Library server", FAIL, "The Credo Library (port 8754) is reachable from the network.",
              "It should listen on 127.0.0.1 only: update Credo OS.")
    elif any(port == "8754" for _, _, port in local):
        r.add("Credo", "Credo Library server", PASS, "Listening on this computer only (127.0.0.1:8754).")


def check_ssh(r):
    _, active = run("systemctl", "is-active", "sshd")
    _, enabled = run("systemctl", "is-enabled", "sshd")
    if active == "active" or enabled == "enabled":
        cfg = pathlib.Path("/etc/ssh/sshd_config")
        txt = ""
        for f in [cfg] + sorted(pathlib.Path("/etc/ssh/sshd_config.d").glob("*.conf")):
            try:
                txt += f.read_text() + "\n"
            except OSError:
                pass
        pw = re.search(r"^\s*PasswordAuthentication\s+yes", txt, re.M | re.I)
        root_login = re.search(r"^\s*PermitRootLogin\s+yes", txt, re.M | re.I)
        detail = "Remote login (SSH) is " + ("running" if active == "active" else "enabled")
        detail += "; password logins allowed" if pw else ""
        detail += "; root may log in" if root_login else ""
        r.add("Network", "Remote login (SSH)", WARN if not (pw or root_login) else FAIL, detail + ".",
              "If you don't need it: sudo systemctl disable --now sshd. Otherwise use keys only "
              "(PasswordAuthentication no, PermitRootLogin no).")
    else:
        r.add("Network", "Remote login (SSH)", PASS, "Off.")


def check_encryption(r):
    code, out = run("lsblk", "-J", "-o", "NAME,TYPE,FSTYPE,MOUNTPOINTS")
    if code is None:
        return r.add("Data", "Disk encryption", WARN, "lsblk not found.")
    try:
        tree = json.loads(out)["blockdevices"]
    except (ValueError, KeyError):
        return r.add("Data", "Disk encryption", WARN, "Could not read the disk layout.")

    def walk(nodes, under_crypt=False):
        for n in nodes:
            crypt = under_crypt or n.get("type") == "crypt" or n.get("fstype") == "crypto_LUKS"
            mps = [m for m in (n.get("mountpoints") or []) if m]
            for m in mps:
                yield m, crypt
            yield from walk(n.get("children") or [], crypt)
    mounts = dict(walk(tree))
    root_enc, home_enc = mounts.get("/"), mounts.get("/home", mounts.get("/"))
    if root_enc and home_enc:
        r.add("Data", "Disk encryption", PASS, "Your system and files are encrypted (LUKS).")
    elif home_enc:
        r.add("Data", "Disk encryption", WARN, "Your home folder is encrypted but the system is not.")
    else:
        r.add("Data", "Disk encryption", FAIL, "The disk is not encrypted: anyone with the laptop can read your files.",
              "Reinstall Credo OS with 'Encrypt my data' ticked in the installer (back up first).")


def check_secureboot(r):
    code, out = run("mokutil", "--sb-state")
    if code is None:
        efi = pathlib.Path("/sys/firmware/efi").exists()
        return r.add("Boot", "Secure Boot", INFO, "mokutil not installed; " + ("UEFI boot." if efi else "legacy BIOS boot."),
                     "sudo dnf install mokutil")
    if "enabled" in out.lower():
        r.add("Boot", "Secure Boot", PASS, "Enabled: only signed boot loaders and kernels can start.")
    else:
        r.add("Boot", "Secure Boot", WARN, out or "Disabled.",
              "Turn it on in the firmware setup (ThinkPad: F1 at power-on > Security > Secure Boot).")


def check_updates(r, quick):
    if quick:
        return r.add("Updates", "Software updates", INFO, "Skipped (--quick).")
    code, out = run("dnf", "check-update", "-q", timeout=240)
    if code is None:
        return r.add("Updates", "Software updates", WARN, "Could not run dnf.")
    if code == 100:
        n = len([l for l in out.splitlines() if l and not l.startswith((" ", "Obsoleting", "Security"))])
        r.add("Updates", "Software updates", WARN, f"About {n} updates are waiting.",
              "Open Software > Updates, or run: sudo dnf upgrade --refresh")
    elif code == 0:
        r.add("Updates", "Software updates", PASS, "Everything is up to date.")
    else:
        r.add("Updates", "Software updates", WARN, "Could not check (offline?).")
    code, out = run("needs-restarting", "-r", timeout=60)
    if code == 1:
        r.add("Updates", "Restart needed", WARN, "Updated system parts (e.g. the kernel) are not in use until you restart.",
              "Restart the computer.")


def check_firmware(r, quick):
    if quick:
        return
    code, out = run("fwupdmgr", "get-updates", "--no-unreported-check", "--json", timeout=120)
    if code is None:
        return r.add("Updates", "Firmware (BIOS, Thunderbolt…)", INFO, "fwupd not installed.", "sudo dnf install fwupd")
    try:
        devs = json.loads(out).get("Devices", [])
    except ValueError:
        devs = []
    names = [d.get("Name", "?") for d in devs if d.get("Releases")]
    if names:
        r.add("Updates", "Firmware (BIOS, Thunderbolt…)", WARN, "Firmware updates available: " + ", ".join(names) + ".",
              "Open Software > Updates, or run: fwupdmgr update")
    else:
        r.add("Updates", "Firmware (BIOS, Thunderbolt…)", PASS, "No firmware updates waiting.")


def check_accounts(r):
    code, out = run("sudo", "-n", "true")
    if code == 0 and not ROOT:
        r.add("Accounts", "Administrator password", WARN,
              "sudo works without asking for your password (or it was entered a moment ago).",
              "Remove any NOPASSWD line from /etc/sudoers and /etc/sudoers.d/*.")
    else:
        r.add("Accounts", "Administrator password", PASS, "Administrator actions ask for your password.")
    if ROOT:
        _, st = run("passwd", "-S", "root")
        if re.search(r"\b(L|LK|NP)\b", st):
            r.add("Accounts", "Root account", PASS, "Locked (no direct root login).")
        else:
            r.add("Accounts", "Root account", WARN, "Root has a password and can log in directly.",
                  "sudo passwd -l root")
    try:
        groups = subprocess.run(["id", "-nG"], capture_output=True, text=True).stdout.split()
    except OSError:
        groups = []
    if "docker" in groups:
        r.add("Accounts", "Docker group (WinBoat)", WARN,
              "Your account is in the 'docker' group, which can gain full administrator rights without a password.",
              "Keep it only while you use WinBoat; remove with: sudo gpasswd -d $USER docker")


def check_screenlock(r):
    kr = shutil.which("kreadconfig6") or shutil.which("kreadconfig5")
    if not kr:
        return
    auto = subprocess.run([kr, "--file", "kscreenlockerrc", "--group", "Daemon", "--key", "Autolock",
                           "--default", "true"], capture_output=True, text=True).stdout.strip()
    mins = subprocess.run([kr, "--file", "kscreenlockerrc", "--group", "Daemon", "--key", "Timeout",
                           "--default", "5"], capture_output=True, text=True).stdout.strip()
    resume = subprocess.run([kr, "--file", "kscreenlockerrc", "--group", "Daemon", "--key", "LockOnResume",
                             "--default", "true"], capture_output=True, text=True).stdout.strip()
    if auto == "false":
        r.add("Accounts", "Screen lock", FAIL, "The screen never locks by itself.",
              "System Settings > Screen Locking > Lock screen automatically.")
    elif mins.isdigit() and int(mins) > 15:
        r.add("Accounts", "Screen lock", WARN, f"The screen locks after {mins} minutes.",
              "Use 5-10 minutes in System Settings > Screen Locking.")
    else:
        r.add("Accounts", "Screen lock", PASS, f"Locks after {mins} minutes"
              + ("" if resume == "false" else " and when waking from sleep") + ".")


def check_credo_files(r):
    bad = []
    for base in ("/usr/lib/credo", "/usr/share/credo", "/usr/libexec/credo"):
        for p in pathlib.Path(base).rglob("*") if pathlib.Path(base).exists() else []:
            try:
                st = p.lstat()
            except OSError:
                continue
            if st.st_mode & 0o002 or st.st_uid != 0:
                bad.append(str(p))
    for p in pathlib.Path("/usr/bin").glob("credo-*"):
        st = p.lstat()
        if st.st_mode & 0o002 or st.st_uid != 0:
            bad.append(str(p))
    if bad:
        r.add("Credo", "Credo program files", FAIL, f"{len(bad)} Credo files can be changed by other users, e.g. "
              + ", ".join(bad[:3]) + ".", "sudo chown -R root:root /usr/lib/credo && sudo chmod -R go-w /usr/lib/credo")
    else:
        r.add("Credo", "Credo program files", PASS, "Owned by the system and not writable by other users.")


def check_browser(r):
    f = pathlib.Path.home() / ".local/share/credo/browser/settings.json"
    try:
        s = json.loads(f.read_text())
    except (OSError, ValueError):
        s = {}
    if s.get("block", True):
        r.add("Credo", "Credo Browser tracker blocking", PASS, "On: ad and tracking sites are blocked.")
    else:
        r.add("Credo", "Credo Browser tracker blocking", WARN, "Off.", "Credo Browser > Settings > Block trackers and ads.")


def check_flatpak(r):
    code, out = run("flatpak", "remotes", "--columns=name,url,options")
    if code is None:
        return
    unsafe = [l.split()[0] for l in out.splitlines() if "no-gpg-verify" in l]
    if unsafe:
        r.add("Updates", "Flatpak sources", FAIL, "Unsigned app sources: " + ", ".join(unsafe) + ".",
              "flatpak remote-modify --gpg-verify NAME (or remove it)")
    else:
        r.add("Updates", "Flatpak sources", PASS, "All app sources are signature-checked.")


CHECKS = [check_selinux, check_firewall, check_listening, check_ssh, check_encryption, check_secureboot,
          check_accounts, check_screenlock, check_credo_files, check_browser, check_flatpak]


# ------------------------------------------------------------------ output
COLOR = {PASS: "\033[32m", WARN: "\033[33m", FAIL: "\033[31m", INFO: "\033[36m"}
MARK = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL", INFO: "INFO"}


def print_report(r):
    tty = sys.stdout.isatty()
    c = (lambda s, k: f"{COLOR[k]}{s}\033[0m") if tty else (lambda s, k: s)
    print("Credo Security Check —", dt.datetime.now().strftime("%d %B %Y %H:%M"),
          "" if ROOT else "(run with sudo for the full audit)")
    area = None
    for it in r.items:
        if it["area"] != area:
            area = it["area"]
            print(f"\n{area}")
        print(f"  [{c(MARK[it['status']], it['status'])}] {it['title']}: {it['detail']}")
        if it["fix"] and it["status"] in (WARN, FAIL):
            print(f"         → {it['fix']}")
    n = {k: sum(1 for i in r.items if i["status"] == k) for k in (PASS, WARN, FAIL)}
    total = n[PASS] + n[WARN] + n[FAIL]
    score = round(100 * (n[PASS] + 0.5 * n[WARN]) / total) if total else 0
    print(f"\nScore {score}/100 — {n[PASS]} passed, {n[WARN]} to improve, {n[FAIL]} to fix.")
    return score


def write_html(r, path, score):
    rows = "".join(
        f'<tr class="{i["status"]}"><td>{html.escape(i["area"])}</td><td><b>{html.escape(i["title"])}</b></td>'
        f'<td class="st">{MARK[i["status"]]}</td><td>{html.escape(i["detail"])}'
        + (f'<div class="fix">→ {html.escape(i["fix"])}</div>' if i["fix"] and i["status"] in (WARN, FAIL) else "")
        + "</td></tr>" for i in r.items)
    page = f"""<!doctype html><meta charset="utf-8"><title>Credo Security Check</title>
<style>body{{font:15px/1.5 Inter,sans-serif;background:#17211c;color:#ebe8df;margin:2rem auto;max-width:60rem}}
h1{{font-weight:600}}table{{border-collapse:collapse;width:100%}}td{{padding:.5rem .6rem;border-bottom:1px solid #ffffff1a;vertical-align:top}}
.st{{font-weight:700}}.pass .st{{color:#6fcf7f}}.warn .st{{color:#e6c45a}}.fail .st{{color:#ef6b6b}}.info .st{{color:#7fc4e6}}
.fix{{color:#c9a85a;margin-top:.2rem}}.score{{font-size:2rem;color:#c9a85a}}</style>
<h1>Credo Security Check</h1><p>{dt.datetime.now():%d %B %Y %H:%M} · <span class="score">{score}/100</span></p>
<table>{rows}</table>"""
    pathlib.Path(path).write_text(page, encoding="utf-8")
    print("Report:", path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="credo-security-check", description=__doc__.splitlines()[0])
    ap.add_argument("--html", metavar="FILE", help="also write an HTML report")
    ap.add_argument("--quick", action="store_true", help="skip online checks (updates, firmware)")
    a = ap.parse_args(argv)
    r = Report()
    for check in CHECKS:
        try:
            check(r)
        except Exception as e:                       # one broken check must not stop the audit
            r.add("Other", check.__name__.replace("check_", ""), WARN, f"Check failed: {e}")
    for check in (check_updates, check_firmware):
        try:
            check(r, a.quick)
        except Exception as e:
            r.add("Updates", check.__name__.replace("check_", ""), WARN, f"Check failed: {e}")
    score = print_report(r)
    if a.html:
        write_html(r, a.html, score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
