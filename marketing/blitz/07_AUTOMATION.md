# 07 — Automation (AI + Make.com workflows)

Goal: everything repetitive runs itself; you keep the two things automation
must never touch — **judgment** (what to say) and **presence** (replies,
Reddit). Set up §1–§5 in Week 2; §6 when paid/Phase 3 starts.

Tool choices: **Make.com** (free tier, 1,000 ops/mo — enough) over Zapier
(same jobs, ~5× the price at volume) and over n8n (self-hosting is a
distraction right now; revisit at scale). AI: Claude (claude.ai) for long-form
and strategy, ChatGPT fine for variants. CapCut for video. Google
Sheets/Drive as the spine.

---

## §1 — Content generation (AI, weekly, ~30 min replaces ~3 hrs)

### 1.1 The Sunday batch prompt (paste into Claude, save as a Project)
Create a Claude Project called "FlipPulse Content" and put this in the
project instructions:

```
You are FlipPulse's content writer. FlipPulse is a done-for-you automated
trading bot for Kalshi's 15-minute BTC Up/Down markets (KXBTC15M). Facts you
may use: 9-layer entry doctrine (regime detection R²>0.65 trending-only,
order-book ≥70% imbalance with ≥$50 near-money depth, spot-momentum AGREE
required, Wilson CI performance guard after 20 trades, no trading UTC 0-4, no
trades <3min to expiry, 3-loss streak pause, maker-only orders 1¢ inside
spread); percentage-of-balance sizing (Conservative 5%/Balanced 10%/Aggressive
20% normal stakes, recovery sizing ~1/3 after a loss); every account starts in
paper mode; funds stay in the customer's own Kalshi account (CFTC-regulated);
Telegram alerts + /status; $150 setup + $99/mo flat, cancel anytime.

LAUNCH OFFER (lead with it early and often until 100 seats fill): the "Founders
100 Club" — the first 100 members join free ($150 setup + first month waived,
$0 today then $99/mo), and lock in Founder status for life: $99/mo price
grandfathered forever, permanent Founder badge, first access to new features.
Real hard cap of 100 seats (Stripe coupon FOUNDING100). Build conversion posts
AROUND the Club, don't bolt it on the end; cite remaining seats ("[N]/100 left")
for scarcity. CTA: "First 100 join free — $0 to start, then $99/mo for life.
go.flippulse.com". The offer is about price + status ONLY, never returns. After
the cap fills, revert to plain "$150 setup + $99/mo".

Voice: calm quant, dry humor, receipts over hype, honest about losses and
boring days. NEVER write: guaranteed, passive income, risk-free, get rich, any
specific return/percentage-profit claim, any dollar P&L figure. Every post
that references results must be about paper mode and say so. Where a post
shows numbers, end with: "Not financial advice. Trading involves risk."

House style: hooks in the first line, one idea per post, one CTA max, no
hashtag spam (X: 0-1, TikTok: 4-6, IG: 3-5).
```

Then each Sunday, one message:
```
This week's anchor topic: [e.g., "recovery-mode sizing"]. This week's real
events: [1-3 bullets: milestones, interesting logs, questions received].

Generate: (1) 3 X posts in our voice on the anchor, (2) 1 X thread (6-8
tweets) on the anchor, (3) 2 TikTok scripts (25s, hook+VO+shot list) — one
educational, one meme-format, (4) 3 IG captions, (5) 1 FB post, (6) 5 reply
drafts to this week's real comments: [paste comments]. Output in a table with
suggested asset IDs continuing from T60/V30.
```
Review, edit at least 20% (your fingerprints keep the voice real), paste into
the library file, schedule.

### 1.2 Trend-reaction prompt (when BTC/Kalshi news breaks)
```
News: [paste headline/link summary]. Draft the T46/T47/T48-style reaction posts
(X + FB) plus a 20s V29-style video script, using only facts above. Include
what the bot actually did today from this log excerpt: [paste 2-3 log lines].
```

### 1.3 SEO pages (one hour each, once)
For each cornerstone page ("Kalshi trading bot", "How Kalshi 15-minute BTC
markets work", "Kalshi API automated trading", "FlipPulse vs manual trading"):
```
Write a 1,200-word page targeting the query "[query]". Structure: H1, direct
2-sentence answer, H2 sections answering the People-Also-Ask variants, an
honest pros/cons section, FAQ with 5 Q&As, and a soft CTA to start in paper
mode. Plain, factual, zero hype; include the standard risk disclaimer verbatim
at the end.
```
Publish as static pages on the onboarding app's domain (add simple Flask
routes/templates, or host on a free Carrd/GitHub Pages subdomain if easier).

