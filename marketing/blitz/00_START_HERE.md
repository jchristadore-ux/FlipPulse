# FlipPulse — 90-Day Social Media & Marketing Blitz
## Operating Manual — START HERE

**Launch date: Monday, July 6, 2026.**
**Campaign window: July 6 → October 4, 2026 (13 weeks / 90 days).**

This folder is a complete, execution-ready marketing operation. It is written so
that you — or a virtual assistant with zero context — can run it step-by-step.
Nothing in here is "advice." Everything is a task, a template, a script, or a
piece of copy you paste.

---

## Executive Summary

**The business:** FlipPulse is a done-for-you automated trading bot for Kalshi's
15-minute Bitcoin Up/Down markets. $150 setup + $99/month. Every customer starts
in paper mode. Funds never leave the customer's own Kalshi account (Kalshi is a
CFTC-regulated US exchange). The bot reports every decision to the customer's
own Telegram.

**Launch offer — the "Founders 100 Club":** the first 100 members join free — the
$150 setup fee **and** first month are waived ($0 today, then $99/mo), and every one
of them locks in **Founder status for life**: their $99/mo price is grandfathered
forever, they keep a permanent Founder badge, and they get first access to everything
we ship. It's a $249-off-first-invoice Stripe coupon (`FOUNDING100`) capped at 100
redemptions; lead every launch-phase post with it — **early and often, until the 100
seats are gone** (`03_POST_LIBRARY.md` §2.0) — then drop it once the cap is hit. See
`01_MASTER_MARKETING_PLAN.md` §1 for the framing and `ADMINISTRATOR_ONBOARDING.md` §9a-i
for the Stripe/onboarding wiring.

**The strategy in one paragraph:** We win by being the *most transparent,
most disciplined* voice in a niche full of hype. Trading-bot marketing is a
credibility desert — everyone screams "guaranteed profits" and gets ignored (or
banned). FlipPulse does the opposite: we publish the bot's actual decision logs,
we brag about the days it *refuses* to trade, we lead every funnel with a free
paper-mode education angle, and we let the 9-layer entry doctrine do the
selling. Radical transparency is both our compliance shield and our viral hook.

**The engine:** 3 posts/day on X, 1–2 short videos/day across TikTok +
Instagram Reels, 1 Facebook post/day, 2–3 genuinely useful Reddit contributions
per week (never spam), all flowing to one CTA: *"Watch it trade paper money
first — flippulse link in bio."* One scheduler (Metricool), one content
library (this folder), one weekly 2-hour batching session, ~45 minutes/day of
live engagement.

**90-day targets:** 5,000+ followers combined, 500,000+ organic impressions,
2,000 site visits/mo, 300 email/Telegram-channel subscribers, **75 paying
customers by Day 90** (≈$7.4K MRR). Full KPI ladder in `09_METRICS_KPI_DASHBOARD.md`.

---

## Table of Contents

| File | What it is | When you use it |
|---|---|---|
| `00_START_HERE.md` | This file: summary + pre-launch setup checklist | Read first, complete before Monday |
| `01_MASTER_MARKETING_PLAN.md` | Strategy: positioning, personas, pillars, funnel, growth loops | Read once, revisit monthly |
| `02_CONTENT_CALENDAR_90D.md` | Day-by-day 90-day calendar (every slot mapped to an asset ID) | Every week when batching |
| `03_POST_LIBRARY.md` | Every post, fully written: bios, tweets, threads, captions, Reddit posts, replies, hashtags | Every week when batching |
| `04_VIDEO_SCRIPTS.md` | 30 full video scripts + 60 platform-specific variants (hooks, shots, edits, captions) | Filming days (Sun/Wed) |
| `05_GRAPHICS_PROMPTS.md` | Copy-paste AI image prompts (Midjourney, ChatGPT, Canva, Ideogram) + brand kit | When creating graphics |
| `06_SCHEDULER_SETUP.md` | Metricool chosen + full click-by-click setup and bulk-upload workflow | One-time setup, then weekly |
| `07_AUTOMATION.md` | Make.com / AI workflows: content gen, lead capture, email, reporting | One-time setup |
| `08_DAILY_OPERATING_PROCEDURE.md` | The daily/weekly/monthly checklist you actually run | Every single day |
| `Run_the_Blitz.xlsx` | **The daily execution cockpit** — one tab per week, every task in clock order (`RUN_THE_BLITZ.md` explains it) | **Open it every morning** |
| `09_METRICS_KPI_DASHBOARD.md` | KPI definitions, tracking sheet, 30/60/90-day targets | Friday reviews |
| `kpi_tracker_template.csv` | Import into Google Sheets — your dashboard | One-time import |
| `10_SCALING_PLAN.md` | What changes at 100 / 500 / 1,000 / 5,000 / 10,000 customers | When milestones hit |
| `11_COMPLIANCE_KIT.md` | Required disclaimers, banned phrases, platform policy rules | **Before posting anything** |

