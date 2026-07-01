#!/usr/bin/env python3
"""
Build FlipPulse_Ad_15s.mp4 — a ~15s vertical (1080x1920) fast-cut ad, reusing the
scene styling + assembler from build_demo.py.

Regenerate:  python marketing/build_ad.py
"""
from __future__ import annotations
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_demo as B          # shared CSS, scene(), LOGO, assemble()

OUT = pathlib.Path(__file__).resolve().parent / "FlipPulse_Ad_15s.mp4"
S = B.scene

AD_SCENES = [
    # hook
    S(f"<img class='logo' src='{B.LOGO}'><div class='big'>Flip<span class='grad'>Pulse</span></div>"
      "<div class='sub'>Automated <b>15-minute</b> Bitcoin trading</div>"),
    # value
    S("<div class='big'><span class='grad'>96</span> trades a day&mdash;<br>done for you</div>"
      "<div class='sub'>Every 15-minute Up/Down market on Kalshi,<br>traded automatically.</div>"),
    # trust
    S("<div class='kicker'>Smart &amp; safe</div>"
      "<div class='big'>A <span class='grad'>%</span> of your<br>balance</div>"
      "<div class='sub'>Auto-compounding &middot; paper mode first<br><b>Your funds stay on Kalshi.</b></div>"),
    # CTA
    S(f"<img class='logo' src='{B.LOGO}'><div class='big'>Pulse the<br><span class='grad'>markets.</span></div>"
      "<div class='price'>$99/mo &middot; start today</div>"
      "<div class='foot'>FLIPPULSE</div>"),
]

if __name__ == "__main__":
    B.assemble(AD_SCENES, str(OUT), dur=4.0, xf=0.4)      # ~14.8s
