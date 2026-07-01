# 01 — Master Marketing Plan

The strategy document. Everything else in this folder executes what's defined
here. Each section ends with **WHY** — the reasoning, so you can adapt when
reality diverges from the plan.

---

## 1. What we're selling (say it the same way everywhere)

**One-liner:**
> FlipPulse is a done-for-you trading bot for Kalshi's 15-minute Bitcoin
> Up/Down markets. It watches all 96 daily markets, trades only when nine
> strict conditions line up, sends every decision to your Telegram — and it
> starts in paper mode, so you watch it work before any real dollar moves.

**Price:** $99 setup + $99/month. Cancel anytime. Funds stay in the customer's
own Kalshi account — FlipPulse never touches or holds money.

**The five product truths every piece of content is built from:**

| # | Truth | Why it markets well |
|---|---|---|
| 1 | **Paper mode first, always.** Every customer starts with fake money. | Kills the #1 objection ("is this a scam?") before it forms. Free-trial energy without a free trial. |
| 2 | **Funds never leave Kalshi**, a CFTC-regulated US exchange. Bot uses the customer's own API key. | Regulatory legitimacy is a moat. "CFTC-regulated" is a phrase no crypto casino can say. |
| 3 | **Nine layers must all pass or it refuses to trade.** Regime detection, order-book depth, momentum agreement, statistical performance guard. Zero-trade days are correct behavior. | Contrarian and memorable: "the bot that's proud of doing nothing." Every rival brags about trade volume; we brag about restraint. |
| 4 | **You see everything.** Live Telegram alerts, `/status` on demand, an EDGE JUSTIFICATION log line for every trade explaining exactly why it fired. | Radical transparency = content. The bot's own logs are an infinite feed of screenshots. |
| 5 | **Percentage sizing that adapts.** Stakes a % of the balance (Conservative 5% / Balanced 10% / Aggressive 20%), drops to recovery sizing after a loss. | Sophistication signal for the quant-curious; safety signal for the cautious. |

**WHY:** Consistency compounds. When five truths repeat across 500 posts,
strangers can recite your pitch. Scattered messaging is why most solo brands
never stick.

---

## 2. Brand positioning