---

## Pre-Launch Checklist (complete by Sunday July 5)

Work top to bottom. Estimated total time: 6–8 hours across the week.
Everything below has detailed instructions in the file referenced.

### A. Infrastructure (Day 1 — ~90 min)

- [ ] **Domain.** Buy `flippulse.com` (or `.io`/`.app` if taken) at Namecheap
      (namecheap.com, ~$10/yr). Point a subdomain `go.flippulse.com` at your
      Railway onboarding app (Railway → onboarding service → Settings →
      Networking → Custom Domain, then add the CNAME Namecheap shows you).
      Every link in every post in this playbook says `go.flippulse.com` —
      replace with your real URL if different.
- [ ] **Link-in-bio.** Create a free Linktree alternative: use **Beacons.ai**
      (free, better analytics). Account at beacons.ai → username `flippulse`.
      Add 3 links: "Start in Paper Mode →" (onboarding URL), "How the bot
      decides (free doc)", "Watch a live decision log". Bio copy is in
      `03_POST_LIBRARY.md` §1.
- [ ] **UTM links.** In Google Sheets, make a tab with these 6 links (used
      everywhere; they make the dashboard work):
      `go.flippulse.com/?utm_source=x&utm_medium=social&utm_campaign=blitz90`
      — repeat with `utm_source=` `tiktok`, `instagram`, `facebook`, `reddit`,
      `email`. Shorten each at **dub.co** (free) to `dub.sh/fp-x`, `dub.sh/fp-tt`, etc.

### B. Social accounts (Day 1–2 — ~2 hrs)

Create each with the same handle. First choice `@flippulse`; fallback
`@flippulsehq`. Use the same profile photo (logo prompt in
`05_GRAPHICS_PROMPTS.md` §2.1) and the exact bios from `03_POST_LIBRARY.md` §1.

- [ ] **X (Twitter):** x.com → Sign up with business email. Immediately buy
      **X Premium** ($8/mo) — required for reply visibility, longer posts, and
      analytics. This is the #1 platform in this plan.
- [ ] **TikTok:** tiktok.com → sign up → switch to **Business Account**
      (Profile → Menu → Settings → Account → Switch to Business Account →
      category "Finance"). Note: link-in-bio requires 1K followers; until then
      the CTA is "link on our X/IG @flippulse."
- [ ] **Instagram:** instagram.com → sign up → Settings → Account type →
      **Professional → Business** → category "Financial Service". Connect it to
      the Facebook Page (next step) when prompted.
- [ ] **Facebook:** facebook.com/pages/create → Page name "FlipPulse" →
      category "Financial Service". Fill the About section with the long bio
      (`03_POST_LIBRARY.md` §1.4).
- [ ] **Reddit:** reddit.com → create account `FlipPulse_Founder` (personal-
      feeling names outperform brand names on Reddit). **Do NOT post any promo
      for 2 weeks** — the account needs comment karma first. Rules in
      `01_MASTER_MARKETING_PLAN.md` §9 and `03_POST_LIBRARY.md` §7.
