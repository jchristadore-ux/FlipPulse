# 05 — Graphics: Brand Kit + AI Prompt Library

Asset IDs (G-x.x) are referenced by the calendar and video scripts. Generate
once, save to Google Drive `/FlipPulse/Brand/` (folder structure in
`07_AUTOMATION.md` §5), and load into Canva as a Brand Kit.

## §1 — Brand kit (set this up in Canva first)

Canva → Brand Hub (Pro) → add:
- **Colors:**
  - `#0B0F1A` Midnight (backgrounds)
  - `#00E5A0` Pulse Green (accents, the "signal" color — up/win/go)
  - `#FF4D5E` Signal Red (refusals, losses — used honestly and often)
  - `#8B93A7` Slate (secondary text)
  - `#F5F7FA` Paper White (text on dark)
  - `#FFC24D` Amber (warnings/disclaimers)
- **Fonts (Canva-available):** Headings **Space Grotesk Bold** · Body **Inter** ·
  Log lines/numbers **JetBrains Mono** (monospace = "terminal receipt" identity).
- **Visual identity in one sentence:** *dark terminal aesthetic, one heartbeat
  of neon green, monospace receipts, generous empty space — a quant's desk at
  night, not a casino.*
- **Text placement rule (all social graphics):** headline top-left or centered
  upper third; log line / receipt center; disclaimer strip bottom 8% in Amber
  or Slate, 60% opacity, always present on anything with numbers.
- **Consistency rule:** every graphic uses ≥1 of: the pulse-line motif, a
  monospace log line, or the ✓/✗ checklist. That's what makes the feed cohere.

**The disclaimer strip (copy for every stats/screenshot graphic):**
`Simulated (paper-mode) activity. Not financial advice. Trading involves risk of loss.`

---

## §2 — Core identity assets

### G-2.1 Logo / profile picture
- **Midjourney:** `minimalist logo for "FlipPulse", a single ECG heartbeat pulse line that ends in an upward candlestick, neon green #00E5A0 on deep navy #0B0F1A, flat vector, geometric, fintech, no text, no gradients, centered, lots of negative space --v 6 --style raw --s 50`
- **ChatGPT Images:** `Design a minimalist flat vector logo mark: an ECG-style heartbeat line that transitions into a single upward candlestick at its final beat. Neon green (#00E5A0) line on a deep navy (#0B0F1A) circular background. No text. Clean, geometric, fintech style, generous negative space, crisp edges, suitable as a 400x400 social profile picture.`
- **Ideogram:** same as ChatGPT prompt + `style: DESIGN, aspect 1:1`.
- Make a white-on-transparent version too (ask: "same mark, white line, transparent background").

### G-2.2 X / Facebook header (1500×500 / 820×312)
- **ChatGPT Images:** `Wide banner, deep navy #0B0F1A background with a very subtle dark grid. A neon green ECG pulse line (#00E5A0) runs the full width at 40% height, flatlining then beating once at the right third. Right side, monospace terminal text in soft white: "9 checks. Then maybe a trade." Bottom-right corner small amber text: "Not financial advice." Minimalist fintech aesthetic, high contrast, no other elements.`
- **Canva Magic Media:** `dark navy fintech banner, single neon green heartbeat pulse line, subtle grid, minimalist, terminal aesthetic` → then add the text in Canva with brand fonts (Magic Media text is unreliable; always set type in Canva).

### G-2.3 End card for all videos (1080×1920)
- Build in Canva (no AI needed): Midnight bg, logo top, `Watch it decide, live` in Space Grotesk, `t.me/flippulse` in JetBrains Mono Pulse-Green, disclaimer strip bottom. Save as template `FP-EndCard`.

---

## §3 — Content graphics (the recurring set)

### G-3.1 "Receipt card" (the workhorse — Telegram log reframed as a graphic, 1080×1080)
- Canva template (build once): Midnight bg → paste log text in JetBrains Mono
  Paper-White → highlight the key value in Pulse Green (win/entry) or Signal
  Red (refusal/loss) → tiny logo bottom-left → disclaimer strip.
- **Midjourney (background only):** `dark navy abstract background, faint grid, soft vignette, single thin neon green pulse line lower third, minimal, empty center for text overlay --ar 1:1 --v 6 --style raw`

### G-3.2 "It said no" card (1080×1080 & 1080×1920)
- Canva: giant Signal-Red `✗ SKIPPED` top, the refusal reason in mono
  (`RANGING (R²=0.31) — only TRENDING allowed.`), subline in Slate: `One failed
  check beats eight passed ones.` Disclaimer strip.
- **Ideogram (for the illustrated variant):** `A minimalist dark navy poster with a large glowing red X made of a flat ECG line, small green monospace terminal text below, fintech terminal aesthetic, moody, high contrast. Text on poster: "SKIPPED"` (Ideogram handles short text well; keep it to one word).

### G-3.3 Quote/hook card (1080×1080)
- Canva: hook line (from `03_POST_LIBRARY.md` §11) in Space Grotesk 72pt Paper
  White on Midnight, one word in Pulse Green, pulse-line divider, logo. No AI needed.

### G-3.4 The 9-layer checklist graphic (1080×1350 portrait — used in V01, C01)
- Canva: numbered 1–9 list, each row `✓` Pulse Green, layer name bold + 4-word
  description Slate; row 5 (Regime) highlighted with a green left border.
  Footer: `ALL nine pass, or no trade.`
