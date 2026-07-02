#!/usr/bin/env python3
"""
Generate the annotated onboarding "screenshots" for the FlipPulse setup guide.

These are clean, reproducible **illustrations** of each screen a customer sees
while (1) creating a Kalshi account + API key and (2) creating a Telegram bot
and finding their chat id. They are drawn as SVG — not photographic captures —
so they stay crisp at any size, embed cleanly in HTML and PDF, never leak a real
person's data, and can be regenerated in seconds if a vendor tweaks their UI:

    python onboarding/guide/build_assets.py

Every image uses the same visual language:
  • a red arrow + a numbered badge point at the ONE thing to click on that step
  • a blue callout pill labels it in plain language
  • a dashed red box highlights fields to copy
Output: onboarding/guide/assets/*.svg  (one file per major step)
"""
from __future__ import annotations
import pathlib

OUT = pathlib.Path(__file__).resolve().parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)

# ── palette ──────────────────────────────────────────────────────────────────
BG        = "#0b1120"      # canvas behind the mock device
INK       = "#1f2937"      # dark UI text
MUTE      = "#6b7280"      # secondary UI text
LINE      = "#e5e7eb"      # light UI hairlines
CARD      = "#ffffff"
FIELD     = "#f3f4f6"
RED       = "#ef4444"      # annotation arrows / warnings
BLUE      = "#2563eb"      # info callouts
TG        = "#2aabee"      # Telegram brand blue
TG_DK     = "#229ed9"
GREEN1    = "#7ef2a0"      # FlipPulse gradient
GREEN2    = "#35cee6"
SUCCESS   = "#16a34a"
FONT      = "font-family='ui-sans-serif,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif'"
MONO      = "font-family='ui-monospace,SFMono-Regular,Menlo,Consolas,monospace'"


# ── low-level primitives (all take absolute coords) ──────────────────────────
def rrect(x, y, w, h, rx, fill, stroke=None, sw=1, extra=""):
    s = f" stroke='{stroke}' stroke-width='{sw}'" if stroke else ""
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='{rx}'{s} fill='{fill}' {extra}/>"


def txt(x, y, s, size, fill, weight=400, anchor="start", font=FONT, extra=""):
    return (f"<text x='{x}' y='{y}' {font} font-size='{size}' font-weight='{weight}' "
            f"fill='{fill}' text-anchor='{anchor}' {extra}>{s}</text>")


def arrow(x1, y1, x2, y2, color=RED, w=5):
    """Curved-ish straight annotation arrow with a solid head."""
    return (f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{color}' "
            f"stroke-width='{w}' stroke-linecap='round' marker-end='url(#ah)'/>")


def hlbox(x, y, w, h, color=RED):
    return (f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='9' fill='none' "
            f"stroke='{color}' stroke-width='3.5' stroke-dasharray='9 6'/>")


def badge(x, y, n, r=19):
    return (f"<circle cx='{x}' cy='{y}' r='{r}' fill='url(#bg)' stroke='#06111a' stroke-width='2'/>"
            f"{txt(x, y+6, n, 20, '#06111a', 800, 'middle')}")


def callout(x, y, s, fill=BLUE):
    w = 22 + len(s) * 8.4
    return (rrect(x, y, w, 34, 17, fill) +
            txt(x + w/2, y + 22, s, 14, "#fff", 700, "middle"))


def button(x, y, w, h, label, fill, tc="#fff", size=15, weight=700, rx=10):
    return rrect(x, y, w, h, rx, fill) + txt(x + w/2, y + h/2 + size*0.35, label, size, tc, weight, "middle")


def cursor(x, y):
    return (f"<path d='M{x} {y} L{x} {y+22} L{x+6} {y+16} L{x+10} {y+24} "
            f"L{x+13} {y+22} L{x+9} {y+14} L{x+16} {y+14} Z' fill='#fff' stroke='#111' stroke-width='1.5'/>")


def field(x, y, w, label, value="", h=44, mono=False, value_color=INK):
    parts = [txt(x, y - 8, label, 12.5, MUTE, 600),
             rrect(x, y, w, h, 9, FIELD, LINE, 1.5)]
    if value:
        parts.append(txt(x + 14, y + h/2 + 5, value, 14.5, value_color, 500, "start",
                         MONO if mono else FONT))
    return "".join(parts)


