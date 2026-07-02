# FlipPulse — Pre-Onboarding Experience

A polished, **zero-technical-experience** setup experience that a customer
completes **before** they reach the onboarding form. Its whole job is to reduce
support requests: most customers get stuck creating a Kalshi API key, saving
the PEM, and making a Telegram bot / finding their Chat ID — so this walks them
through all of it, one picture at a time.

Everything here is **self-contained and static** (no build step to view, no
external CSS/JS/CDN). Internal links are relative, so the same files work three
ways: served by the Flask app, opened directly from disk, or rendered to PDF.

## What's in here

| File | What it is | Deliverable |
|---|---|---|
| `index.html` | **Landing page** — welcome, the 4 steps (Kalshi referral button, Telegram download buttons, start-guide, continue-to-form) | Landing page |
| `guide.html` | **Complete setup guide** — 10 sections + FAQ + troubleshooting, embedded screenshots, callouts, progress bar | Setup guide |
| `checklist.html` | **Printable Quick Start Checklist** — tick-boxes + a fill-in box for the 4 items | Checklist |
| `SETUP_GUIDE.md` | **Markdown** version of the guide (renders on GitHub, references the SVGs) | Markdown docs |
| `FlipPulse_Setup_Guide.pdf` | **PDF** of the full guide (rendered from `guide.html`) | Downloadable PDF |
| `FlipPulse_Quick_Start_Checklist.pdf` | **PDF** of the checklist | Printable PDF |
| `assets/*.svg` | **Annotated screenshots** — one per major step (red arrows, numbered badges, callouts) | Individual screenshots |
| `styles.css` | Shared stylesheet for the three HTML pages | — |
| `build_assets.py` | Regenerates every SVG in `assets/` | — |

### About the screenshots

The images in `assets/` are clean, reproducible **illustrations** of each screen
(drawn as SVG), not photographic captures. That is deliberate:

- they stay crisp at any size and embed perfectly in HTML **and** PDF,
- they never contain a real person's account data,
- when Kalshi or Telegram tweak their UI, you regenerate in seconds instead of
  re-screenshotting a dozen flows,
- each one uses the same visual language — a **red arrow + numbered badge** on
  the one thing to click, a **blue callout** naming it, a **dashed red box**
  around anything to copy.

## How a customer flows through it

```
/welcome/  (index.html)
   │  Step 1 → Create Kalshi account (your referral link)
   │  Step 2 → Install Telegram (Win/macOS/Linux/iPhone/Android)
   │  Step 3 → Open the guide  ─────────────►  /welcome/guide.html
   │                                              (+ /welcome/checklist.html to print)
   └► Step 4 → Continue to Customer Onboarding ─►  /   (the existing form)
```

## Served by the onboarding Flask app

`onboarding/app.py` serves this directory under **`/welcome/`**:

| URL | Serves |
|---|---|
| `/welcome/` | `index.html` (landing) |
| `/welcome/guide.html` | full guide |
| `/welcome/checklist.html` | printable checklist |
| `/welcome/FlipPulse_Setup_Guide.pdf` | the PDF |
| `/welcome/assets/…` | screenshots, css |

The existing form at `/` also links back to `/welcome/` for anyone who lands on
it directly. Send new customers to **`https://<your-onboarding-host>/welcome/`**.

> **The "Continue to Customer Onboarding" button links to `/`** — the form on the
> same service. If you ever host the guide on a *different* domain than the form,
> change that one `href="/"` (in `index.html` and `guide.html`) to the form's
> full URL.

## Regenerating

```bash
# 1) screenshots  → assets/*.svg
python onboarding/guide/build_assets.py

# 2) PDFs (headless Chromium — same tool the repo already uses for docs/*.pdf)
cd onboarding/guide
chromium --headless --no-pdf-header-footer \
  --print-to-pdf=FlipPulse_Setup_Guide.pdf            guide.html
chromium --headless --no-pdf-header-footer \
  --print-to-pdf=FlipPulse_Quick_Start_Checklist.pdf  checklist.html
```

Edit copy in `guide.html` / `SETUP_GUIDE.md`, re-render the PDF, and you're done.
Keep the two in sync when you change wording.

## Accessibility & design notes

- Light, high-contrast theme; brand accent gradient (`#7ef2a0 → #35cee6`).
- Every screenshot has descriptive `alt` text; callouts use text + colour (not
  colour alone) so they're readable for colour-blind users.
- Fully responsive (single-column on phones; the guide's section nav collapses).
- Print styles hide navigation and keep figures/callouts from breaking across
  pages, so `guide.html` and `checklist.html` also print cleanly from a browser.
