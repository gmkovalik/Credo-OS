"""Neutral FSSP app icon for public releases (no FSSP emblem): gold cross and "FSSP" on blue.

    python tools/make_fssp_public_icon.py   ->  tools/assets/credo-fssp-public.svg
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_theme as m  # noqa: E402

text = ('<text x="256" y="402" text-anchor="middle" font-family="Inter, Noto Sans, DejaVu Sans, sans-serif" '
        'font-weight="700" font-size="62" letter-spacing="8" fill="#ffffff">FSSP</text>')
svg = m.app_icon("credo-fssp", "#1d3a6e", "#1d3a6e", m.cross(256, 214, 170, 110, 26) + text)
(HERE / "assets/credo-fssp-public.svg").write_text(svg, encoding="utf-8")
print("wrote tools/assets/credo-fssp-public.svg")
