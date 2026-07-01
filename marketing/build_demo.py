#!/usr/bin/env python3
"""
Build FlipPulse_Demo.mp4 — a ~40s vertical (1080x1920) social explainer.

Pipeline: render each HTML scene to a PNG with headless Chromium, turn each still
into a short Ken-Burns clip, then crossfade them together with ffmpeg (H.264).

Regenerate:  python marketing/build_demo.py
"""
from __future__ import annotations
import base64, os, subprocess, sys, tempfile, pathlib

ROOT   = pathlib.Path(__file__).resolve().parent
REPO   = ROOT.parent
OUT    = ROOT / "FlipPulse_Demo.mp4"
W, H, FPS = 1080, 1920, 30
DUR, XF   = 6.2, 0.7        # per-scene seconds, crossfade seconds

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
import imageio_ffmpeg
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

LOGO = "data:image/jpeg;base64," + base64.b64encode((REPO / "IMG_7262.jpeg").read_bytes()).decode()

CSS = """
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif;}
html,body{width:1080px;height:1920px;overflow:hidden;background:#070b13;}
.stage{width:1080px;height:1920px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:110px 90px;color:#dbe6f5;
  background:
    radial-gradient(1200px 700px at 78% -6%, rgba(51,206,230,0.16), transparent 60%),
    radial-gradient(1000px 640px at 8% 112%, rgba(126,242,160,0.12), transparent 55%),
    #070b13;}
.kicker{font-size:30px;font-weight:800;letter-spacing:5px;text-transform:uppercase;
  color:#35cee6;margin-bottom:34px;}
.big{font-size:118px;font-weight:850;line-height:1.02;letter-spacing:-2px;color:#fff;}
.grad{background:linear-gradient(100deg,#7ef2a0,#35cee6);-webkit-background-clip:text;background-clip:text;color:transparent;}
.sub{font-size:44px;line-height:1.35;color:#aab8cf;margin-top:40px;font-weight:500;}
.sub b{color:#eaf2ff;font-weight:800;}
.logo{width:230px;height:230px;border-radius:52px;object-fit:cover;box-shadow:0 0 0 2px #24405f,0 30px 90px rgba(0,0,0,.5);margin-bottom:60px;}
.chips{display:flex;gap:26px;margin-top:60px;flex-wrap:wrap;justify-content:center;}
.chip{font-size:38px;font-weight:800;padding:20px 40px;border-radius:60px;border:2px solid #24405f;color:#cfe;}
.chip.a{border-color:#7ef2a0;color:#7ef2a0;} .chip.b{border-color:#35cee6;color:#35cee6;} .chip.c{border-color:#f2b06a;color:#f2b06a;}
.candles{display:flex;gap:16px;align-items:flex-end;height:360px;margin-top:20px;}
.candle{width:46px;border-radius:8px;}
.up{background:linear-gradient(#7ef2a0,#3aa66a);} .dn{background:linear-gradient(#f2789a,#a63a5a);}
.row{display:flex;flex-direction:column;gap:30px;margin-top:50px;}
.li{font-size:44px;color:#cdd8e8;display:flex;align-items:center;gap:22px;justify-content:center;}
.li .dot{color:#35cee6;font-weight:900;}
.price{font-size:62px;font-weight:850;color:#7ef2a0;margin-top:50px;}
.price small{font-size:34px;color:#8fa0ba;font-weight:600;}
.tag{font-size:40px;color:#8fa0ba;margin-top:26px;letter-spacing:1px;}
.foot{position:absolute;bottom:70px;font-size:30px;color:#5f6d85;letter-spacing:3px;}
"""

def scene(inner: str) -> str:
    return f"<!doctype html><html><head><meta charset=utf-8><style>{CSS}</style></head><body><div class='stage'>{inner}</div></body></html>"

CANDLES = "".join(
    f"<div class='candle {'up' if h in (120,210,300,330) else 'dn'}' style='height:{h}px'></div>"
    for h in (120,190,150,210,170,300,240,330,280,360))

