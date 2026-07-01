# 09 — Metrics & KPI Dashboard

One Google Sheet, three tabs, ten minutes on Friday. Import
`kpi_tracker_template.csv` (this folder) → Google Sheets → File → Import →
Upload → "Insert new sheet(s)". Then duplicate the weekly block 13×.

## §1 — What we track and why

| Metric | Source | Why it earns a column |
|---|---|---|
| Reach / Impressions (per platform) | Metricool Analytics | Raw top-of-funnel; tells you if the algorithm is feeding you |
| Follower count & weekly growth | Metricool | Compounding audience; growth *rate* matters more than the count |
| Engagement rate (eng ÷ reach) | Metricool | Content quality signal — reach can be bought, engagement can't |
| Video watch time / completion % | TikTok Studio, IG insights | The #1 input to short-video distribution |
| Shares & saves | per app | The two signals algorithms weight most; saves = IG gold |
| Comments | per app | Community heat + tomorrow's content fuel |
| Link clicks (per platform) | dub.co dashboard | The bridge metric: attention → traffic |
| Site visits | onboarding app / dub.co | Funnel top of the money section |
| Email signups | MailerLite | Owned audience (platform-ban insurance) |
| Telegram channel members | Telegram | Proof-channel growth = consideration-stage depth |
| Signups started / completed | Stripe + Customers tab | Conversion truth |
| New customers / churned | Stripe (auto via Make Scenario C) | The number the whole blitz exists for |
| MRR | Stripe | (customers × $99) + setup fees this month |
| CAC | Spend ÷ new customers | Keeps paid honest; organic-only weeks CAC = your time |
| ROAS (paid only) | attributed revenue ÷ ad spend | Boost kill/scale decisions |

**Vanity trap warning:** followers and impressions are diagnostic, not goals.
The Friday decision only ever optimizes the chain
*watch-time → clicks → signups*.

## §2 — Sheet structure (matches the CSV)
- **Tab `Weekly`** — one row per week × the columns above (per-platform reach
  groups, then funnel, then money). Conditional format: week-over-week ▲ green
  / ▼ red (Format → Conditional formatting → custom formula vs prior row).
- **Tab `Daily`** — 5-minute evening log: date, followers ×5, clicks, signups,
  notes ("V10 spiking on TikTok").
- **Tab `Customers`** — auto-filled by Make Scenario C from Stripe events;
  Weekly tab reads it with COUNTIFS.

## §3 — The Friday fill (10 min)
Metricool → Analytics → date range Mon–Sun → per network copy: impressions,
engagement, follower delta, top post. dub.co → clicks per short link.
MailerLite → new subs. Telegram → member count. Stripe tab auto. Paste row,
read the conditional colors, go to §5.

## §4 — Targets: 30 / 60 / 90 days

| Metric | Day 30 (Aug 4) | Day 60 (Sep 3) | Day 90 (Oct 4) |
|---|---|---|---|
| X followers | 500 | 1,500 | 3,000 |
| TikTok followers | 600 | 2,000 | 4,000 |
| IG followers | 300 | 900 | 2,000 |
| FB page likes | 150 | 400 | 800 |
| Combined monthly impressions | 100K | 300K | 600K |
| Avg engagement rate | ≥3% | ≥4% | ≥4% |
| ≥1 video over | 10K views | 50K views | 100K views |
| Telegram channel members | 75 | 250 | 600 |
| Email subscribers | 100 | 250 | 500 |
| Site visits / month | 600 | 1,500 | 3,000 |
| **Customers (cumulative)** | **15** | **40** | **75** |
| MRR | ~$1.5K | ~$4.0K | ~$7.4K |
| Blended CAC | <$200 | <$150 | <$120 |
| Churn | <8%/mo | <6%/mo | <5%/mo |

These are ambitious-but-sane for a from-zero solo blitz (visit→signup ~2–3%,
follower→visit ~10%/mo). The business model's "100 by month 6" needs ~17/mo —
this plan front-loads harder because the blitz IS the growth engine.

## §5 — Friday kill/double rules (mechanical, no vibes)
- **DOUBLE:** any format/topic in the top 10% of its platform two weeks
  running → +1 weekly slot next week (swap out the bottom performer).
- **KILL:** any recurring format below the account's median engagement 3 weeks
  running → retire it; backfill from the extra-ideas lists (04 §3–4).
- **CLICKS RULE:** platform with the best click→signup rate gets your best
  `[shot]` content next week, regardless of its follower count.
- **PAID:** CPC > $1.50 or $50 spent with 0 signups → kill. CAC < $150 →
  scale +$10/day.
- **Never kill:** the daily receipts habit or the reply quota — they're the
  substrate, not an experiment. Judge them quarterly.

## §6 — If you miss targets 2 weeks straight (diagnosis tree)
1. **Impressions low?** → hooks problem. Next week: film only formats F1/F3
   with hooks from the §11 hook bank; post 2 TikToks/day for 7 days as a probe.
2. **Impressions fine, engagement low?** → content is generic. More receipts
   (`[shot]` posts), fewer abstractions; every post names a number from a log.
3. **Engagement fine, clicks low?** → CTA problem. Push the proof channel
   (lowest friction) instead of the signup; check bio links on every platform.
4. **Clicks fine, signups low?** → funnel problem. Watch 3 people (friends)
   try the onboarding form cold; fix the top confusion; check the form loads
   fast on mobile; make sure pricing + paper-mode are above the fold.
5. **Signups fine, churn high?** → product/expectation gap. Interview 3
   churned customers; usually the fix is expectation-setting content (more
   T24/"zero-trade days" education, sooner in the funnel).
