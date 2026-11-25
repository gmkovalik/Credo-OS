"""credo-dock: helpers for the Credo Dock (the dock itself is the org.credo.dock Plasma widget).

  credo-dock --launchpad   open Apps (credo-launchpad, the full-screen glass app grid)
"""
import shutil
import subprocess
import sys


def stop_crystal_dock():
    """Earlier Credo updates used Crystal Dock; make sure it is gone."""
    subprocess.run(["pkill", "-x", "crystal-dock"], capture_output=True)


def launchpad():
    if shutil.which("credo-launchpad"):
        subprocess.Popen(["credo-launchpad"], start_new_session=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--launchpad" in argv:
        return launchpad()
    print(__doc__.strip())


if __name__ == "__main__":
    sys.exit(main())