SCENES = [
    # 1 — logo intro
    scene(f"<img class='logo' src='{LOGO}'><div class='big'>Flip<span class='grad'>Pulse</span></div>"
          f"<div class='sub'>Automated <b>15-minute</b> Bitcoin<br>Up/Down trading on Kalshi</div>"),
    # 2 — the opportunity
    scene("<div class='kicker'>The opportunity</div>"
          "<div class='big'><span class='grad'>96</span> markets<br>every day</div>"
          "<div class='sub'>Bitcoin settles Up or Down every 15 minutes.<br><b>Too fast to trade by hand.</b></div>"),
    # 3 — the engine
    scene("<div class='kicker'>The Pulse Engine</div>"
          f"<div class='candles'>{CANDLES}</div>"
          "<div class='sub'>Reads <b>order flow</b>, <b>momentum</b> &amp; <b>trend</b><br>on every 15-minute candle — automatically.</div>"),
    # 4 — sizing
    scene("<div class='kicker'>Smart position sizing</div>"
          "<div class='big'>A <span class='grad'>%</span> of your<br>balance</div>"
          "<div class='sub'>Scales to any account and <b>compounds</b> as you grow.</div>"
          "<div class='chips'><span class='chip a'>Conservative</span><span class='chip b'>Balanced</span><span class='chip c'>Aggressive</span></div>"),
    # 5 — safety
    scene("<div class='kicker'>Built-in safety</div>"
          "<div class='big grad'>Guardrails<br>on by default</div>"
          "<div class='row'>"
          "<div class='li'><span class='dot'>&#9642;</span> Recovery mode &amp; loss-streak pause</div>"
          "<div class='li'><span class='dot'>&#9642;</span> Paper mode first — practice risk-free</div>"
          "<div class='li'><span class='dot'>&#9642;</span> Your funds never leave Kalshi</div></div>"),
    # 6 — control
    scene("<div class='kicker'>You stay in control</div>"
          "<div class='big'>Live alerts.<br><span class='grad'>One-tap</span> pause.</div>"
          "<div class='sub'>Every trade, win, and daily summary<br>straight to your <b>Telegram</b>.</div>"),
    # 7 — CTA
    scene(f"<img class='logo' src='{LOGO}'><div class='big'>Pulse the<br><span class='grad'>markets.</span></div>"
          "<div class='price'>$99 setup &middot; $99/mo <small>+ 20% of profits</small></div>"
          "<div class='tag'>Start in paper mode &mdash; go live when you're ready.</div>"
          "<div class='foot'>FLIPPULSE</div>"),
]

def render_png(html: str, png: str) -> None:
    html_path = png + ".html"
    with open(html_path, "w") as f:
        f.write(html)
    subprocess.run([CHROME, "--headless", "--no-sandbox", "--hide-scrollbars",
                    "--force-device-scale-factor=1", f"--window-size={W},{H}",
                    f"--screenshot={png}", html_path],
                   check=True, capture_output=True)

def make_clip(png: str, clip: str, zoom_in: bool) -> None:
    # Canonical Ken Burns: ONE input image expanded to `frames` frames by zoompan.
    frames = int(DUR * FPS)
    if zoom_in:
        z = "min(zoom+0.00060,1.11)"
    else:
        z = "if(lte(on,1),1.11,max(zoom-0.00060,1.0))"
    vf = (f"zoompan=z='{z}':d={frames}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"format=yuv420p")
    subprocess.run([FFMPEG, "-y", "-i", png, "-vf", vf, "-frames:v", str(frames),
                    "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", clip],
                   check=True, capture_output=True)

def main() -> None:
    tmp = tempfile.mkdtemp()
    clips = []
    for i, html in enumerate(SCENES):
        png = os.path.join(tmp, f"s{i}.png")
        clip = os.path.join(tmp, f"c{i}.mp4")
        render_png(html, png)
        make_clip(png, clip, zoom_in=(i % 2 == 0))
        clips.append(clip)
        print(f"  scene {i+1}/{len(SCENES)} rendered")

    # crossfade chain
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    trans = ["fade", "smoothleft", "fade", "smoothup", "fade", "fadegrays"]
    fc, prev = [], "0"
    for j in range(1, len(clips)):
        off = round(j * (DUR - XF), 3)
        lbl = f"v{j}"
        src = f"[{prev}]" if j == 1 else f"[{prev}]"
        t = trans[(j - 1) % len(trans)]
        fc.append(f"{src}[{j}]xfade=transition={t}:duration={XF}:offset={off}[{lbl}]")
        prev = lbl
    filtergraph = ";".join(fc)
    total = round(len(clips) * DUR - (len(clips) - 1) * XF, 2)
    cmd = [FFMPEG, "-y", *inputs, "-filter_complex", filtergraph,
           "-map", f"[{prev}]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", str(FPS), str(OUT)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit("ffmpeg xfade failed")
    print(f"wrote {OUT}  (~{total}s, {W}x{H})")

if __name__ == "__main__":
    main()
