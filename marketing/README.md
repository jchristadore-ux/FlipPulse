# FlipPulse — Marketing

## 90-day social media & marketing blitz

**[`blitz/00_START_HERE.md`](blitz/00_START_HERE.md)** — the complete, execution-ready
90-day marketing operating manual (master plan, day-by-day content calendar, every
post pre-written, 30 video scripts, AI graphics prompts, scheduler + automation
setup, daily checklist, KPI dashboard, scaling plan, and the compliance kit that
governs all of it). Start there.

# FlipPulse — Video

Two cuts, both vertical (1080×1920, 9:16), silent so they play clean muted in feeds:

- **[`FlipPulse_Demo.mp4`](FlipPulse_Demo.mp4)** — ~40s full explainer for socials and the
  landing page.
- **[`FlipPulse_Ad_15s.mp4`](FlipPulse_Ad_15s.mp4)** — ~15s fast-cut ad (hook → value →
  trust → CTA) for paid placements / Stories. Build it with `python marketing/build_ad.py`
  (it reuses the scene styling + assembler from `build_demo.py`).

## Scenes

1. **FlipPulse** — automated 15-minute BTC Up/Down trading on Kalshi.
2. **96 markets every day** — too fast to trade by hand.
3. **The Pulse Engine** — reads order flow, momentum & trend on every 15-min candle.
4. **Smart sizing** — a % of your balance, auto-compounding (Conservative/Balanced/Aggressive).
5. **Built-in safety** — recovery mode, paper mode first, funds stay on Kalshi.
6. **You stay in control** — live Telegram alerts, one-tap pause.
7. **CTA** — "Pulse the markets." $150 setup · $99/mo.

## Regenerate / edit

Scenes are plain HTML/CSS in `build_demo.py`; edit the copy or styling there, then:

```bash
pip install imageio-ffmpeg          # bundles an H.264 ffmpeg
python marketing/build_demo.py
```

It renders each scene to a PNG with headless Chromium, adds a slow Ken-Burns zoom, and
crossfades the scenes together into `FlipPulse_Demo.mp4` (H.264, yuv420p, faststart —
ready to upload).

> Tweak `DUR` / `XF` at the top of `build_demo.py` to change pacing (currently 6.2s per
> scene, 0.7s crossfades → ~40s total). Keep it 30–60s for social feeds.
