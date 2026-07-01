# 06 — Scheduling System (Metricool, click-by-click)

## §1 — The decision: Metricool. Here's the comparison that got there.

| Tool | Price for what we need | X | TikTok | IG (Reels+Stories) | FB | Analytics | Bulk upload | Best-time engine | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Metricool** | **Free → Starter ~$22/mo** | ✅ | ✅ direct publish | ✅ Reels; Stories via notification | ✅ | ✅ strong, incl. competitor tracking | ✅ CSV | ✅ per-account heatmap | **✅ CHOSEN** |
| Buffer | ~$30/mo for 5 channels | ✅ | ✅ | ✅ | ✅ | basic on cheap tiers | limited | generic | Clean but shallow analytics, pricier at multi-channel |
| Publer | ~$21/mo comparable | ✅ | ✅ | ✅ | ✅ | decent | ✅ | ok | Close #2; weaker analytics + heatmaps than Metricool |
| Later | ~$25/mo | limited X | ✅ | ✅ (IG-first) | ✅ | IG-centric | partial | IG-only strength | Built for IG aesthetics brands, weak for X-heavy plans |
| Hootsuite | $99/mo minimum | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4× the price for nothing we need at this stage |
| SocialBee | ~$29/mo | ✅ | ✅ | ✅ | ✅ | light | ✅ | category-based | Great evergreen recycling, weak analytics; we replicate recycling manually (§7) |
| Vista Social | ~$39/mo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Genuinely good (even has Reddit) — but Reddit must be manual anyway (strategy), so we won't pay the premium |

**Why Metricool wins for this exact operation:** cheapest tool that covers all
four scheduled platforms (Reddit is deliberately manual — see
`01_MASTER_MARKETING_PLAN.md` §9), has real analytics + a per-audience
best-times heatmap (which drives our Friday iteration loop), direct TikTok and
Reels publishing, and CSV bulk upload that matches our asset-ID workflow. One
dashboard, one login, ~$22/mo.

**When to re-evaluate:** at 1,000 customers / when you hire a social manager —
Vista Social or Hootsuite for team seats and approval flows (`10_SCALING_PLAN.md`).

---

## §2 — Account setup (one time, ~30 min)

1. Go to **metricool.com** → Sign up with your business Google account.
2. Choose the **Free** plan to start (upgrade to **Starter** when you connect
   the 5th account or need >50 scheduled posts/mo — you will in week 1, so
   realistically: upgrade day one, ~$22/mo, card in Settings → Subscription).
3. You land in your **Brand** (Metricool's word for a workspace). Rename it
   "FlipPulse": top-left brand menu → ⚙ → Brand name.

**Connect every account** (Settings → **Social connections**):
- **X:** click Connect on Twitter/X → log in as @flippulse → Authorize app.
- **Instagram:** MUST be a Business/Professional account linked to your FB
  Page first (done in `00_START_HERE.md` §B). Click Connect on Instagram →
  choose **Instagram Business** → log into Facebook → select the FlipPulse
  Page + IG account → allow all permissions (skipping permissions breaks
  Reels publishing).
- **Facebook:** Connect on Facebook → select the FlipPulse **Page** (not your profile).
- **TikTok:** Connect on TikTok → log in → **Allow** direct publishing
  permissions (lets Metricool post videos without you).
- **YouTube (optional):** Connect for Shorts scheduling.
- Reddit: **do not connect**, even where offered. Manual per strategy.

Install the **Metricool mobile app** (iOS/Android) — it's how Story
notifications and failure alerts reach you.

---

## §3 — Organizing content (folders + naming)

Metricool doesn't have deep folder systems; organization lives in Google Drive
(structure in `07_AUTOMATION.md` §5) and in **post naming**. Convention:

- Every scheduled post's first line of internal notes (or the start of the
  draft) carries its asset ID: `W3-TUE-XMID · TH03`.
- Videos uploaded to Metricool keep their filenames: `V04_receipt-read_TIKTOK.mp4`,
  `V04_receipt-read_CLEAN.mp4` (clean = for IG/YT).
- Drive mirrors the calendar: `/FlipPulse/Content/Week03/` contains everything
  Week 3 needs before Sunday scheduling.

---

## §4 — Scheduling a normal week (the Sunday 60-minute routine)