**Category:** automated trading for regulated prediction markets.
**Against:** (a) crypto trading bots (3Commas, Cornix, random Telegram "signal
groups") and (b) doing it manually on Kalshi.

**Positioning statement:**
> For people who want systematic exposure to Bitcoin's short-term moves without
> staring at charts, FlipPulse is the managed trading bot that behaves like a
> risk manager, not a slot machine — because unlike hype bots, it's built on a
> published trading doctrine, starts on paper, and shows you every decision.

**Voice & tone:**
- **Calm quant, not hype bro.** Numbers, screenshots, receipts. Zero rocket emojis on claims (🚀 allowed only ironically).
- **Honest to a fault.** We post losing days. We post "0 trades today, here's why that's the system working."
- **Slightly wry.** "Our bot did nothing today. It's very good at that." Dry humor makes discipline shareable.
- **Founder-forward.** Posts come from a person building a thing, not a faceless brand. Build-in-public is the growth engine (§8).

**Words we own:** *discipline, doctrine, Pulse Engine, paper-first, receipts,
stand down, qualified setup.*
**Words we never use:** guaranteed, passive income, get rich, profits (as a
promise), "can't lose," moon. Full list: `11_COMPLIANCE_KIT.md`.

**WHY:** In a low-trust category, the trust-signaling brand doesn't need to
out-shout anyone — it just needs to be *findable* when a skeptic goes looking.
Positioning against the hype is cheaper and more defensible than positioning
against other calm brands, because there aren't any.

---

## 3. Target audience personas

### P1 — "Side-Hustle Sam" (primary, ~50% of content)
- 25–40, male-skewed, US. Has a Coinbase account, tried day-trading BTC, lost
  a bit, still believes. $500–$5,000 he'd deploy. Scrolls X and TikTok daily.
- **Pain:** no time + no discipline; FOMO-trades and regrets it.
- **Hook that works:** "The bot has rules you don't. Here's it refusing to trade at 2am."
- **Objection:** "Every bot is a scam." → Answer: paper mode + public log channel.
- **Found on:** X fintwit, TikTok #cryptotok, r/CryptoCurrency, r/Kalshi.

### P2 — "Data-Driven Dan" (the amplifier, ~20% of content)
- 28–45, engineer/analyst/quant-curious. Reads the doctrine doc for fun.
  Small deployer but **massive social proof value** — his quote-tweet carries weight.
- **Pain:** wants to build this himself, never ships it.
- **Hook:** the 9-layer checklist, Wilson confidence intervals, regime detection, maker-only execution. Technical threads.
- **Objection:** "68.8% backtest on a limited dataset, really?" → We literally publish the caveat. Honesty converts him.
- **Found on:** X (quant/dev Twitter), Hacker News adjacent, r/algotrading, r/quant.

### P3 — "Busy Professional Priya" (~20% of content)
- 30–50, professional income, no time, wants exposure with control. Values the
  pause button, alerts, and the $99 flat fee vs % fees.
- **Hook:** "You get a text every time it trades. You can pause it from your phone."
- **Objection:** safety of funds → CFTC-regulated exchange, funds never move, own API key.
- **Found on:** Instagram, Facebook, LinkedIn-ish content repurposed to FB.

### P4 — "Prediction-Market Pete" (~10% of content, highest intent)
- Already trades on Kalshi/Polymarket. Knows what KXBTC15M is. Smallest
  audience, hottest leads — often converts from a single Reddit comment.
- **Hook:** market microstructure talk — order-book imbalance ≥70%, $50 near-money depth, maker-only fills.
- **Found on:** r/Kalshi, Kalshi Discord, prediction-market X.

**WHY:** Four personas, one product story told at four altitudes. Content slots
in the calendar are tagged by persona so the mix stays deliberate instead of
drifting toward whichever persona is easiest to write for.

---

## 4. Messaging pillars (every post maps to exactly one)

| Pillar | Share of content | What it looks like |
|---|---|---|
| **A. Receipts** (transparency) | 30% | Telegram screenshots, EDGE JUSTIFICATION lines, daily paper-mode recaps, losing days posted with commentary |
| **B. Doctrine** (education) | 25% | How the 9 layers work, why zero-trade days happen, what regime detection is, Kalshi 101, binary-market math |
| **C. Discipline > Hype** (contrarian) | 20% | "Things our bot refuses to do", hype-bot autopsy threads, "most bots die of overtrading" |
| **D. Build-in-public** (founder story) | 15% | Customer count milestones, feature ships, mistakes made, revenue-adjacent updates (never customer P&L) |
| **E. Control & Safety** (objection killers) | 10% | Paper mode, pause command, funds-stay-on-Kalshi, CFTC-regulated, own API keys |

**WHY:** Pillars prevent the two classic failure modes: all-promo (audience
leaves) and all-value-no-ask (audience never converts). The ratio embeds a
~4:1 value-to-ask rhythm automatically.

---

## 5. Platform strategies (different algorithm, different game)

### X / Twitter — the home base (3 posts/day + heavy replies)
- **Algorithm reality:** reply-driven. Small accounts grow by being *the best
  reply* under big accounts, not by posting into the void. Threads and native
  images outperform links; links go in the reply below the post.
- **Play:** 1 educational/receipt post (morning), 1 engagement/contrarian post
  (midday), 1 screenshot/log post (evening). 15+ replies/day under fintwit,
  Kalshi, and BTC accounts. Weekly long-form doctrine thread pinned candidates.
- **Growth goal:** this is where P2 and P4 live and where virality is cheapest.

### TikTok — reach machine (1 video/day)
- **Algorithm reality:** every video is shown to a fresh test audience
  regardless of follower count; watch-time % and rewatches decide everything.
  First 1.5 seconds = 80% of the outcome.
- **Play:** screen-recording-driven "watch the bot decide" clips, POV memes
  about discipline, 20–35s. Text-on-screen hook in frame one. Trending audio
  at low volume under voiceover. CTA verbal + comment-pin (bio link locked
  until 1K followers).
- **Growth goal:** raw awareness for P1; expect 1 in 15 videos to pop — that's
  the model working, not failing.

### Instagram (Reels + Stories + carousels) — trust layer
- **Algorithm reality:** Reels reach non-followers; carousels get saved
  (saves = strongest ranking signal); Stories nurture existing followers and
  drive link taps (sticker link available at any size).
- **Play:** repurpose TikToks *re-exported without watermark* (CapCut → new
  export; watermarked reposts get suppressed), 2 educational carousels/week,
  daily Story (poll/quiz/screenshot + link sticker).
- **Growth goal:** P3 conversion surface; the grid is the "is this legit?"
  background check.

### Facebook — the quiet converter (1 post/day)
- **Algorithm reality:** organic Page reach is weak, BUT (a) FB Groups reach is
  strong, (b) the audience skews 35+ with money, (c) shares travel far.
- **Play:** 1 page post/day (repurposed IG content + longer text), join 5–8
  relevant groups (Kalshi traders, prediction markets, side-hustle finance,
  BTC groups) and contribute genuinely 3×/week. Page exists mostly to look
  alive and retarget later with ads.
- **Growth goal:** P3, and cheap credibility ("they're everywhere").

### Reddit — highest-trust, highest-risk (2–3 contributions/week, MANUAL only)
- **Algorithm reality:** Reddit *is* the anti-marketing platform. Self-promo
  gets nuked; genuine expertise gets worshipped and ranks on Google for years.
- **Play (strict):** Weeks 1–2 comment-only (build karma). From week 3: 1
  value post/week in r/Kalshi or r/algotrading (strategy breakdowns, "what I
  learned building a 15-min BTC bot" — doctrine content with **no link**;
  mention FlipPulse only in profile or when asked). Answer every "is there a
  bot for Kalshi?" thread — those are purchase-intent searches.
- **Growth goal:** P4 conversions + evergreen SEO (Reddit threads rank for
  "Kalshi trading bot" searches).

**WHY each platform gets different content:** X rewards text + conversation;
TikTok rewards retention; IG rewards saves; FB rewards shares in groups;
Reddit rewards expertise and punishes promotion. One asset, five native
re-expressions — that's the repurposing workflow (§11), not copy-paste.

---

## 6. Posting frequency & best times (all times US Eastern)

| Platform | Frequency | Slot 1 | Slot 2 | Slot 3 | Notes |
|---|---|---|---|---|---|
| X | 3/day + 15 replies | 8:15am | 12:30pm | 7:30pm | Threads: Tue & Thu 12:30pm |
| TikTok | 1/day (2 on Sat) | 6:00pm | (Sat 11am) | — | Finance audience scrolls evenings |
| Instagram Reels | 1/day | 12:00pm | — | — | + daily Story 9am; carousel Wed/Sun |
| Facebook | 1/day | 1:00pm | — | — | Groups: Mon/Wed/Fri manual |
| Reddit | 2–3/wk | varies | — | — | Manual only, never scheduled |
| Telegram channel | live | auto | — | — | Bot forwards paper trades in real time |

Rules: these are starting points. After 14 days, Metricool's "Best times"
heatmap (built from *your* audience) overrides this table — check it every
Friday (`09_METRICS_KPI_DASHBOARD.md` §5).

**WHY:** Finance content peaks pre-market (7–9am ET), lunch (12–1pm), and
post-work (6–9pm). Consistency matters more than perfection — the algorithm
rewards accounts that post daily for 60+ days far more than accounts that nail
the perfect hour twice a week.

---

## 7. Funnel

```
   AWARENESS            CONSIDERATION              CONVERSION            RETENTION/REFERRAL
TikTok/Reels/X  ──►  Profile & pinned post  ──►  go.flippulse.com  ──►  Customer Telegram bot
FB/Reddit            t.me/flippulse (live         onboarding form        monthly check-in email
                     paper-trade channel)         Stripe $99+$99/mo      referral offer (§10)
                     free "How it decides"
                     doc (email capture)
```

**Stage mechanics:**
1. **Hook** (video/post) → "see how it decides" curiosity.
2. **Proof** — the Telegram channel `t.me/flippulse` republishes the bot's own
   paper-mode alerts, timestamped, unedited. This is the consideration asset;
   push everyone there. It costs nothing and no competitor can fake it daily.
3. **Capture** — the free doc *"The 9 Rules Our Bot Checks Before Risking a
   Dollar"* (a cleaned-up doctrine excerpt; build it as a Canva PDF, gate it
   with MailerLite — setup in `07_AUTOMATION.md` §4). Email nurture: 5-email
   sequence, written in `07_AUTOMATION.md` §4.3.
