#!/usr/bin/env python3
"""
Build FlipPulse_OnePager.html (investor/partner brief) and render the PDF.

Numbers mirror the defaults in FlipPulse_Business_Model.xlsx. Regenerate the HTML:
    python business/build_onepager.py
Then render the PDF with headless Chromium:
    chromium --headless --no-pdf-header-footer \
      --print-to-pdf=FlipPulse_OnePager.pdf FlipPulse_OnePager.html
"""
from __future__ import annotations
import base64, pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
LOGO = "data:image/jpeg;base64," + base64.b64encode((REPO / "IMG_7262.jpeg").read_bytes()).decode()

# ── model defaults (from FlipPulse_Business_Model.xlsx) ───────────────────────
REV  = [1596,3234,5691,8379,10290,12390,18480,24675,32918,41738,51608,60532]
CUST = [8,20,38,60,80,100,140,190,255,330,415,500]

# ── inline SVG: monthly revenue bars + customers line ─────────────────────────
CW, CH = 660, 176
padL, padB, padT = 8, 22, 10
maxrev = max(REV)
bw = (CW - padL) / len(REV)
bars = []
for i, r in enumerate(REV):
    h = (r / maxrev) * (CH - padB - padT)
    x = padL + i * bw + bw * 0.18
    y = CH - padB - h
    bars.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw*0.64:.1f}' height='{h:.1f}' rx='3' fill='url(#g)'/>")
pts = []
for i, c in enumerate(CUST):
    x = padL + i * bw + bw * 0.5
    y = CH - padB - (c / 500) * (CH - padB - padT)
    pts.append(f"{x:.1f},{y:.1f}")
labels = "".join(
    f"<text x='{padL + i*bw + bw*0.5:.1f}' y='{CH-6}' fill='#5f6d85' font-size='9' text-anchor='middle'>{i+1}</text>"
    for i in range(12))
SVG = f"""<svg viewBox="0 0 {CW} {CH}" width="100%" preserveAspectRatio="xMidYMid meet">
  <defs><linearGradient id="g" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="#1f7a55"/><stop offset="1" stop-color="#7ef2a0"/></linearGradient></defs>
  {''.join(bars)}
  <polyline points="{' '.join(pts)}" fill="none" stroke="#35cee6" stroke-width="2.5"/>
  {''.join(f"<circle cx='{p.split(',')[0]}' cy='{p.split(',')[1]}' r='3' fill='#35cee6'/>" for p in pts)}
  {labels}
</svg>"""

HTML = f"""<!doctype html>
<!-- Source for business/FlipPulse_OnePager.pdf. Regenerate via business/build_onepager.py + Chromium. -->
<html lang="en"><head><meta charset="utf-8"><style>
  @page {{ size: letter; margin: 0; }}
  * {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  html,body {{ margin:0; padding:0; }}
  body {{ font-family:-apple-system,'Segoe UI',Helvetica,Arial,sans-serif; background:#080c15;
    color:#c9d3e2; font-size:10.4px; line-height:1.42; }}
  .page {{ min-height:100vh; padding:30px 40px 22px;
    background:
      radial-gradient(1000px 440px at 82% -8%, rgba(51,206,230,0.11), transparent 60%),
      radial-gradient(820px 400px at 6% 110%, rgba(126,242,160,0.08), transparent 55%), #080c15; }}
  .head {{ display:flex; align-items:center; gap:14px; border-bottom:1px solid #1c2740; padding-bottom:12px; }}
  .logo {{ width:52px; height:52px; border-radius:13px; box-shadow:0 0 0 1px #22344f; }}
  .brand {{ font-size:25px; font-weight:800; color:#fff; letter-spacing:-.5px; line-height:1; }}
  .tag {{ font-size:11px; color:#7c8aa3; margin-top:3px; }}
  .pill {{ margin-left:auto; font-size:9px; font-weight:800; color:#06111a;
    background:linear-gradient(135deg,#7ef2a0,#35cee6); padding:5px 11px; border-radius:20px; }}
  h2 {{ font-size:10.5px; text-transform:uppercase; letter-spacing:1px; margin:0 0 7px; font-weight:800;
    background:linear-gradient(90deg,#7ef2a0,#35cee6); -webkit-background-clip:text; background-clip:text; color:transparent; }}
  .metrics {{ display:flex; gap:9px; margin:14px 0 4px; }}
  .metric {{ flex:1; border:1px solid #1e3350; border-radius:9px; padding:9px 6px; text-align:center;
    background:linear-gradient(180deg,rgba(51,206,230,0.05),transparent); }}
  .metric .v {{ font-size:19px; font-weight:800; color:#7ef2a0; line-height:1; }}
  .metric .l {{ font-size:8.4px; color:#8fa0ba; text-transform:uppercase; letter-spacing:.4px; margin-top:4px; }}
  .cols {{ display:flex; gap:20px; margin-top:14px; }}
  .col {{ flex:1; }}
  ul {{ margin:0; padding-left:0; list-style:none; }}
  li {{ position:relative; padding-left:15px; margin-bottom:5px; }}
  li::before {{ content:"▸"; position:absolute; left:0; color:#35cee6; font-weight:800; }}
  b {{ color:#eaf2ff; }}
  .box {{ border:1px solid #22344f; border-radius:9px; padding:11px 13px; margin-top:6px;
    background:rgba(255,255,255,0.015); }}
  table {{ width:100%; border-collapse:collapse; font-size:9.6px; margin-top:4px; }}
  th,td {{ padding:4px 6px; border-bottom:1px solid #17233a; text-align:right; }}
  th:first-child, td:first-child {{ text-align:left; color:#9aa7bd; }}
  th {{ color:#7c8aa3; font-size:8.6px; text-transform:uppercase; letter-spacing:.4px; }}
  td.g {{ color:#7ef2a0; font-weight:700; }}
  .chartwrap {{ border:1px solid #22344f; border-radius:9px; padding:10px 12px 4px; margin-top:6px;
    background:rgba(255,255,255,0.015); }}
  .legend {{ display:flex; gap:16px; font-size:9px; color:#8fa0ba; margin-bottom:4px; }}
  .sw {{ display:inline-block; width:10px; height:10px; border-radius:3px; vertical-align:-1px; margin-right:4px; }}
  .disc {{ margin-top:13px; border-top:1px solid #1c2740; padding-top:9px; font-size:8.4px; color:#5f6d85; }}
</style></head><body>
<div class="page">
  <div class="head">
    <img class="logo" src="{LOGO}">
    <div><div class="brand">FlipPulse</div>
      <div class="tag">Automated 15-minute BTC Up/Down trading on Kalshi — sold as a managed service.</div></div>
    <div class="pill">Investor / Partner Brief</div>
  </div>

  <div class="metrics">
    <div class="metric"><div class="v">500</div><div class="l">Customers · mo 12</div></div>
    <div class="metric"><div class="v">$594K</div><div class="l">ARR (run-rate)</div></div>
    <div class="metric"><div class="v">$272K</div><div class="l">Yr-1 revenue</div></div>
    <div class="metric"><div class="v">$247K</div><div class="l">Yr-1 net profit</div></div>
    <div class="metric"><div class="v">~92%</div><div class="l">Gross margin</div></div>
  </div>

  <div class="cols">
    <div class="col">
      <h2>The Business</h2>
      <ul>
        <li>A trading bot that turns Kalshi's <b>96 daily 15-minute BTC markets</b> into a hands-off, rules-based engine.</li>
        <li><b>One bot per customer</b> — their Kalshi key, their Telegram, their own deployment. Funds never leave Kalshi.</li>
        <li><b>Self-serve funnel:</b> a web form takes payment + keys, alerts the operator, and a dashboard turns each signup into a deploy in minutes.</li>
        <li>Sizing is a <b>% of balance</b>, so one product fits every account size and compounds.</li>
      </ul>
      <h2 style="margin-top:12px;">Revenue Model</h2>
      <div class="box">
        <ul>
          <li><b>$150</b> one-time setup</li>
          <li><b>$99 / month</b> subscription (the core, recurring engine)</li>
          <li>Performance fee &mdash; <b>TBD</b> (planned upside, not currently charged)*</li>
        </ul>
      </div>
      <h2 style="margin-top:12px;">Unit Economics <span style="color:#8fa0ba;font-weight:600;">/ customer / mo</span></h2>
      <div class="box">
        <table>
          <tr><td>Subscription</td><td class="g">$99.00</td></tr>
          <tr><td>Hosting (Railway, 1 bot)</td><td>−$5.00</td></tr>
          <tr><td>Stripe fee (~3.9%)</td><td>−$3.90</td></tr>
          <tr><td><b>Gross margin / customer</b></td><td class="g">≈ $90 (91%)</td></tr>
        </table>
        <div style="font-size:8.6px;color:#8fa0ba;margin-top:5px;">Fixed overhead ≈ $130/mo (Claude Max $100 + tools $30) — amortizes to ~$0.26/customer at 500.</div>
      </div>
    </div>

    <div class="col">
      <h2>12-Month Projection</h2>
      <div class="chartwrap">
        <div class="legend"><span><span class="sw" style="background:#7ef2a0;"></span>Monthly revenue</span>
          <span><span class="sw" style="background:#35cee6;"></span>Active customers (→500)</span></div>
        {SVG}
        <div style="font-size:8.4px;color:#5f6d85;text-align:center;">month 1 → 12</div>
      </div>
      <table style="margin-top:10px;">
        <tr><th>Quarter</th><th>Revenue</th><th>Net profit</th></tr>
        <tr><td>Q1 (mo 1–3)</td><td>$10.5K</td><td class="g">$9.5K</td></tr>
        <tr><td>Q2 (mo 4–6)</td><td>$31.1K</td><td class="g">$25.1K</td></tr>
        <tr><td>Q3 (mo 7–9)</td><td>$76.1K</td><td class="g">$70.3K</td></tr>
        <tr><td>Q4 (mo 10–12)</td><td>$153.9K</td><td class="g">$142.2K</td></tr>
        <tr><td><b>Year 1</b></td><td><b>$271.5K</b></td><td class="g"><b>$247.1K</b></td></tr>
      </table>
      <h2 style="margin-top:12px;">Growth &amp; Costs</h2>
      <ul>
        <li>Ramp: <b>100 customers by month 6</b>, <b>500 by month 12</b> (4% monthly churn).</li>
        <li>Annual operating cost <b>~$21K</b> — dominated by per-bot hosting, which scales linearly with revenue.</li>
        <li>Hardware (top-spec Mac mini + curved monitor, ~$3.3K) <b>funded from profit</b> in month 5.</li>
        <li>Future upside lever: an optional <b>performance fee</b> (currently on hold, pending review) — a lever on top of the recurring base above.</li>
      </ul>
    </div>
  </div>

  <div class="disc">
    *The performance fee is <b>not currently charged</b> (temporarily on hold, pending regulatory/compliance review) and
    is excluded from every figure above — all headline numbers are from the recurring <b>$150 setup + $99/mo</b> model
    only. Numbers are generated by <b>FlipPulse_Business_Model.xlsx</b> with fully editable inputs (pricing, growth, costs
    sourced mid-2026: Railway, Stripe, Claude, GitHub, Apple). This brief is a business projection, not investment advice
    or a securities offering.
  </div>
</div>
</body></html>"""

out = REPO / "business" / "FlipPulse_OnePager.html"
out.write_text(HTML)
print("wrote", out, len(HTML), "bytes")