# ── frames ───────────────────────────────────────────────────────────────────
def browser(x, y, w, h, url, body):
    """A generic desktop browser window. `body` is drawn inside the content area."""
    bar = 46
    dots = "".join(f"<circle cx='{x+22+i*20}' cy='{y+23}' r='6' fill='{c}'/>"
                   for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
    addr = (rrect(x+92, y+12, w-180, 22, 11, "#fff", LINE, 1) +
            f"<circle cx='{x+108}' cy='{y+23}' r='4.5' fill='none' stroke='{MUTE}' stroke-width='1.5'/>"
            + txt(x+120, y+27, url, 12.5, MUTE, 500))
    return "".join([
        rrect(x, y, w, h, 14, CARD, "#cbd5e1", 1.5),
        rrect(x, y, w, bar, 14, "#f1f5f9"),
        rrect(x, y+bar-8, w, 8, 0, "#f1f5f9"),
        f"<line x1='{x}' y1='{y+bar}' x2='{x+w}' y2='{y+bar}' stroke='{LINE}' stroke-width='1.5'/>",
        dots, addr, body,
    ])


def phone(x, y, w=380, h=760):
    """Returns (frame_svg, sx, sy, sw, sh) — screen content area inside a phone."""
    frame = (rrect(x, y, w, h, 46, "#0f172a") +
             rrect(x+8, y+8, w-16, h-16, 40, "#000") +
             rrect(x+16, y+16, w-32, h-32, 32, CARD))
    # notch
    frame += rrect(x + w/2 - 46, y+16, 92, 26, 13, "#0f172a")
    sx, sy, sw, sh = x+16, y+16, w-32, h-32
    return frame, sx, sy, sw, sh


def tg_status(sx, sy, sw):
    return (txt(sx+22, sy+34, "9:41", 13.5, INK, 700) +
            txt(sx+sw-22, sy+34, "● ● ● ▯", 12, INK, 700, "end"))


def tg_header(sx, sy, sw, name, sub, avatar_letter, color=TG):
    top = sy + 46
    return "".join([
        rrect(sx, top, sw, 60, 0, "#527da3" if color == "gray" else color),
        txt(sx+18, top+37, "‹", 30, "#fff", 700),
        f"<circle cx='{sx+64}' cy='{top+30}' r='19' fill='#ffffff33'/>",
        txt(sx+64, top+37, avatar_letter, 18, "#fff", 800, "middle"),
        txt(sx+92, top+26, name, 16, "#fff", 700),
        txt(sx+92, top+45, sub, 12, "#ffffffcc", 500),
    ]) , top + 60


def bubble(sx, y, side, lines, w=None, tail=True, fill_in="#f1f0f0", fill_out="#e1ffc7"):
    """A chat bubble. side='in' (left/gray) or 'out' (right/green)."""
    pad = 14
    lh = 21
    tw = max((len(l) for l in lines), default=8) * 7.6 + pad*2
    bw = w or min(max(tw, 60), 250)
    bh = len(lines) * lh + pad*1.4
    fill = fill_in if side == "in" else fill_out
    bx = sx + 16 if side == "in" else sx + 380 - 32 - bw - 16
    body = [rrect(bx, y, bw, bh, 16, fill)]
    for i, l in enumerate(lines):
        body.append(txt(bx + pad, y + pad + 6 + i*lh, l, 13.5, INK, 500))
    return "".join(body), y + bh + 12, bx, bw, bh


def wrap(name, w, h, inner, caption=""):
    cap = txt(w/2, h-16, caption, 15, "#94a3b8", 600, "middle") if caption else ""
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='100%' role='img' aria-label='{caption or name}'>
<defs>
  <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>
    <stop offset='0' stop-color='{GREEN1}'/><stop offset='1' stop-color='{GREEN2}'/>
  </linearGradient>
  <marker id='ah' markerWidth='9' markerHeight='9' refX='6.5' refY='4.5' orient='auto'>
    <path d='M0 0 L9 4.5 L0 9 Z' fill='{RED}'/>
  </marker>
  <filter id='sh' x='-20%' y='-20%' width='140%' height='140%'>
    <feDropShadow dx='0' dy='8' stdDeviation='14' flood-color='#000' flood-opacity='0.28'/>
  </filter>
</defs>
<rect width='{w}' height='{h}' rx='20' fill='{BG}'/>
{inner}
{cap}
</svg>"""
    (OUT / f"{name}.svg").write_text(svg)
    return name


# ═════════════════════════════════════════════════════════════════════════════
# KALSHI
# ═════════════════════════════════════════════════════════════════════════════
def _screen(name, url, content, ann, caption, w=960, h=620, bw=880, bh=500):
    b = f"<g filter='url(#sh)'>{browser(40, 40, bw, bh, url, content + ann)}</g>"
    wrap(name, w, h, b, caption)


def k02_verify():
    cx, cy = 40, 86
    content = "".join([
        f"<circle cx='{cx+bwc()/2}' cy='{cy+120}' r='34' fill='#eff6ff'/>",
        txt(cx+bwc()/2, cy+130, "✉", 34, BLUE, 700, "middle"),
        txt(cx+bwc()/2, cy+195, "Verify your email", 27, INK, 800, "middle"),
        txt(cx+bwc()/2, cy+228, "We sent a link to you@example.com.", 15, MUTE, 500, "middle"),
        txt(cx+bwc()/2, cy+250, "Open it and click “Verify”, then come back.", 15, MUTE, 500, "middle"),
        button(cx+bwc()/2-120, cy+290, 240, 48, "Open email app", "#fff", INK, 15, 700, 10) .replace("fill='#fff'", f"fill='#fff' stroke='{LINE}' stroke-width='1.5'"),
    ])
    ann = "".join([badge(cx+bwc()/2-150, cy+120, "2"),
                   callout(cx+bwc()/2+70, cy+104, "Check your inbox")])
    _screen("kalshi-02-verify-email", "kalshi.com/verify", content, ann,
            "Kalshi – verify your email before continuing")


def bwc():  # browser content width helper
    return 880


def k01_signup():
    cx, cy = 40, 86
    content = "".join([
        txt(cx+60, cy+80, "Create your account", 30, INK, 800),
        txt(cx+60, cy+112, "Trade on the outcome of real-world events.", 15, MUTE, 500),
        field(cx+60, cy+150, 380, "Email address", "you@example.com", mono=True),
        field(cx+60, cy+230, 380, "Password", "••••••••••"),
        button(cx+60, cy+310, 380, 50, "Create account", INK),
        rrect(cx+60, cy+390, 380, 30, 8, "#ecfdf5"),
        txt(cx+72, cy+410, "✓  Referred by a FlipPulse partner", 12.5, SUCCESS, 700),
    ])
    ann = "".join([
        badge(cx+40, cy+335, "1"),
        arrow(cx+540, cy+335, cx+445, cy+335),
        callout(cx+560, cy+318, "Click to sign up"),
        cursor(cx+300, cy+345),
    ])
    _screen("kalshi-01-signup", "kalshi.com/sign-up", content, ann,
            "Kalshi – create your account (opens from the green button)")


def k03_login():
    cx, cy = 40, 86
    content = "".join([
        # left nav
        rrect(cx, cy, 190, 414, 0, "#f8fafc"),
        txt(cx+22, cy+44, "Kalshi", 19, INK, 800),
        *[txt(cx+22, cy+90+i*38, t, 14.5, INK if i == 0 else MUTE, 600 if i == 0 else 500)
          for i, t in enumerate(["Markets", "Portfolio", "Activity", "Settings"])],
        # main
        txt(cx+230, cy+60, "Welcome back \U0001f44b", 26, INK, 800),
        txt(cx+230, cy+92, "Your account is verified and ready.", 15, MUTE, 500),
        rrect(cx+230, cy+120, 250, 96, 12, "#ecfdf5", "#a7f3d0", 1.5),
        txt(cx+250, cy+156, "Available balance", 13, "#047857", 700),
        txt(cx+250, cy+190, "$0.00", 28, SUCCESS, 800),
    ])
    ann = "".join([badge(cx+22-2, cy+90+3*38-14, "3"),
                   arrow(cx+330, cy+250, cx+150, cy+90+3*38-6),
                   callout(cx+300, cy+236, "Next: open Settings")])
    _screen("kalshi-03-login", "kalshi.com/portfolio", content, ann,
            "Kalshi – logged in; head to Settings next")


def k04_api_settings():
    cx, cy = 40, 86
    rows = ["Profile", "Security", "Notifications", "API Keys"]
    content = "".join([
        rrect(cx, cy, 220, 414, 0, "#f8fafc"),
        txt(cx+22, cy+42, "Settings", 18, INK, 800),
        *[(rrect(cx+10, cy+66+i*44, 200, 34, 8, "#eef2ff" if i == 3 else "none") +
           txt(cx+24, cy+88+i*44, t, 14.5, BLUE if i == 3 else MUTE, 700 if i == 3 else 500))
          for i, t in enumerate(rows)],
        txt(cx+260, cy+60, "API Keys", 24, INK, 800),
        txt(cx+260, cy+90, "Create a key so approved software can trade for you.", 14.5, MUTE, 500),
        rrect(cx+260, cy+120, 360, 70, 12, "#fff", LINE, 1.5),
        txt(cx+280, cy+152, "You don’t have any API keys yet.", 14, MUTE, 500),
        button(cx+260, cy+210, 220, 48, "+  Create API Key", INK),
    ])
    ann = "".join([badge(cx+10, cy+66+3*44+17, "4"),
                   arrow(cx+700, cy+150, cx+485, cy+150),
                   callout(cx+720, cy+134, "Open API Keys"),
                   cursor(cx+380, cy+232)])
    _screen("kalshi-04-api-settings", "kalshi.com/settings/api", content, ann,
            "Kalshi – Settings › API Keys › Create API Key")


def k05_create_key():
    cx, cy = 40, 86
    # modal
    content = "".join([
        rrect(cx, cy, bwc(), 414, 0, "#0b112055"),
        f"<g filter='url(#sh)'>",
        rrect(cx+bwc()/2-230, cy+70, 460, 300, 16, CARD),
        txt(cx+bwc()/2-200, cy+120, "New API key", 22, INK, 800),
        txt(cx+bwc()/2-200, cy+150, "Name it so you remember what it’s for.", 14, MUTE, 500),
        field(cx+bwc()/2-200, cy+176, 400, "Key name", "FlipPulse", mono=False),
        rrect(cx+bwc()/2-200, cy+250, 400, 44, 9, "#fffbeb", "#fde68a", 1.5),
        txt(cx+bwc()/2-186, cy+277, "⚠  Your PEM file downloads once. Save it now.", 12.5, "#b45309", 700),
        button(cx+bwc()/2-200, cy+312, 195, 46, "Cancel", "#fff", INK, 15, 700).replace("fill='#fff'", f"fill='#fff' stroke='{LINE}' stroke-width='1.5'"),
        button(cx+bwc()/2+5, cy+312, 195, 46, "Create key", INK),
        "</g>",
    ])
    ann = "".join([badge(cx+bwc()/2-215, cy+335, "5"),
                   arrow(cx+bwc()/2+240, cy+335, cx+bwc()/2+150, cy+335),
                   callout(cx+bwc()/2+250, cy+318, "Create the key")])
    _screen("kalshi-05-create-key", "kalshi.com/settings/api", content, ann,
            "Kalshi – name the key “FlipPulse” and create it")


def k06_download_pem():
    cx, cy = 40, 86
    content = "".join([
        txt(cx+40, cy+50, "API key created ✓", 22, SUCCESS, 800),
        txt(cx+40, cy+80, "Copy the Key ID and download the PEM. You’ll paste both into the form.", 14, MUTE, 500),
        # key id row
        rrect(cx+40, cy+110, bwc()-80, 62, 10, "#f8fafc", LINE, 1.5),
        txt(cx+58, cy+134, "API Key ID", 12, MUTE, 700),
        txt(cx+58, cy+158, "a1b2c3d4-0000-4e5f-9a8b-1234567890ab", 15, INK, 600, "start", MONO),
        button(cx+bwc()-80-120+40-20, cy+124, 120, 34, "Copy", "#eef2ff", BLUE, 13, 700, 8),
        # download row
        rrect(cx+40, cy+190, bwc()-80, 90, 10, "#fff", LINE, 1.5),
        txt(cx+58, cy+220, "Private key (PEM file)", 13.5, INK, 700),
        txt(cx+58, cy+244, "kalshi-flippulse.pem", 13.5, MUTE, 500, "start", MONO),
        txt(cx+58, cy+266, "Downloads once — keep it safe, don’t rename or open it.", 12, MUTE, 500),
        button(cx+bwc()-80-170+40, cy+212, 150, 46, "↓  Download PEM", INK),
        # browser download chip
        rrect(cx+40, cy+330, 260, 44, 10, "#eef2ff", "#c7d2fe", 1.5),
        txt(cx+58, cy+357, "↓  kalshi-flippulse.pem", 13.5, BLUE, 700, "start", MONO),
    ])
    ann = "".join([badge(cx+24, cy+141, "6a"),
                   callout(cx+bwc()-250, cy+92, "Copy the Key ID"),
                   arrow(cx+bwc()-150, cy+126, cx+bwc()-120, cy+120),
                   badge(cx+24, cy+235, "6b"),
                   callout(cx+bwc()-330, cy+300, "Download & save the PEM"),
                   arrow(cx+bwc()-190, cy+296, cx+bwc()-125, cy+258)])
    _screen("kalshi-06-download-pem", "kalshi.com/settings/api", content, ann,
            "Kalshi – copy the Key ID and download the PEM file (saves once)")


# ═════════════════════════════════════════════════════════════════════════════
# TELEGRAM
# ═════════════════════════════════════════════════════════════════════════════
def t07_download():
    w, h = 960, 560
    cx = 60
    cards = [("\U0001f4bb", "Windows", "telegram.org/dl"), ("", "macOS", "App Store"),
             ("\U0001f427", "Linux", "telegram.org/dl"), ("\U0001f4f1", "iPhone", "App Store"),
             ("▶", "Android", "Google Play")]
    body = [txt(w/2, 90, "Get Telegram", 30, "#fff", 800, "middle"),
            txt(w/2, 122, "The bot sends your alerts here. Install it on any device.", 15, "#94a3b8", 500, "middle")]
    cw, gap = 150, 20
    total = len(cards)*cw + (len(cards)-1)*gap
    x0 = (w - total) / 2
    for i, (ic, name, src) in enumerate(cards):
        x = x0 + i*(cw+gap)
        body += [rrect(x, 170, cw, 180, 16, "#ffffff", "#1e293b", 1),
                 txt(x+cw/2, 235, ic, 44, INK, 700, "middle"),
                 txt(x+cw/2, 278, name, 17, INK, 800, "middle"),
                 txt(x+cw/2, 302, src, 12, MUTE, 500, "middle"),
                 button(x+18, 316, cw-36, 20, "", GREEN2, "#06111a", 11, 700, 6).split("<text")[0]]
    body.append(badge(x0-4, 170, "1"))
    body.append(callout(w/2-95, 380, "Pick your device → install", BLUE))
    wrap("telegram-07-download", w, h, "".join(body),
         "Telegram – install on Windows, macOS, Linux, iPhone or Android")


def t08_account():
    w, h = 760, 820
    frame, sx, sy, sw, sh = phone(190, 30)
    content = "".join([
        tg_status(sx, sy, sw),
        rrect(sx, sy+46, sw, sh-46, 0, "#ffffff"),
        f"<circle cx='{sx+sw/2}' cy='{sy+180}' r='52' fill='{TG}'/>",
        txt(sx+sw/2, sy+196, "✈", 46, "#fff", 700, "middle"),
        txt(sx+sw/2, sy+280, "Your phone number", 20, INK, 800, "middle"),
        txt(sx+sw/2, sy+308, "Telegram will text you a code.", 13.5, MUTE, 500, "middle"),
        field(sx+30, sy+340, sw-60, "", "+1  (555) 123-4567", mono=True),
        button(sx+30, sy+410, sw-60, 48, "Next", TG),
        txt(sx+sw/2, sy+500, "Enter the 5-digit code they text you,", 13, MUTE, 500, "middle"),
        txt(sx+sw/2, sy+520, "then pick a name. That’s it — you’re in.", 13, MUTE, 500, "middle"),
    ])
    ann = "".join([badge(sx+18, sy+364, "2"),
                   arrow(sx+sw+70, sy+434, sx+sw-40, sy+434),
                   callout(sx+sw+30, sy+417, "Tap Next")])
    wrap("telegram-08-account", w, h, frame+content+ann,
         "Telegram – sign in with your phone number")


def _tg_phone_scene(name, header, sub, avatar, color, msgs, anns, caption, input_hint="Message"):
    w, h = 760, 820
    frame, sx, sy, sw, sh = phone(190, 30)
    parts = [frame, tg_status(sx, sy, sw)]
    hdr, ytop = tg_header(sx, sy, sw, header, sub, avatar, color)
    parts.append(rrect(sx, sy+46, sw, sh-46, 0, "#e7ebf0"))
    parts.append(hdr)
    y = ytop + 18
    for side, lines in msgs:
        bub, y, bx, bw, bh = bubble(sx, y, side, lines)
        parts.append(bub)
    # input bar
    iy = sy+sh-56
    parts += [rrect(sx, iy, sw, 56, 0, "#fff"),
              rrect(sx+16, iy+12, sw-90, 32, 16, FIELD, LINE, 1),
              txt(sx+32, iy+33, input_hint, 13.5, MUTE, 500),
              f"<circle cx='{sx+sw-32}' cy='{iy+28}' r='18' fill='{TG}'/>",
              txt(sx+sw-32, iy+33, "➤", 15, "#fff", 700, "middle")]
    parts += anns(sx, sy, sw, sh, ytop)
    wrap(name, w, h, "".join(parts), caption)


def t09_search_botfather():
    w, h = 760, 820
    frame, sx, sy, sw, sh = phone(190, 30)
    parts = [frame, tg_status(sx, sy, sw), rrect(sx, sy+46, sw, sh-46, 0, "#fff")]
    # search bar
    parts += [rrect(sx+16, sy+58, sw-32, 40, 20, FIELD),
              txt(sx+38, sy+83, "\U0001f50d  BotFather", 15, INK, 600)]
    # result row
    parts += [rrect(sx+8, sy+112, sw-16, 66, 12, "#f4f7fb"),
              f"<circle cx='{sx+42}' cy='{sy+145}' r='22' fill='{TG}'/>",
              txt(sx+42, sy+152, "\U0001f916", 20, "#fff", 700, "middle"),
              txt(sx+76, sy+140, "BotFather", 16, INK, 800),
              txt(sx+150, sy+140, "✓", 14, TG, 800),
              txt(sx+76, sy+162, "The one bot to rule them all", 12.5, MUTE, 500)]
    parts += [badge(sx+24, sy+145, "3"),
              arrow(sx+sw+70, sy+145, sx+sw-6, sy+145),
              callout(sx+sw+18, sy+128, "Tap the verified BotFather")]
    wrap("telegram-09-search-botfather", w, h, "".join(parts),
         "Telegram – search @BotFather and tap the verified (✓) result")


def t10_newbot():
    _tg_phone_scene(
        "telegram-10-newbot", "BotFather", "bot", "\U0001f916", TG,
        [("in", ["I can help you create and", "manage Telegram bots.", "", "Send /newbot to start."]),
         ("out", ["/newbot"])],
        lambda sx, sy, sw, sh, ytop: [
            badge(sx+sw-40, ytop+118, "4"),
            arrow(sx+sw+70, ytop+150, sx+sw-30, ytop+150),
            callout(sx+sw+18, ytop+133, "Type /newbot and send"),
            arrow(sx+sw/2, sy+sh-70, sx+sw/2, sy+sh-40)],
        "Telegram – press Start, then send /newbot to BotFather",
        input_hint="/newbot")


def t11_name_bot():
    _tg_phone_scene(
        "telegram-11-name-bot", "BotFather", "bot", "\U0001f916", TG,
        [("in", ["Alright, a new bot. How are", "we going to call it?"]),
         ("out", ["FlipPulse Alerts"]),
         ("in", ["Good. Now pick a username.", "It must end in ‘bot’."]),
         ("out", ["flippulse_jane_bot"]),
         ("in", ["Done! Congratulations \U0001f389"])],
        lambda sx, sy, sw, sh, ytop: [
            callout(sx+sw+18, ytop+30, "Any name you like", BLUE),
            badge(sx+sw-30, ytop+150, "5"),
            callout(sx+sw+18, ytop+150, "Username MUST end in ‘bot’"),
            arrow(sx+sw+70, ytop+150, sx+sw-8, ytop+150)],
        "Telegram – give the bot a name, then a username ending in ‘bot’")


def t12_copy_token():
    w, h = 760, 820
    frame, sx, sy, sw, sh = phone(190, 30)
    parts = [frame, tg_status(sx, sy, sw)]
    hdr, ytop = tg_header(sx, sy, sw, "BotFather", "bot", "\U0001f916", TG)
    parts += [rrect(sx, sy+46, sw, sh-46, 0, "#e7ebf0"), hdr]
    y = ytop + 16
    b1, y, *_ = bubble(sx, y, "in", ["Done! Use this token to", "access the HTTP API:"])
    parts.append(b1)
    # token bubble (highlighted)
    tbx = sx+16
    tbw = sw-40
    parts += [rrect(tbx, y, tbw, 60, 16, "#f1f0f0"),
              txt(tbx+14, y+26, "7767891234:AAH...", 13.5, INK, 700, "start", MONO),
              txt(tbx+14, y+48, "tap to copy", 11.5, TG, 600)]
    ty = y
    y += 74
    b3, y, *_ = bubble(sx, y, "in", ["Keep it secret. Anyone with", "this token controls your bot."])
    parts.append(b3)
    parts += [rrect(sx, sy+sh-56, sw, 56, 0, "#fff"),
              rrect(sx+16, sy+sh-44, sw-90, 32, 16, FIELD),
              txt(sx+32, sy+sh-23, "Message", 13.5, MUTE, 500),
              f"<circle cx='{sx+sw-32}' cy='{sy+sh-28}' r='18' fill='{TG}'/>",
              txt(sx+sw-32, sy+sh-23, "➤", 15, "#fff", 700, "middle")]
    parts += [hlbox(tbx-4, ty-4, tbw+8, 68),
              badge(sx, ty+30, "6"),
              arrow(sx+sw+70, ty+30, tbx+tbw+6, ty+30),
              callout(sx+sw+18, ty+13, "Copy the WHOLE token"),
              callout(sx+16, sy+sh-120, "⚠  Never share this token", RED)]
    wrap("telegram-12-copy-token", w, h, "".join(parts),
         "Telegram – tap the long token to copy it (keep it secret)")


def t13_open_start():
    _tg_phone_scene(
        "telegram-13-open-start", "FlipPulse Alerts", "bot", "F", "#5b8def",
        [("in", ["\U0001f916  This is your FlipPulse", "alerts bot."])],
        lambda sx, sy, sw, sh, ytop: [
            # big START button over input
            rrect(sx+16, sy+sh-64, sw-32, 44, 10, TG),
            txt(sx+sw/2, sy+sh-36, "START", 16, "#fff", 800, "middle"),
            badge(sx+40, sy+sh-42, "7"),
            arrow(sx+sw+70, sy+sh-42, sx+sw-30, sy+sh-42),
            callout(sx+sw+18, sy+sh-59, "Tap START once — required!"),
            callout(sx+16, sy+sh-150, "Open YOUR new bot — not BotFather", BLUE)],
        "Telegram – open your new bot and tap START (it won’t work otherwise)")
    # overwrite the default input bar drawn by helper is fine; START sits above it


def t14_userinfobot():
    w, h = 760, 820
    frame, sx, sy, sw, sh = phone(190, 30)
    parts = [frame, tg_status(sx, sy, sw)]
    hdr, ytop = tg_header(sx, sy, sw, "userinfobot", "bot", "i", "#7c8aa3")
    parts += [rrect(sx, sy+46, sw, sh-46, 0, "#e7ebf0"), hdr]
    y = ytop + 16
    bo, y, *_ = bubble(sx, y, "out", ["hi"])
    parts.append(bo)
    # response bubble with chat id highlighted
    rbx, rbw = sx+16, sw-60
    parts += [rrect(rbx, y, rbw, 118, 16, "#f1f0f0"),
              txt(rbx+14, y+28, "\U0001f464  Jane", 14, INK, 700),
              txt(rbx+14, y+52, "First name: Jane", 13, INK, 500),
              txt(rbx+14, y+74, "Username: @jane", 13, INK, 500),
              rrect(rbx+10, y+86, 190, 26, 7, "#e1ffc7"),
              txt(rbx+18, y+104, "Id: 123456789", 14, INK, 800, "start", MONO)]
    idy = y+86
    parts += [rrect(sx, sy+sh-56, sw, 56, 0, "#fff"),
              rrect(sx+16, sy+sh-44, sw-90, 32, 16, FIELD),
              txt(sx+32, sy+sh-23, "Message", 13.5, MUTE, 500),
              f"<circle cx='{sx+sw-32}' cy='{sy+sh-28}' r='18' fill='{TG}'/>",
              txt(sx+sw-32, sy+sh-23, "➤", 15, "#fff", 700, "middle")]
    parts += [callout(sx+96, ytop+18, "You send: hi", BLUE),
              arrow(sx+206, ytop+34, sx+266, ytop+34),
              badge(sx, idy+13, "8"),
              hlbox(rbx+6, idy-4, 198, 34),
              arrow(sx+sw+70, idy+13, rbx+210, idy+13),
              callout(sx+sw+18, idy-4, "Copy ONLY the number")]
    wrap("telegram-14-userinfobot", w, h, "".join(parts),
         "Telegram – @userinfobot replies with your numeric Chat ID")


def cover():
    """A friendly hero graphic for the guide/landing header."""
    w, h = 1200, 420
    body = [
        f"<rect width='{w}' height='{h}' fill='#080c15'/>",
        f"<rect width='{w}' height='{h}' fill='url(#hero)'/>",
        txt(80, 150, "FlipPulse Setup", 58, "#fff", 800),
        txt(82, 205, "Everything you need, one step at a time.", 24, "#9fb3c8", 500),
        rrect(80, 250, 250, 44, 22, "#ffffff14", "#35cee655", 1.5),
        txt(205, 278, "⏱  About 10–15 minutes", 16, GREEN1, 700, "middle"),
        rrect(350, 250, 210, 44, 22, "#ffffff14", "#35cee655", 1.5),
        txt(455, 278, "✓  One time only", 16, GREEN2, 700, "middle"),
    ]
    # little step dots
    for i in range(5):
        x = 820 + i*70
        body += [f"<circle cx='{x}' cy='210' r='26' fill='url(#bg)'/>",
                 txt(x, 217, str(i+1), 20, "#06111a", 800, "middle")]
        if i < 4:
            body.append(f"<line x1='{x+26}' y1='210' x2='{x+44}' y2='210' stroke='#35cee6' stroke-width='3'/>")
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='100%' role='img' aria-label='FlipPulse setup takes about 10 to 15 minutes'>
<defs>
  <linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='{GREEN1}'/><stop offset='1' stop-color='{GREEN2}'/></linearGradient>
  <radialGradient id='hero' cx='85%' cy='0%' r='90%'>
    <stop offset='0' stop-color='#35cee6' stop-opacity='0.18'/>
    <stop offset='0.5' stop-color='#7ef2a0' stop-opacity='0.06'/>
    <stop offset='1' stop-color='#080c15' stop-opacity='0'/>
  </radialGradient>
</defs>
{''.join(body)}
</svg>"""
    (OUT / "cover.svg").write_text(svg)


def main():
    k01_signup(); k02_verify(); k03_login(); k04_api_settings(); k05_create_key(); k06_download_pem()
    t07_download(); t08_account(); t09_search_botfather(); t10_newbot(); t11_name_bot()
    t12_copy_token(); t13_open_start(); t14_userinfobot()
    cover()
    files = sorted(p.name for p in OUT.glob("*.svg"))
    print(f"Wrote {len(files)} SVGs to {OUT}:")
    for f in files:
        print("  ", f)


if __name__ == "__main__":
    main()