4. **Convert** — onboarding form → Stripe. The paper-mode start *is* the trial.
5. **Retain** — the product's own Telegram alerts are daily retention touches.
   Monthly "your bot this month" email (template in `07_AUTOMATION.md` §4.4).
6. **Refer** — §10.

**WHY a Telegram channel instead of a landing page as the proof asset:** a
landing page says what you claim; a channel shows what happened, in public,
with timestamps. For a trust-poor category, *verifiable* beats *pretty*.

---

## 8. Organic growth strategy & the build-in-public engine

The account that grows is "founder building a disciplined trading bot in
public," not "brand posting features."

Weekly build-in-public beats (rotates in calendar):
- **Milestone Monday** (D-pillar): customers count, ships, lessons.
- **Doctrine Tuesday**: one layer of the 9-layer checklist explained.
- **Receipts Wednesday**: this week's paper-mode log excerpts, wins AND losses.
- **"It said no" Thursday**: screenshot of a blocked trade + the reason line.
- **Founder Friday**: what broke, what I fixed, what's next.

Engagement mechanics (the 45 min/day in the DOP):
- 15 quality replies/day on X under accounts ≥10K followers in fintech/
  prediction markets (target list in `03_POST_LIBRARY.md` §8.4).
- Reply to 100% of comments on our own posts within 12h for the first 60 days.
- 10 thoughtful TikTok/IG comments/day on niche-adjacent videos (comments on
  rising videos harvest profile visits).