- **ChatGPT Images (illustrated header for it):** `A vertical dark navy infographic header: nine small glowing green checkboxes in a column descending into one large padlock, flat vector, minimalist fintech style, neon green #00E5A0 accents, no text.`

### G-3.5 Chart-day graphic (sideways/volatile BTC days)
- **Midjourney:** `flat vector illustration, a bitcoin price chart moving perfectly sideways in a boring flat channel, a small sleeping robot sitting on the chart line, dark navy background, neon green accents, minimal, dry humor, editorial style --ar 1:1 --v 6`
- Volatile variant: `...a chaotic spiking bitcoin chart like a seismograph, a small robot calmly sitting behind glass unbothered...`

### G-3.6 Custody diagram "your money never moves" (1080×1080 — used in V05, X-RL-12)
- Canva build: left box `YOUR Kalshi account (CFTC-regulated)` with a Pulse
  Green padlock; right box `FlipPulse` connected only by a dotted line labeled
  `API key — trade only, can't withdraw`; a big red ✗ over an arrow labeled
  `your funds` pointing at FlipPulse. Caption: `We never hold your money.`
- **ChatGPT Images (icon set for it):** `Flat vector icon set on transparent background, neon green on navy style: a padlock, a bank/exchange building, a small friendly robot, a key, a crossed-out dollar arrow. Consistent 2px stroke, minimal fintech style.`

### G-3.7 "Choose your fighter" format cards (3× 1080×1350 — used in V19, C06)
- **Ideogram:** `Three trading-mode character cards in a video-game select screen style, dark navy background, neon UI: "CONSERVATIVE" with a shield icon and small stat bars (low risk, low frequency), "BALANCED" with scales icon (medium bars), "AGGRESSIVE" with lightning icon (high bars), flat vector, fintech gaming aesthetic, green/white/red accents. Text: "CONSERVATIVE", "BALANCED", "AGGRESSIVE"`
- Then rebuild cleanly in Canva using the AI output as the layout reference
  (stat bars: Stake 5/10/20%, Filters strict→loose, Frequency low→high,
  Variance low→high — data from `formats.py`).

### G-3.8 Meme templates
- Keep a Canva folder `FP-Memes` with: Drake-format (top: `Bot that trades
  24/7` / bottom: `Bot that sleeps through the 2am garbage books`), tier-list
  frame, "corporate needs you to find the difference" (two identical sideways
  charts labeled `opportunity` / `noise`). Build from Canva's meme templates —
  don't AI-generate memes; native template look performs better.

---

## §4 — Recurring template specs (build once in Canva, reuse forever)

### G-4.1 Carousel master (1080×1350, 8-page template for C01–C06)
Page 1 cover: hook + pulse line. Pages 2–7: one idea per page — Space Grotesk
headline ≤7 words top, 2-line Inter body, mono log-line footer where relevant,
page dots. Page 8 CTA: `Starts in paper mode` + `go.flippulse.com` + disclaimer
strip. Duplicate → swap copy from `03_POST_LIBRARY.md` §4.3 outlines.

### G-4.2 Story master (1080×1920)
Zones: top 15% safe (avatar overlap), poll/quiz sticker center-right, log
screenshot in a phone-frame mockup center, link sticker bottom-third, Amber
disclaimer above it on stat stories.

### G-4.3 Weekly recap card (1080×1920 Story + 1080×1080 feed)
`THIS WEEK IN THE FEED` header → 4 mono stat rows (setups passed / trades
refused / top refusal reason / new customers) → pulse divider → CTA. Numbers
from the KPI sheet every Friday. **Always includes the disclaimer strip.**

### G-4.4 Thumbnail template (TikTok/Reels covers)
1080×1920, giant 3–5 word hook in Space Grotesk (from each script's Thumbnail
line), heavy contrast, one Pulse Green word, face or log screenshot underneath
at 60% brightness. Covers matter: they're your IG grid.

---

## §5 — Tool cheat-sheet

| Tool | Use for | Where | Notes |
|---|---|---|---|
| **Midjourney** ($10/mo) | Backgrounds, illustrations, logo exploration | midjourney.com | Use `--style raw --v 6`; never for text |
| **ChatGPT Images** | Diagrams, icon sets, banners with short text | chat.openai.com | Best at following layout instructions |
| **Ideogram** (free tier) | Anything where text must render correctly | ideogram.ai | Keep rendered text ≤3 words |
| **Canva Magic Media** | Quick fills inside existing templates | canva.com → Apps → Magic Media | Convenience only |
| **Canva (manual)** | ALL final typesetting, templates, carousels, memes | canva.com | AI makes ingredients; Canva plates the dish |

**Iron rule:** AI generates *backgrounds and illustrations*; humans set *all
real type* in Canva with brand fonts. AI-rendered paragraphs look like AI and
erode exactly the trust this brand is built on.

**Consistency checklist before exporting anything:**
- [ ] Midnight background (or white inverse for FB)
- [ ] Exactly one accent color doing one job (green = go/win, red = no/loss)
- [ ] Mono font for anything that is a "receipt"
- [ ] Disclaimer strip if the graphic shows numbers, results, or screenshots
- [ ] Logo small, corner, never the hero