---

## §2 — Scheduling automation
Covered by Metricool (`06_SCHEDULER_SETUP.md`): auto-publish for X/TT/IG/FB,
notification-publish Stories, CSV bulk upload, failure push alerts. The only
scheduling automation to add here:

**Make.com Scenario A — "Content sheet → Metricool CSV"** (optional, 15 min):
Google Sheets (your weekly content tab) → Make **Google Sheets: Search rows**
(status = "approved") → **CSV: Create** → email it to yourself Sunday 4pm
(**Schedule** trigger) → you import to Metricool. Keeps the Sheet as the
single source of truth.

---

## §3 — Analytics & weekly reporting (fully automated)

**Make.com Scenario B — "Friday KPI digest":**
1. Trigger: **Schedule** — Fridays 3:00pm.
2. **Google Sheets: Get range** — reads this week's row of the KPI tracker
   (you filled platform numbers at 8am; Stripe/customer numbers pull below).
3. **OpenAI/Anthropic module** (Make has both): prompt:
   `Summarize this week's marketing KPIs vs last week for a solo founder in
   10 bullet lines: biggest win, biggest drop, what to double, what to kill,
   using these rules: [paste 09 §5 kill/double rules]. Data: {{sheet row}}`
4. **Email: Send** (or Telegram bot message to yourself): subject
   `FlipPulse Weekly Marketing Report W##`.

**Stripe → Sheet (customer/MRR numbers without logging in):**
Make Scenario C: **Stripe: Watch events** (`customer.subscription.created`,
`...deleted`) → **Google Sheets: Add row** to `Customers` tab (date, event,
plan). The KPI sheet's customer/MRR cells read from this tab via COUNTIF/SUMIF
(formulas included in the CSV template comments).

---

## §4 — Lead capture, email marketing & CRM

### 4.1 MailerLite setup (45 min, free to 1,000 subs)
1. mailerlite.com → sign up → verify domain (Settings → Domains → add the DNS
   records at Namecheap: SPF + DKIM they show you).
2. Create **Form** → "9 Rules" landing page (MailerLite hosts it free):
   headline `The 9 Rules Our Bot Checks Before Risking a Dollar`, sub `The
   actual FlipPulse entry doctrine, in plain English. Free PDF.`, one email
   field. Success action: deliver the PDF (make it: doctrine → Claude prompt
   `rewrite as a friendly 8-page plain-English PDF outline` → lay out in Canva
   → export PDF). **Launch-phase banner on this page (while seats remain):**
   `🎟 Founders 100 Club — the first 100 members join free: $0 to start, then $99/mo locked in for life. go.flippulse.com` (remove when the cap fills).
3. That form URL is `[lead magnet link]` everywhere in the library. Add it to
   Beacons as button 2.

### 4.2 Lead capture wiring
- Beacons button + link-in-bio → MailerLite form (native, no Make needed).
- Onboarding form signups: Make Scenario D — **Webhooks** (add a webhook POST
  to the Flask app on submit, or poll the operator Telegram alerts) →
  **MailerLite: Add subscriber** to group `customers`.

### 4.3 The 5-email nurture sequence (MailerLite → Automations → trigger:
joins group `lead-magnet`; one email every 2 days; templates — subject / core):
1. `Here's your doc (and the one thing to read first)` — deliver PDF; point at
   Layer 5 (regime) as the money page; PS: live feed t.me/flippulse.
2. `The screenshot most bot companies would never post` — a refusal log,
   explained in 5 sentences; CTA: follow the feed.
3. `Where your money sits (the only question that matters)` — custody
   explainer (FB03 content); CTA: reply with questions (replies = deliverability gold).
4. `Paper mode: the free trial that actually proves something` — TH06 content
   condensed; CTA (launch phase): `Join the Founders 100 Club — first 100 free: $0
   to start, then $99/mo locked in for life` → go.flippulse.com. (After the cap:
   `Start in paper mode — $150 setup + $99/mo`.)