**WHY:** Sub-10K accounts get more reach from replies than posts. Build-in-
public converts the founder's time into content for free, and it makes the
brand impossible to fake — which is the whole positioning.

---

## 9. Reddit & community strategy (the trust play)

- Weeks 1–2: comment-only in r/Kalshi, r/algotrading, r/CryptoCurrency,
  r/passive_income (carefully), r/sidehustle. Target 200+ comment karma.
- Week 3+: one genuinely useful post/week (pre-written in `03_POST_LIBRARY.md`
  §7 — they are real value posts, not ads).
- Always: search Reddit weekly for "Kalshi bot", "Kalshi automated",
  "prediction market bot" — answer every thread helpfully; mention FlipPulse
  only when directly relevant, with a risk caveat, max 1 link.
- Kalshi's own Discord: be a known helpful member; never drop links unprompted.
- 10-to-1 rule: ten non-promotional contributions per one self-referential one.

**WHY:** One well-received Reddit post in r/Kalshi is worth 50 TikToks in
conversions, and threads rank on Google for the exact queries buyers type. But
the same post written as an ad gets removed and the account banned — hence the
karma-first runway and the 10:1 rule.

---

## 10. Referral, influencer, partnership & UGC strategies

**Referral (start Day 30):**
- Offer: *give a month, get a month.* Referred friend gets $99 setup waived;
  referrer gets one month free. Mechanic: "reply STOP… no — just tell them to
  put your Telegram handle in the 'how did you hear about us' box" — zero
  software needed at this scale; upgrade to Rewardful ($49/mo) at 100+ customers.
- Prompt it in the monthly customer email + after every visible paper-mode win.

**Influencer outreach (start Day 21, budget $0–500/mo):**
- Targets: 10–100K-follower finance/prediction-market creators (micro, high
  trust). List-building instructions + full outreach DM/email scripts in
  `03_POST_LIBRARY.md` §8.
- Offer ladder: (1) free account + affiliate 20% recurring for 6 months →
  (2) flat $150–400 per dedicated video for proven converters. Never pay
  upfront for "exposure."