1. Open `02_CONTENT_CALENDAR_90D.md` → next week's table.
2. Metricool → **Planning** → click a time slot on the calendar grid.
3. For each X post: paste copy from `03_POST_LIBRARY.md` → attach graphic if
   the slot says `[shot]` (fresh screenshot!) → set date/time → **Schedule**.
   - Threads: Metricool supports X threads — click **+ Add tweet** inside the
     composer for each numbered tweet of a TH asset.
4. TikTok video slots: upload the `_TIKTOK.mp4` → paste TT caption from the
   script → schedule 6:00pm → publishing mode **Auto-publish**.
5. Reels: upload `_CLEAN.mp4` → paste the paired IG caption → toggle **Reel** →
   schedule 12:00pm → also tick **Share to feed**.
6. FB: paste FB asset → attach image → 1:00pm.
7. Stories: schedule as **notification-type** posts (Metricool pings your
   phone at 9am; you post the Story in-app in 30 seconds — Stories can't be
   fully auto-published by API).
8. Sanity pass: Planning view → **Week** — you should see 3 X + 1 TT + 1 Reel +
   1 FB + 1 Story per day (2 TT on Sat). Gaps are obvious visually.

## §5 — Bulk upload (the faster way once comfortable)

Metricool → Planning → **Bulk upload** (CSV):
1. Make a Google Sheet with columns: `Text, Date (YYYY-MM-DD), Time (HH:MM),
   Draft (FALSE), Network (twitter/facebook/instagram/tiktok), Media URL,
   Shortener (FALSE)`.
2. Fill a week (or month) of text posts straight from the library — fastest
   for X and FB text posts. Media URLs must be public links (use Drive
   share links set to "anyone with link", or upload media manually after import).
3. File → Download → CSV → Metricool Bulk upload → map columns → import →
   review in Planning view.
4. Keep videos/Stories manual (they need per-platform toggles anyway).

## §6 — Scheduling Reels and Stories, specifically
- **Reels:** always native upload of the clean export (no TikTok watermark),
  vertical 1080×1920, toggle Reel + Share to feed, cover image = thumbnail
  from template G-4.4 (upload as custom cover).
- **Stories:** notification workflow (above). Batch your 7 Story assets on
  Sunday into `/Content/WeekNN/Stories/`; when the 9am ping arrives, post,
  add the interactive sticker (polls/quizzes can't be scheduled — add live),
  done in under a minute.

## §7 — Evergreen recycling (SocialBee's feature, rebuilt free)
1. Google Sheet `FP Evergreen Bank`, tabs: `X-education`, `X-discipline`,
   `FB`, `hooks`. Paste in every library asset marked evergreen (T09–T25,
   T51–T58, FB04/06/08/10/12/13).
2. From Week 9 (per the calendar), reruns are official: each Sunday pick the
   next 3 rows top-down, give each a fresh first line or new screenshot, mark
   the row `used W##`, move to bottom. A cell comment holds performance notes.
3. Rule: an asset reruns no sooner than 5 weeks after last use, always with
   something fresh. (Metricool Starter has no autolists; this manual loop
   costs 10 min/week and keeps quality control human.)

## §8 — Monitoring failures
- Metricool app push notifications ON (app → profile → notifications →
  publishing errors). Failed posts show **red** in Planning.
- Daily 8am check (it's in the DOP): open app → Planning → today. Red item?
  Open → read error → usual causes: expired token (Settings → Social
  connections → Reconnect), video too long/format (re-export H.264 MP4),
  IG permission drop (reconnect via Facebook flow).
- If X posting fails silently: Settings → Social connections → X → Reconnect
  (tokens expire after password changes).

## §9 — Analytics & approvals in one dashboard
- **Analytics** tab per network: reach, impressions, engagement, follower
  delta, best posts. Every Friday: open Analytics → set range Mon–Fri → copy
  the 6 numbers the KPI sheet asks for (`09_METRICS_KPI_DASHBOARD.md` §3) —
  10 minutes.
- **Best times heatmap:** Planning → the darker the cell, the more YOUR
  audience is online. After 14 days of data, shift the §6-of-plan default
  slots to match the heatmap. Re-check monthly.
- **Link tracking:** always paste the dub.sh short links (per-platform UTM,
  from `00_START_HERE.md` §A) — Metricool link clicks + dub.co dashboard +
  GA-free simplicity.
- **Approvals (when you hire a VA):** Starter tier → have the VA schedule
  everything as **Draft**; your daily 8am check approves drafts (Planning →
  filter Drafts → review → Schedule). At real team scale, move to Vista
  Social/Hootsuite approval workflows (`10_SCALING_PLAN.md` §2).