5. `What $99/month actually buys (and when NOT to buy it)` — TH08 content +
   honest "don't sign up if..." list (money you can't lose / expecting
   guaranteed returns / want 50 trades a day). This email converts best
   precisely because of that list. Close with the Founders 100 Club nudge while
   seats remain (`[N]/100 left — Founders lock in $99/mo for life`). Every email
   footer: unsubscribe + full risk disclaimer (`11_COMPLIANCE_KIT.md` §1).

> **Add a launch-phase email 0** (send immediately on lead-magnet signup, before
> the sequence above, only while seats remain): subject `The Founders 100 Club is
> open (first 100 only)` — 4 lines: what the Club is ($0 to start, $99/mo locked
> in for life, permanent Founder status), the hard 100-seat cap with current
> count, one CTA to go.flippulse.com, and the risk disclaimer. Retire it when the
> cap fills so nobody is promised a closed offer.

### 4.4 Customer emails (retention + referral)
- **Monthly "Your bot this month"** (manual, 20 min/mo, MailerLite campaign to
  `customers`): what shipped, one doctrine deep-dive, reminder of /status and
  the pause command, referral paragraph (§8.5 of the library).
- **Day-14 check-in:** MailerLite automation on `customers` group, 14-day
  delay → the §8.5 testimonial/referral email.

### 4.5 CRM (don't buy one)
The CRM is a Google Sheet `FlipPulse CRM`, tabs: `Leads` (from MailerLite
export monthly), `Customers` (auto from Stripe via Scenario C), `Influencers`
(name, handle, size, status: contacted/replied/deal/live, terms), `Partners`.
At 500+ customers, graduate to Airtable (`10_SCALING_PLAN.md`).

---

## §5 — Inbox, files & engagement reminders

- **Google Drive structure** (create now):
  `/FlipPulse/Brand/` (logo, kit, templates) · `/Content/Week01..13/`
  (subfolders `Video/ Graphics/ Stories/ Shots/`) · `/UGC/` (customer
  screenshots + written permissions) · `/Reports/` (Friday digests) ·
  `/Legal/` (disclaimer texts, influencer agreements).
- **Screenshot pipeline (daily, 2 min):** your operator Telegram already
  receives every bot alert (`TELEGRAM_OPERATOR_CHAT_ID`). Each morning,
  forward the 1–3 most interesting alerts to your public channel
  t.me/flippulse (10 seconds each), and screenshot the best one to
  `/Content/WeekNN/Shots/` for the day's `[shot]` slots. This single habit
  feeds Pillar A forever.
- **Engagement reminders:** three phone alarms — 8:30am `X replies ×15`,
  12:45pm `comments sweep`, 8:00pm `community + log KPIs`. (Calendar events
  work too; alarms are harder to ignore.)
- **Unified inbox:** Metricool → **Inbox** tab aggregates IG/FB comments +
  DMs; X and TikTok natively (apps). Reply templates live in
  `03_POST_LIBRARY.md` §9 — keep them in a phone note for thumb-speed pasting.

---

## §6 — Paid amplification workflow (Phase 3 only)
1. Friday review flags a post with top-10% engagement AND a compliant creative
   (checklist `11_COMPLIANCE_KIT.md` §5).
2. FB/IG: Meta Ads Manager → Boost the existing post → objective Traffic (to
   go.flippulse.com) → audience: US, 25–54, interests "Kalshi", "prediction
   markets", "day trading", "Investing" → $10/day → 5 days. **Note:** Meta may
   classify this as a financial-services ad; complete any required advertiser
   verification it asks for, and never run creatives with result claims.
3. TikTok: Spark Ads on the organic post (TikTok Ads Manager → Spark Ad →
   authorize your own post) → same audience/budget.
4. Kill rule: CPC > $1.50 or zero signups after $50 spend → stop. Winner rule:
   signup CAC < $150 → raise to $20/day, never more than 2 ads live at once.
5. Log every dollar in the KPI sheet's `Spend` column — CAC/ROAS formulas use it.

---

## §7 — What is deliberately NOT automated
Reddit posts/comments (authenticity is the strategy) · replies to comments
(voice = trust) · Story interactive stickers (API limitation) · going-live
decisions on ads (spend needs judgment) · anything a customer reads 1:1
(DMs, support). Automation buys you the time to do these by hand.