- Non-negotiable: they must disclose (#ad) and must not make profit claims —
  send them `11_COMPLIANCE_KIT.md` §4 (creator one-pager).

**Partnerships:**
- Kalshi-adjacent newsletters (prediction-market newsletters, small fintech
  Substacks): offer a genuinely good guest post ("How 15-minute BTC markets
  actually work") + one mention. Scripts in `03_POST_LIBRARY.md` §8.3.
- Cross-promo with non-competing tools for the same audience (portfolio
  trackers, Kalshi analytics dashboards).

**UGC:**
- Ask every customer at day 14: "screenshot your favorite bot alert, tag
  @flippulse, we'll feature you" (repost = social proof loop).
- Rules: only paper-mode or non-dollar screenshots get reposted publicly
  (compliance §3); testimonial requests use the template in
  `03_POST_LIBRARY.md` §8.5 and must include the required disclaimer.

**WHY micro over macro influencers:** at $99/mo price point, conversion needs
trust, not reach. A 30K-follower Kalshi YouTuber converts better than a 2M
crypto influencer, at 1/50th the price — and recurring affiliate aligns them
with retention, not hit-and-run promotion.

---

## 11. Email, SEO, content flywheel & repurposing workflow

**Email (from Week 2):**
- Lead magnet: *"The 9 Rules Our Bot Checks Before Risking a Dollar"* (PDF).
- MailerLite free tier; 5-email nurture sequence + weekly "Paper Trade Weekly"
  digest (the week's most interesting bot decisions — content already exists
  in the Telegram channel). Templates: `07_AUTOMATION.md` §4.
- **WHY:** email is the only audience we own if any platform bans finance
  content overnight (it happens).

**SEO (slow burn, 1 hr/week):**
- The onboarding site gets 4 cornerstone pages (write with the AI prompts in
  `07_AUTOMATION.md` §2.3): "Kalshi trading bot", "How Kalshi 15-minute BTC
  markets work", "Kalshi API automated trading", "FlipPulse vs manual trading".
- Reddit posts + YouTube Shorts titles target the same queries.
- **WHY:** "kalshi trading bot" is a low-volume, ultra-high-intent query with
  almost zero competition. Owning it is cheap and permanent.

**Content flywheel (the whole system on one line):**
> The bot's own logs → screenshots → posts → questions from comments → next
> week's content topics → doctrine explainers → email digest → customers →
> their bot's logs → more receipts.

**Repurposing workflow (1 asset → 9 outputs), run every Sunday:**
1. Pick the week's "anchor" (one doctrine concept or one standout log).
2. Film 1 TikTok about it (script formulas in `04_VIDEO_SCRIPTS.md` §1).
3. CapCut export ×2 (TikTok version, clean version) → IG Reel + YT Short.
4. Transcript → X thread (5–8 tweets).
5. Thread condensed → 1 standalone tweet + 1 FB post.
6. Thread → IG carousel (Canva template `05_GRAPHICS_PROMPTS.md` §4).
7. Best comment/question → next day's engagement post.
8. Everything → Friday email digest paragraph.
9. If it performed top-20%: → Reddit-safe long-form version (no links).

**WHY:** creation is the bottleneck for a one-person team. One good idea,
expressed natively nine ways, is a 20-person department's output at a
one-person cost.

---

## 12. Phased 90-day rollout

| Phase | Days | Focus | Exit criteria |
|---|---|---|---|
| **1. Foundation** | 1–14 | All accounts live, daily cadence holds, Telegram proof channel running, Reddit karma building | 14-day posting streak; 250+ combined followers |
| **2. Traction** | 15–45 | Double down on best-performing format; launch email capture + lead magnet; start influencer outreach; first Reddit value posts | 1 video >10K views; 100 email subs; 15 customers |
| **3. Amplify** | 46–75 | Referral program live; 2–3 micro-influencer deals; test $10–20/day paid boosts on proven organic winners (FB/IG + TikTok Spark Ads only on compliant creatives) | 40 customers; CAC < $150 |
| **4. Systematize** | 76–90 | Automate reporting; hire VA for scheduling/comments ($400–600/mo); document what works into V2 playbook | 75 customers; 10 hrs/wk founder time |

**WHY paid comes in Phase 3, not Day 1:** paid traffic amplifies a message that
already converts organically. Spending before organic proof means paying to
find out your hook is wrong. Boosting proven winners is the only intelligent
spend at this budget.