- [ ] **YouTube (bonus, 10 min):** Same videos you make for TikTok get
      re-uploaded as Shorts. Create channel "FlipPulse" at youtube.com.
- [ ] **Telegram public channel (the "product demo as content" weapon):**
      In Telegram → New Channel → "FlipPulse Paper Trades (Live)" → public →
      t.me/flippulse. You'll forward your own bot's paper-mode alerts here.
      This is the single most persuasive asset we have: a public, timestamped,
      unedited feed of the bot's real decisions. Every platform bio links to it.

### C. Tools (Day 2 — ~1 hr, ~$40/mo total)

| Tool | What for | Where | Cost |
|---|---|---|---|
| **Metricool** | Schedules everything (X, TikTok, IG, FB, YT) | metricool.com | Free to start; **Starter $22/mo** when you connect all accounts |
| **CapCut (desktop)** | All video editing, auto-captions | capcut.com/download | Free |
| **Canva Pro** | Graphics, carousels, thumbnails | canva.com | $15/mo (Pro needed for brand kit + resize) |
| **Claude / ChatGPT** | Weekly content generation (prompts provided) | claude.ai / chat.openai.com | you likely have this |
| **dub.co** | Short links + click analytics | dub.co | Free |
| **Beacons** | Link in bio | beacons.ai | Free |
| **Make.com** | Automation (set up in week 2, not required for launch) | make.com | Free tier |
| **MailerLite** | Email list (set up in week 2) | mailerlite.com | Free to 1,000 subs |

Skip for now: Buffer, Hootsuite, Later, etc. — comparison and why Metricool
wins is in `06_SCHEDULER_SETUP.md` §1.

### D. Content batch #1 (Day 3–5 — ~4 hrs)

- [ ] Generate the logo + 10 launch graphics using `05_GRAPHICS_PROMPTS.md`.
- [ ] Film Video Batch 1 = scripts V01–V07 from `04_VIDEO_SCRIPTS.md`
      (one ~90-minute session; they're 20–45s each, mostly screen recordings).
- [ ] Load Week 1 posts into Metricool per `06_SCHEDULER_SETUP.md` §5
      (all copy is pre-written in `03_POST_LIBRARY.md`; the calendar tells you
      which asset goes in which slot).
- [ ] Set up the KPI sheet: import `kpi_tracker_template.csv` into Google
      Sheets (per `09_METRICS_KPI_DASHBOARD.md` §2).

### E. Legal / compliance (Day 5 — 30 min, mandatory)

- [ ] Read `11_COMPLIANCE_KIT.md` fully. It is short and it will keep your
      accounts alive and your business out of trouble.
- [ ] Add the standard risk disclaimer to: Beacons page, onboarding form
      footer, every platform bio ("Not financial advice. Trading involves risk
      of loss."), and the Telegram channel description.

---

## How to run the machine (the 10,000-ft view)

1. **Sunday (2 hrs):** Batch-film next week's videos; schedule the whole week
   in Metricool from the calendar + library.
2. **Every day (45 min total):** Morning 15 min engagement sprint, midday
   10 min replies, evening 20 min community + log the day's numbers.
   Exact checklist: `08_DAILY_OPERATING_PROCEDURE.md`.
3. **Friday (30 min):** Fill the KPI sheet, kill what's not working, double
   what is. Rules for that decision: `09_METRICS_KPI_DASHBOARD.md` §5.
4. **Monthly:** Review against 30/60/90 targets; execute the next phase of
   `01_MASTER_MARKETING_PLAN.md` §12 (phased rollout).

> **The one rule that outranks everything:** never publish a profit claim,
> a projected return, or the word "guaranteed." The full banned list is in
> `11_COMPLIANCE_KIT.md`. Transparency-first isn't just safer — in this niche
> it converts better, because every competitor is screaming and nobody
> believes them.
