# FlipPulse — Demo Video

**[`FlipPulse_Demo.mp4`](FlipPulse_Demo.mp4)** — a ~40-second vertical (1080×1920,
9:16) explainer for socials (Reels / TikTok / Shorts) and the landing page. No audio,
so it plays fine muted in feeds; add a music track in your editor if you want sound.

## Scenes

1. **FlipPulse** — automated 15-minute BTC Up/Down trading on Kalshi.
2. **96 markets every day** — too fast to trade by hand.
3. **The Pulse Engine** — reads order flow, momentum & trend on every 15-min candle.
4. **Smart sizing** — a % of your balance, auto-compounding (Conservative/Balanced/Aggressive).
5. **Built-in safety** — recovery mode, paper mode first, funds stay on Kalshi.
6. **You stay in control** — live Telegram alerts, one-tap pause.
7. **CTA** — "Pulse the markets." $99 setup · $99/mo + 20% of profits.

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
