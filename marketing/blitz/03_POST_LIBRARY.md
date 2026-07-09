# 03 — Post Library (every word, ready to paste)

Every asset has an ID (e.g., `T14`, `TH03`, `IG07`, `FB05`, `R02`). The 90-day
calendar (`02_CONTENT_CALENDAR_90D.md`) schedules assets by ID. Paste as-is;
replace `go.flippulse.com` / `t.me/flippulse` if your URLs differ.

**Compliance reminder:** never edit a post to add a return figure, a dollar
P&L, or a promise. If you write new posts, run them against `11_COMPLIANCE_KIT.md` §2.

---

## §1 — Bios & profile setup

### 1.1 X (Twitter) — @flippulse
- **Name:** FlipPulse — trading bot for Kalshi
- **Bio:**
  `Automated bot for Kalshi's 15-min BTC Up/Down markets. 9 checks before every trade. Starts in paper mode. Every decision on your Telegram. Not financial advice.`
- **Location:** United States · **Website:** `go.flippulse.com`
- **Header image:** prompt G-2.2 in `05_GRAPHICS_PROMPTS.md`.

### 1.2 TikTok — @flippulse
`The trading bot that mostly says no 🤖\n9 rules. Paper mode first. Kalshi (CFTC-regulated).\nNot financial advice ⚠️`

### 1.3 Instagram — @flippulse
- **Name field (searchable):** FlipPulse | Kalshi Trading Bot
- **Bio:**
  `🤖 Automated 15-min BTC trading on Kalshi`
  `🧠 9 checks before every trade`
  `📄 Starts in paper mode — watch it think first`
  `⚠️ Not financial advice. Trading involves risk.`
  `👇 See it decide, live`
- **Link:** beacons.ai/flippulse

### 1.4 Facebook Page — About (long)
`FlipPulse is a done-for-you trading bot for Kalshi's 15-minute Bitcoin Up/Down markets. It monitors all 96 daily markets, and only places a trade when nine strict conditions pass — market regime, order-book depth, momentum agreement, statistical performance checks, and more. Most hours, it does nothing. That's the point.

Every customer starts in paper (simulated) mode. Your funds stay in your own Kalshi account — a CFTC-regulated US exchange — and every decision the bot makes is sent to your own Telegram in real time. Pause any time with one tap.

$150 setup + $99/month. Cancel anytime.

FlipPulse is software, not an investment adviser. Nothing we publish is financial advice. Trading involves risk, including loss of principal. Past performance — real or simulated — does not guarantee future results.`

### 1.5 Reddit — u/FlipPulse_Founder profile
`Building FlipPulse — an automated bot for Kalshi's 15-min BTC markets. I post about market microstructure, discipline, and what I learn. Happy to answer questions. Nothing I post is financial advice.`

### 1.6 Telegram channel — t.me/flippulse description
`Live, unedited paper-mode feed from a FlipPulse bot. Every alert you see here is exactly what customers get on their own private bot. Simulated trading — no real money in this feed. Not financial advice. flippulse.com`

### 1.7 Beacons (link-in-bio) page
- Headline: `FlipPulse — the trading bot that mostly says no.`
- Sub: `Automated 15-min BTC trading on Kalshi. Paper mode first. Not financial advice; trading involves risk.`
- Buttons (in order): `▶ Watch it decide — live paper feed` → t.me/flippulse ·
  `📄 The 9 rules it checks (free)` → lead-magnet link · `🚀 Start in paper mode — $99` → go.flippulse.com

---

## §2 — Pinned posts

### 2.0 Founder 100 launch offer — `FOUNDER-LAUNCH` (Day 1; pin ABOVE the how-it-works thread until 100 spots are gone)

> Runs only while the `FOUNDING100` coupon has spots left. When it's exhausted, unpin
> these and revert CTAs to plain "$150 setup + $99/mo." Never promise it past the cap.
> **Compliance:** the offer is about *price*, never about returns — keep every risk
> disclosure intact (`11_COMPLIANCE_KIT.md` §2).

- **X / short** `FL-X`: `We're opening FlipPulse to our first 100 members.\n\nFounders join free — $150 setup + first month, on us. $0 today, then $99/mo. Cancel anytime.\n\nStarts in paper mode, so you watch it work first.\n\n100 spots. Then it's gone.\n👉 go.flippulse.com\n\n⚠️ Not financial advice. Trading involves risk of loss.`
- **IG / FB / long** `FL-FB`: `Founder 100 is open.\n\nFlipPulse is an automated bot for Kalshi's 15-minute Bitcoin Up/Down markets — it runs 9 checks before every trade and does nothing the rest of the time. Every member starts in PAPER mode (simulated money), so you watch it make real decisions before a single real dollar is at stake. Your funds never leave your own Kalshi account.\n\nFor the first 100 members, we're waiving the $150 setup fee AND your first month — $0 to start, then $99/month, cancel anytime. Regular price after that is $150 setup + $99/mo.\n\nThere are exactly 100 spots. When they're gone, they're gone.\n\n👉 go.flippulse.com\n\n⚠️ FlipPulse is software, not investment advice. Trading involves risk, including loss of principal. Simulated results do not guarantee live results.`
- **Countdown reply/story** `FL-COUNT` (reuse as spots drop): `[N] of 100 founder spots left. Setup + first month free, then $99/mo. go.flippulse.com` *(update N by hand from the Stripe coupon's redemption count.)*

### 2.1 X pinned thread — `TH-PIN` (post Day 1, pin immediately)
1/ `Most trading bots are built to trade as much as possible.\n\nOurs is built to refuse.\n\nFlipPulse trades Kalshi's 15-minute BTC Up/Down markets — but only when 9 conditions ALL pass. Most hours: nothing.\n\nHere's how it decides, in plain English 🧵`
2/ `First, the market: Kalshi (a CFTC-regulated US exchange) runs a BTC Up/Down contract every 15 minutes. 96 per day.\n\nEach contract pays $1 if you're right, $0 if you're wrong.\n\nSimple structure. Brutally fast. Impossible to trade well by hand, all day.`
3/ `The bot's job isn't predicting Bitcoin.\n\nIt's recognizing the rare moments when the odds are measurably tilted — and standing down the rest of the time.\n\nWe call the checklist the 9 Layers. Every layer must pass. One failure = no trade.`
4/ `The big three:\n\n🔍 Regime — is BTC actually trending? (R² test on recent price action)\n📊 Order book — is $50+ of real depth stacked 70%+ on one side?\n⚡ Momentum — is spot BTC moving the SAME direction?\n\nAll three agree, or nothing happens.`
5/ `It also checks its own performance. After 20 settled trades, if it can't statistically prove (90% confidence) it's beating a coin flip, it stops trading.\n\nA bot that benches itself. On purpose.`
6/ `Sizing: a % of the current balance — never a fixed bet. After a loss it cuts size to ~1/3 until it recovers. Three losses in a row = automatic pause.\n\nConservative / Balanced / Aggressive presets. You pick.`
7/ `And you see everything. Every decision hits your Telegram in real time — including the trades it REFUSED and why:\n\n"Regime filter │ RANGING — only TRENDING allowed. Skipping."\n\nSend /status any time. Pause any time.`
8/ `Every customer starts in paper mode — simulated money — so you watch it operate before a real dollar is at stake. Your funds stay in YOUR Kalshi account. We never touch them.\n\n$150 setup + $99/mo. Cancel anytime.\n\nLive paper feed: t.me/flippulse\nStart: go.flippulse.com\n\n⚠️ Not financial advice. Trading involves risk of loss. Simulated results don't guarantee anything.`

### 2.2 Instagram pinned post → use carousel `C01` (§4.3).
### 2.3 Facebook pinned post → `FB01` (§5).
### 2.4 TikTok — pin your first 3 videos (V01, V03, V05); pinned comment on every video:
`Every customer starts in paper mode (fake money) — you watch it work before anything real. Not financial advice; trading involves risk. Link on our IG/X @flippulse 🔗`

---

## §3 — X library

### 3.1 Standalone tweets (T01–T60)

**Pillar A — Receipts**
- `T01` `Our bot's day so far:\n\n✅ Checked 34 markets\n❌ Traded 0 of them\n\nReason logged every time: "RANGING regime — no edge."\n\nA bot with the patience you don't have. That's the product.`
- `T02` `Today's paper-mode log, unedited 👇\n\n[screenshot of Telegram daily summary]\n\nEvery customer gets this feed for their own bot. Wins, losses, and the boring days. t.me/flippulse if you want to watch live.`
- `T03` `It took a loss this morning.\n\nHere's what happened next, automatically:\n→ stake cut to 3% of balance\n→ recovery target set\n→ kept trading small until the balance recovered\n→ size restored. No human involved.\n\n[screenshot]`
- `T04` `The bot just sent this:\n\n"EDGE JUSTIFICATION │ YES @ 48¢ │ Regime=TRENDING(R²=0.78) │ OB=75% depth=$120 │ Momentum=AGREE │ Confidence=73/100"\n\nEvery single trade comes with its homework attached.`
- `T05` `Zero trades yesterday.\n\nSome customers ask if it's broken. It's not broken. Bitcoin spent the day chopping sideways and the doctrine says: ranging market = no trades, always.\n\nDiscipline looks boring right up until it saves you.`
- `T06` `Weekly receipts 🧾\n\nQualified setups found: [n]\nTrades taken: [n]\nTrades refused: [n]\nMost common refusal: [reason]\n\nFull unedited feed: t.me/flippulse\n\n(Paper mode. Not advice. Risk disclosure in bio.)`
- `T07` `A customer sent /status at 2am:\n\n[screenshot showing mode, balance, W/L, open positions]\n\nNo dashboard to log into. No spreadsheet. Just ask the bot how it's doing, any hour.`
- `T08` `3 consecutive losses → the bot benches itself. Automatically. Cooldown before it's allowed back in.\n\nWhen was the last time YOU did that after 3 losses?`

**Pillar B — Doctrine / education**
- `T09` `Kalshi runs a Bitcoin Up/Down market every 15 minutes.\n\n96 markets a day. Each pays $1 if right, $0 if wrong.\n\nMost people have never heard of these. Fewer have the reflexes to trade them all day. That's exactly why we built a bot for it.`
- `T10` `"Why did it skip that trade? BTC was clearly moving!"\n\nBecause one signal isn't confirmation.\n\nThe order book said UP. But spot momentum was NEUTRAL. The doctrine requires both to AGREE — explicitly. Neutral is a rejection.\n\nOne signal = a guess. Two agreeing = a setup.`
- `T11` `The single most important filter in our stack:\n\nRegime detection.\n\nEvery 30s, the bot runs a regression on recent BTC prices. R² > 0.65 = trending → trading allowed. Below = ranging → all signals ignored.\n\nThis one check eliminates 50–70% of would-be trades.`
- `T12` `Binary market math in one tweet:\n\nContract at 50¢ → you need >50% win rate to break even.\nAt 65¢ → you need >65%.\n\nEdge isn't "being right." It's being right MORE OFTEN than the price implies. That gap is the only thing worth trading.`
- `T13` `Why the bot only posts maker orders:\n\nTaker fees ≈ $5+/day at moderate frequency. On a small account that eats the entire edge.\n\nSo it posts limit orders 1¢ inside the spread and waits to be filled. Slower. Cheaper. Correct.`
- `T14` `The Wilson confidence interval, explained like you're 12:\n\n"You've won 12 of 20. Are you actually good, or lucky?"\n\nThe bot computes the statistically-safe LOWER estimate of its true win rate. If that drops under 50%, it stops trading. Evidence or nothing.`
- `T15` `Things that make the bot refuse to trade:\n\n• sideways BTC\n• violent BTC\n• thin order book\n• near-certain contracts (>85¢ / <15¢)\n• under 3 min to expiry\n• 3 losses in a row\n• its own win rate unproven\n\nThe list of reasons to say no is longer than the list to say yes. As it should be.`
- `T16` `What "smart sizing" actually means here:\n\nEvery stake is a % of the CURRENT balance.\n\nAccount grows → stakes grow.\nAccount dips → stakes shrink.\nLoss? → drop to recovery size until you're back.\n\nNo martingale. No doubling down. Ever.`
- `T17` `UTC 0–4 (post-US-close), the bot won't trade at all.\n\nThin books. One or two orders can fake an entire signal.\n\nIt's not missing opportunities at 2am. There are no opportunities at 2am — just noise wearing a costume.`
- `T18` `Kalshi 101, since people keep asking:\n\n• US exchange, CFTC-regulated\n• You trade event contracts: "Will BTC be above X at 3:15pm?"\n• Pays $1 per contract if right, $0 if wrong\n• Your money sits at the exchange, like a brokerage\n\nOur bot just automates one specific market there. Your account, your funds, your API key.`

**Pillar C — Discipline > hype**
- `T19` `Every trading bot ad: "It never sleeps! It trades 24/7!"\n\nOurs sleeps on purpose, 5 hours a day, because the books are garbage after US close.\n\n"Always trading" isn't a feature. It's how accounts die.`
- `T20` `Red flag phrases in bot marketing, a thread-less thread:\n\n"guaranteed returns" — nothing is\n"1000% APY" — run\n"risk-free" — lie\n"secret strategy" — it's martingale\n\nWhat honest looks like: published rules, paper mode first, losses posted. Judge us by that standard too.`
- `T21` `Hot take: your trading problem isn't information.\n\nIt's that at 11:47pm, up 3% and feeling invincible, you take one more trade.\n\nA bot doesn't feel invincible. It checks 9 boxes or it goes back to sleep.`
- `T22` `We could 10x our trade count by loosening two thresholds.\n\nMore action! More engagement! More dopamine!\n\nAnd worse expectancy. The doctrine line we wrote on day one still stands: "If trade frequency drops 80% but expectancy rises, that is success."`
- `T23` `Most bots die of overtrading.\n\nNot bad signals — overtrading. Fees, spreads, and forced trades in dead markets bleed accounts one paper cut at a time.\n\nThe cheapest edge in trading is simply refusing to play bad hands.`
- `T24` `"How many trades a day does it take?"\n\nHonest answer: 1–5 on a good day. Sometimes zero.\n\nIf that number disappoints you, we're not for you — and the bots promising 50/day are not your friend.`
- `T25` `POV: it's a choppy, sideways Bitcoin day\n\nYou: 14 trades, revenge-trading by noon\nThe bot: "RANGING (R²=0.31). Skipping." ×34\n\nSame market. Different nervous systems.`

**Pillar D — Build-in-public**
- `T26` `Building FlipPulse in public, week [n]:\n\n• [milestone]\n• [thing that broke + fix]\n• [what's next]\n\nAsk me anything about running a one-person trading-bot company. The unglamorous parts too.`
- `T27` `Design decision I'm proud of: the /status command is read-only.\n\nNo command can place a trade or flip a bot to live mode. Not from Telegram, not from anywhere. Going live is a deliberate, manual, human step.\n\nSome things should be hard.`
- `T28` `Why one bot per customer instead of one big multi-tenant system:\n\n• your own API key\n• your own Telegram bot\n• your own isolated deployment\n• nobody's bug becomes your bug\n\nCosts us more to run. Worth it.`
- `T29` `New customer onboarding, timed: 9 minutes from form to their bot's first heartbeat message.\n\nGoal by fall: under 5. The boring ops work IS the product.`
- `T30` `Milestone: [n] customers 🎉\n\nEvery single one started in paper mode. Several are still there, watching — and honestly? That's the system working exactly as designed. Go live when YOU'RE convinced, not when we say so.`

**Pillar E — Control & safety**
- `T31` `Things FlipPulse can't do, by design:\n\n• hold your money (stays in YOUR Kalshi account)\n• stop you pausing it (one tap)\n• go live without you explicitly choosing it\n• hide a trade from you (everything hits your Telegram)\n\nThe cage is the feature.`
- `T32` `"What if I want out?"\n\nPause: one tap, instant.\nCancel: anytime, no lock-in.\nYour funds: never left your own Kalshi account to begin with.\n\nExit doors everywhere. On purpose.`
- `T33` `Paper mode isn't a demo. It's the full bot — same signals, same sizing, same alerts — with simulated money.\n\nWatch it for a week. Watch it for a month. Go live only when you've seen enough. Or don't go live at all.`
- `T34` `Your money never touches our hands.\n\nIt sits in your Kalshi account (CFTC-regulated US exchange). The bot trades via YOUR API key, which can trade but can't withdraw.\n\nWe sell software + service. We are not a fund. Big difference.`
- `T35` `Every 15 minutes, heartbeat. Every trade, alert. Every day, summary. Anytime, /status.\n\nIf your current "automated strategy" goes quiet for hours, you don't have automation. You have a mystery box.`

**Engagement / question posts**
- `T36` `Honest question for traders:\n\nWhat % of your worst losses came from a bad READ vs. bad DISCIPLINE (revenge trade, oversize, boredom)?\n\nBe honest. Mine were 80% discipline.`
- `T37` `Poll: a trading bot goes 0-for-3 today, then correctly refuses 30 setups in a chop.\n\nDid it have a good day or a bad day?`
- `T38` `Fill in the blank: the hardest part of trading is ______.\n\n(We built a whole product around one specific answer. Curious how many say it.)`
- `T39` `What would it take for you to trust an automated strategy? Serious question — building the answer is literally my job. Wrong answers also welcome.`
- `T40` `If a bot could text you "why" before every trade it takes, would you actually read it — or do you just want the summary at the end of the day? Building for both, curious about the split.`

**CTA / promo (max ~1 in 5 posts)**
- `T41` `We stream a FlipPulse bot's paper-mode decisions to a public Telegram channel. Unedited. Timestamped. Including the boring days.\n\nWatch it think before you spend a dollar: t.me/flippulse\n\n⚠️ Simulated trading. Not financial advice.`
- `T42` `How FlipPulse starts, every time:\n\n1. Sign up (5 min) — go.flippulse.com\n2. We deploy YOUR bot (own keys, own Telegram)\n3. It runs in PAPER MODE\n4. You watch it decide, live\n5. Go live only if/when you choose\n\n$150 setup + $99/mo. Cancel anytime. Risk disclosure on site.`
- `T43` `$99/month. Flat.\n\nNo % of profits. No AUM fee. No upsell tiers.\n\nWe make the same $99 whether you deploy $500 or $50,000 — which means we have zero incentive to push you to oversize. Fee structure is risk management.`
- `T44` `Conservative: 5% stakes, strictest filters, lowest variance\nBalanced: 10% stakes, doctrine defaults\nAggressive: 20% stakes, more setups, higher variance\n\nThree postures, one switch, chosen by you at signup. All start in paper mode. go.flippulse.com`
- `T45` `The free doc we probably shouldn't give away: "The 9 Rules Our Bot Checks Before Risking a Dollar."\n\nThe actual entry doctrine, plain English. Steal it for your own trading, honestly.\n\nGrab it: [lead magnet link]`

**Trend-reactive templates (fill blanks when news hits)**
- `T46` `BTC just [moved X% / hit $X]. Everyone's asking what the bot did.\n\nAnswer: [it traded — here's the justification log / it stood down — regime flipped HIGH_VOL and the doctrine says violent markets are untradeable].\n\n[screenshot]`
- `T47` `Volatility like today is where "always trading" bots get wrecked.\n\nOurs classifies HIGH_VOL as untradeable — mean 30s move over 0.15% = stand down. It sat out [n] straight windows this afternoon.\n\nSurviving days like this IS the strategy.`
- `T48` `[News: Kalshi/prediction-market headline]\n\nOur take as people who trade these markets programmatically every day: [2-sentence take].\n\nThis space is getting big, fast.`
- `T49` `Quiet BTC week = quiet bot week.\n\nTrades: few. Refusals: many. Account: intact.\n\nThe flex is the third line.`
- `T50` `Everyone's a genius in a trend. The doctrine's job is the OTHER 70% of the time.\n\nThis week that meant: [n] setups passed all 9 layers, [n] rejected. The rejections are the product.`

**Spare evergreen**
- `T51` `A limit order 1¢ inside the spread is the bot equivalent of never paying retail.`
- `T52` `"Set and forget" is marketing. FlipPulse is "set and VERIFY" — it runs itself, but every decision lands on your phone. Automation with receipts.`
- `T53` `The order book is the only place market participants put money where their mouth is. That's why it's our primary signal — not headlines, not indicators, not vibes.`
- `T54` `Two kinds of trading pain: losing money on a good process, and making money on a bad one. The second is more expensive. It just bills you later.`
- `T55` `Every stake is stamped with the balance BEFORE the trade, so recovery targets are exact — never reconstructed from PnL math. Boring engineering detail. Exactly the kind that matters at 3am.`
- `T56` `We publish our no-trade conditions. All 14 of them.\n\nAsk any other bot for their list. Watch what happens.`
- `T57` `If your strategy can't survive being written down and shown to strangers, it isn't a strategy. Ours is public: the 9 layers, the sizing, the refusal list. [lead magnet link]`
- `T58` `The 15-minute contract either pays $1 or $0. No stop-losses to fumble, no liquidations, no leverage. The risk is the stake, known in advance, every time. Binary markets are brutally honest.`
- `T59` `Customer question of the week: "[real question]"\n\nAnswer: [answer in 2-3 sentences].\n\nKeep these coming — they write our roadmap.`
- `T60` `Reminder because finance Twitter needs it daily: paper-mode results are practice. Live results involve slippage, fills, and feelings. Anyone who shows you simulated numbers as proof of profit is selling something. (Yes, ours are labeled.)`

### 3.2 Threads (TH01–TH08) — post the numbered tweets as a chain

**TH01 — "96 markets a day" (Pillar B, Week 1)**
1/ `Kalshi runs a Bitcoin Up/Down market every 15 minutes. 96 a day, ~35,000 a year.\n\nAlmost nobody can trade them well by hand. Here's why — and what it takes to do it programmatically 🧵`
2/ `The contract: "Will BTC be above $X at [time]?" YES/NO, priced 1–99¢, pays $1 if right.\n\nAt 50¢, the market says coin flip. At 70¢, it says 70%. The price IS the market's probability estimate.`
3/ `To profit you must find moments where the TRUE probability beats the priced one. In a 15-min window. Repeatedly. Without tilting.\n\nBy hand, that's a full-time job with a caffeine problem.`
4/ `What a bot does instead: watches every one of the 96 windows, measures order-book pressure, tests whether BTC is actually trending, confirms with spot momentum, prices its edge — and passes on ~everything.`
5/ `The punchline: the hard part isn't speed. It's that a bot will skip 30 mediocre setups in a row without getting bored. No human can.\n\nWe built FlipPulse to be exactly that: patient, all day, every day.`
6/ `It starts in paper mode so you can watch it make (and refuse) trades with zero risk: t.me/flippulse for the live feed.\n\n⚠️ Not financial advice. Trading involves risk.`

**TH02 — "Anatomy of a refused trade" (Pillar A, Week 2)**
1/ `At 2:47pm today our bot found a juicy signal — order book stacked 78% one side — and refused to trade it.\n\nThis is the most important screenshot we can show you 🧵 [screenshot]`
2/ `The signal that tempted it: 78% of near-money depth on YES. Historically that kind of imbalance has been a real edge.\n\nSo why no trade?`
3/ `Layer 5 failed. BTC's last 5 minutes: R² of 0.31 — a ranging, directionless chop. In ranging markets, order-book pressure is NOISE. The smart-money thesis requires an actual trend to position into.`
4/ `One layer fails = no trade. Doesn't matter how pretty the other 8 look.\n\nLog line, verbatim: "Regime filter │ RANGING (R²=0.31) — only TRENDING allowed. Skipping."`
5/ `Multiply this by ~30 refusals a day and you understand the product: we're not selling trades. We're selling the discipline to skip almost all of them.\n\nWatch the refusals live: t.me/flippulse — Not financial advice.`

**TH03 — "The 9 layers" (Pillar B, Week 3 — long-form doctrine)**
1/ `Our bot checks 9 things before every trade. All 9 must pass. One failure = no trade, reason logged.\n\nHere's the full checklist — steal it for your own trading 🧵`
2/ `Layer 1 — Sanity. Price between 15–85¢ (no near-certainties), real spread, no existing position, 2-min cooldown since last trade. The "are we even looking at a tradeable market" gate.`
3/ `Layer 2 — Streak pause. 3 consecutive losses = automatic timeout. Bad luck and dead regimes look identical in the moment; the pause outlasts both.`
4/ `Layer 3 — Proof of edge. After 20 settled trades, the bot computes a Wilson confidence interval on its own win rate. Lower bound under 50%? It stops. Statistical evidence or no capital.`
5/ `Layer 4 — Time quality. No trading UTC 0–4 (thin books) and never under 3 minutes to expiry (that's resolution, not positioning).`
6/ `Layer 5 — Regime. Linear regression on recent BTC prices. Only a TRENDING regime (R² > 0.65) is tradeable. Ranging = noise. High-vol = chaos. This kills 50–70% of candidate trades alone.`
7/ `Layer 6 — Book quality. ≥$50 of real depth near the money, ≥70% stacked on one side. Below that, one retail order can fake the whole signal.`
8/ `Layer 7 — Momentum agreement. Spot BTC must be moving the SAME direction as the book says. Neutral isn't agreement. Conflict is a veto.`
9/ `Layer 8 — Composite confidence ≥65/100 across all signals. Layer 9 — priced edge ≥6%, sensible size, fillable limit price.\n\nThen — and only then — it posts a maker order and tells you why, in one log line.`
10/ `That's the whole doctrine. No secrets, no black box.\n\nPlain-English PDF version free here: [lead magnet link]\nWatch it applied live: t.me/flippulse\n\n⚠️ Educational content, not financial advice.`

**TH04 — "Why flat pricing" (Pillar D/E, Week 4)**
1/ `FlipPulse costs $99/mo flat. No performance fee, no % of account.\n\nThis is a deliberate incentive-design choice, not a pricing afterthought 🧵`
2/ `Performance fees sound aligned ("we only win when you win!") but they quietly reward the manager for VARIANCE. Big swings = big fee years. Heads they win, tails you lose alone.`
3/ `% of account (AUM) fees reward gathering assets, not managing them well.\n\nFlat SaaS pricing rewards exactly one thing: keeping you as a happy customer next month. Retention IS the incentive.`
4/ `It also means we don't care if you run $500 or $50k — so you'll never get a nudge from us to size up. Your bankroll is your business.`
5/ `$150 setup + $99/mo, cancel anytime, start in paper mode. go.flippulse.com\n\n⚠️ Not financial advice. Trading involves risk of loss.`

**TH05 — "How we almost blew up (v5 postmortem)" (Pillar D, Week 5 — the trust nuke)**
1/ `In March an early version of our bot lost 50% of a session's (test) capital in two days.\n\nWe kept the postmortem in the codebase permanently. Here's everything that was wrong — and what it taught us about every bot you've ever been pitched 🧵`
2/ `Bug 1: no regime detection. It traded order-book signals in CHOPPY markets, where those signals are pure noise. Right signal, wrong weather.`
3/ `Bug 2: it accepted "neutral" momentum as confirmation. BTC is flat 60–80% of the time — so most trades were effectively single-signal guesses.`
4/ `Bug 3: a $5 order-book depth threshold. One retail order could trigger a "smart money" signal. $5! Now it's $50 minimum with 70% imbalance.`
5/ `Bug 4: broken sizing math that anchored bets to a fixed proxy instead of the real balance — so as the account shrank, bets DIDN'T. Drawdown accelerator, built in by accident.`
6/ `Every one of those bugs now has a named layer, a threshold, and a log line guarding against it. The doctrine file opens with the scar tissue.`
7/ `Why tell you this? Because every bot vendor has a version of this story and almost none will tell it. Ask them. The silence is the answer.\n\nOur full doctrine, including the postmortem notes: [lead magnet link]`

**TH06 — "Paper mode is the product" (Pillar E, Week 6)**
1/ `Unpopular SaaS opinion: our free-trial equivalent is better than a free trial — and most customers should stay in it longer than they plan to 🧵`
2/ `Every FlipPulse deployment starts in paper mode: full bot, real signals, real-time alerts, simulated money. Not a demo. The actual system with the money wire unplugged.`
3/ `What you're really evaluating in paper mode isn't "does it make money this week" (short windows prove nothing either way). It's: do I understand WHY it trades? Do the refusals make sense? Can I live with the cadence?`
4/ `Going live is a deliberate, manual step that only you initiate. No command, no setting, no support ticket can flip it silently. We made it inconvenient on purpose.`
5/ `Watch a live paper feed right now, no signup: t.me/flippulse\n\nStart yours: go.flippulse.com — $150 setup + $99/mo.\n\n⚠️ Simulated results don't predict live results. Not financial advice.`

**TH07 — "Prediction markets are eating finance" (Pillar B, Week 7 — trend-surf thread)**
1/ `Prediction markets went from novelty to a regulated, multi-billion-dollar asset class in ~3 years. If you only know Kalshi from election odds, you're missing the more interesting part 🧵`
2/ `Kalshi is a CFTC-regulated US exchange for event contracts. Elections got headlines — but the volume workhorses are the boring ones: rates, weather, crypto prices.`
3/ `The BTC 15-minute Up/Down series runs 96 markets/day. It's basically a pure, fast, capped-risk instrument: pay ≤$1, get $1 or $0. No leverage, no liquidation, no funding rates.`
4/ `Capped-risk + high-frequency + inefficient books (it's early!) = exactly the environment where systematic, disciplined trading has a shot — and manual trading is miserable.`
5/ `That's the thesis FlipPulse is built on. One market, traded with a published doctrine, transparent to the customer. Early spaces reward the disciplined.\n\nt.me/flippulse to watch. Not financial advice.`

**TH08 — "What $99/mo actually buys" (Pillar D/E, Week 8)**
1/ `"Why wouldn't I just build this myself?" — fair question, favorite question 🧵`
2/ `You could! The concepts are public — we literally give the doctrine away. What you're paying for is everything around the strategy:`
3/ `• Your own isolated deployment (not shared infra)\n• Your own Telegram bot wired to it\n• State that survives restarts & redeploys\n• Recovery/sizing state machines that don't wedge\n• Monitoring, heartbeats, a /status command\n• A human (me) watching the fleet`
4/ `The strategy is 20% of the work. The other 80% is the unglamorous reliability engineering that decides whether the strategy survives contact with reality. DIY that part is a month of weekends. Then maintenance, forever.`
5/ `If you build it anyway — genuinely, respect, send me your repo. If you'd rather have it running by tonight: go.flippulse.com. Paper mode first, $99 + $99/mo, cancel anytime.`

---

## §4 — Instagram

### 4.1 Reel captions (IG01–IG20) — pair with videos per calendar; 3–5 hashtags from §10

- `IG01` `The trading bot that's proud of doing nothing. 9 checks before every trade — most hours, at least one fails, so it waits. Discipline as a service. ⚠️ Not financial advice. Trading involves risk. #kalshi #tradingbot #btc`
- `IG02` `POV: Bitcoin is chopping sideways and your bot refuses to give you dopamine 📉🤖 "RANGING — skipping." ×34 today. That's not a bug. #trading #discipline #crypto`
- `IG03` `Every trade comes with its homework attached 📋 Regime, order book, momentum, confidence score — one log line, every time. If your strategy can't explain itself, is it a strategy? #quant #tradingbot #kalshi`
- `IG04` `96 Bitcoin markets a day on Kalshi. 15 minutes each. Nobody can watch them all — so we built the thing that does. Starts in paper mode 📄 link in bio. ⚠️ Not financial advice. #btc #predictionmarkets #kalshi`
- `IG05` `It lost. Here's what happened next, automatically 👇 stake cut to a third → small recovery trades → balance back → full size restored. No revenge trading. No human required. #riskmanagement #trading #automation`
- `IG06` `Paper mode = the whole bot, fake money. Watch it decide for weeks before a real dollar moves. If a bot won't let you do that… ask why 🤔 link in bio. #tradingbot #papertrading #kalshi`
- `IG07` `Your money never touches our hands. It stays in YOUR Kalshi account (CFTC-regulated). The bot trades via your API key — which can't withdraw. The cage is the feature 🔒 #fintech #kalshi #security`
- `IG08` `3 losses in a row → automatic timeout 🪑 When was the last time you benched yourself? #tradingpsychology #discipline #bots`
- `IG09` `Things our bot refuses to trade: sideways markets, violent markets, thin order books, near-certain contracts, the 2am hours. The "no" list is the product. #trading #quant #btc`
- `IG10` `Flat $99/mo. No % of profits, no AUM fee. We earn the same whether you run $500 or $50k — so we never have a reason to push you bigger. Fee design = risk design 🧮 ⚠️ Not financial advice. #pricing #fintech #trading`
- `IG11` `Every 15 min: heartbeat. Every trade: alert. Every day: summary. Anytime: /status. Automation with receipts 🧾 #tradingbot #telegram #transparency`
- `IG12` `We publish our losing days. On purpose. Because the day you should trust a trading product is the day it stops hiding. Live paper feed → link in bio ⚠️ Simulated trading, not financial advice. #buildinpublic #trading`
- `IG13` `Conservative 🛡 / Balanced ⚖️ / Aggressive ⚡ — three risk postures, one switch, your choice at signup. All start in paper mode. Link in bio. ⚠️ Trading involves risk. #kalshi #tradingbot`
- `IG14` `The bot slept from midnight to 4am. On purpose. Thin books = fake signals = no trades. "Always on" is a marketing line, not a strategy 😴 #trading #quant`
- `IG15` `What is Kalshi? US exchange, CFTC-regulated, event contracts that pay $1 or $0. The 15-min BTC market is the fast lane — and it's what FlipPulse trades. Full explainer in this reel 🎥 #kalshi #predictionmarkets #explained`
- `IG16` `Build-in-public update 🛠 [milestone] · [fix] · [next]. One person, one bot fleet, all receipts. Ask anything in the comments. #buildinpublic #indiehacker #fintech`
- `IG17` `Signal without confirmation is a guess. Order book says UP + spot momentum says UP = setup. Order book says UP + momentum flat = nothing happens. Two keys, one lock 🔑🔑 #trading #quant #btc`
- `IG18` `The math nobody does: at 50¢ a contract, you need >50% wins to break even. At 65¢, >65%. Edge is beating the price, not being right. #tradingmath #predictionmarkets`
- `IG19` `Customer question: "Is it broken? It hasn't traded today." Answer: Bitcoin went sideways all day, and sideways = untradeable, always. The most common support ticket is the system working 😅 #tradingbot #kalshi`
- `IG20` `From signup to your bot's first heartbeat: ~10 minutes. Your keys, your Telegram, your risk format, paper mode on. This is what the start actually looks like 👀 link in bio. ⚠️ Not financial advice. #onboarding #tradingbot`

### 4.2 Story templates (rotate daily, 9:00am)
- `ST-A` Poll: screenshot of a refusal log + "Would YOU have skipped this trade?" [Yes/No poll sticker]
- `ST-B` Quiz: "A contract at 65¢ needs what win rate to break even?" [50% / 65% / 35%] → answer slide with 1-line explainer.
- `ST-C` This-or-that: "Pick your posture: 🛡 Conservative / ⚖️ Balanced / ⚡ Aggressive" [emoji slider or poll]
- `ST-D` Screenshot of `/status` output + link sticker "watch live → t.me/flippulse"
- `ST-E` Behind-the-scenes: deploy screen / terminal / coffee + "shipping [feature] today"
- `ST-F` Reshare the day's Reel with "🆕 today's post" + question sticker "what should the bot explain next?"
- `ST-G` (Fridays) Weekly recap card (Canva template G-4.3) + link sticker.

### 4.3 Carousel outlines (C01–C06) — build in Canva per `05_GRAPHICS_PROMPTS.md` §4
- `C01` **"How FlipPulse decides"** (pinned): 8 slides — cover "9 checks before every trade" → one slide per key layer (sanity, streak pause, statistical guard, time, regime, book, momentum, confidence+edge) → CTA slide "starts in paper mode · link in bio · not financial advice."
- `C02` **"Kalshi 101"**: 7 slides — what Kalshi is → event contracts → $1/$0 payoff → the 15-min BTC series → why it's hard by hand → where a bot fits → CTA.
- `C03` **"Red flags in trading-bot ads"**: 6 slides — guaranteed returns / hidden strategy / no paper mode / they hold your funds / only winners posted → "what honest looks like" checklist → CTA.
- `C04` **"What happens after a loss"**: 6 slides — the loss → recovery sizing (3%) → target set from pre-trade balance → small trades → recovery hit → size restored. Flowchart style.
- `C05` **"Paper → Live, the whole journey"**: 7 slides — signup → deploy → paper weeks → what to look for → the deliberate go-live step → the pause button → CTA.
- `C06` **"3 risk formats compared"**: 5 slides — table Conservative/Balanced/Aggressive (stake %, filters, frequency, variance) → "all start in paper mode" → CTA.

---

## §5 — Facebook posts (FB01–FB15) — longer, plain-spoken, 35+ audience

- `FB01` (pin) `Most trading software is sold on hype. We built FlipPulse on the opposite idea.\n\nIt's an automated bot for Kalshi's 15-minute Bitcoin Up/Down markets — Kalshi is a CFTC-regulated US exchange. The bot checks nine strict conditions before every single trade: is Bitcoin actually trending, is there real money in the order book, does spot momentum agree, has the bot statistically proven its own edge… If even one check fails, it does nothing and tells you why.\n\nEvery customer starts in paper mode — simulated money — and watches the bot make real decisions with zero risk. Your funds stay in your own Kalshi account the entire time. Every decision arrives on your own Telegram, and you can pause with one tap.\n\n$150 setup + $99/month, cancel anytime. If you'd like to watch a live paper-mode feed first (we publish one, unedited): t.me/flippulse\n\nQuestions welcome in the comments — the founder answers every one.\n\n⚠️ FlipPulse is software, not investment advice. Trading involves risk, including loss of principal. Simulated results do not guarantee live results.`
- `FB02` `Here's a screenshot most companies wouldn't post: our bot refusing to trade, 34 times in one day. Bitcoin spent the day moving sideways, and in sideways markets the signals this strategy uses are just noise — so the rules say stand down. A tool that protects you from bad days is worth more than one that promises good ones. [screenshot] ⚠️ Not financial advice.`
- `FB03` `"Where does my money actually sit?" — the best question we get.\n\nAnswer: in YOUR Kalshi account, a CFTC-regulated US exchange. FlipPulse never holds a dollar. The bot trades through your own API key, which can place trades but cannot withdraw funds. We charge a flat software fee — $99/month — and that's the entire business model. [link] ⚠️ Trading involves risk.`
- `FB04` `A 15-minute Bitcoin market sounds exotic, but the structure is simple: "Will Bitcoin be higher at 2:15 than at 2:00?" Contracts pay $1 if you're right, $0 if not. Risk is capped at what you paid — no leverage, no liquidations. There are 96 of these a day on Kalshi. Our bot watches all of them so nobody has to. [explainer video]`
- `FB05` `The feature our customers mention most isn't a trading feature. It's the Telegram feed. Every heartbeat, every trade, every daily summary — on your phone, from your own private bot. Send /status any time and get the full picture in two seconds. Automation you can actually see. [screenshot]`
- `FB06` `Three risk settings, plain English:\n\n🛡 Conservative — small stakes (5% of balance), strictest filters, fewest trades.\n⚖️ Balanced — the default. 10% stakes, standard doctrine.\n⚡ Aggressive — 20% stakes, more setups, bigger swings.\n\nYou choose at signup, we deploy it, and everyone starts in paper mode regardless. [link] ⚠️ Not financial advice.`
- `FB07` `Founder note, week [n]: [milestone / lesson / fix]. Building this company in public because trust is the entire product in this category. Ask me anything below — including the uncomfortable questions. Especially those.`
- `FB08` `If you're evaluating ANY automated trading product (including ours), demand these five things:\n\n1. Published rules — what makes it trade?\n2. Paper mode — can you watch before risking money?\n3. Custody — does your money stay at a regulated exchange, in your name?\n4. Transparency — do you see every decision, or a monthly summary?\n5. Exit — can you pause instantly and cancel anytime?\n\nAnything that fails #3 is an automatic no. Here's how FlipPulse answers all five: [link]`
- `FB09` `Poll for the traders here: what's cost you more over the years — bad analysis, or bad discipline (the revenge trade, the oversized position, the 1am "one more")? Honest answers only. Our bet when we built FlipPulse was that for most people it's discipline. 🗳`
- `FB10` `Sunday reading: we wrote down every condition under which our bot is forbidden to trade — all 14 — and published the list. Sideways markets. Violent markets. Thin order books. Three losses in a row. The 2am hours. If a strategy's "never trade" list is longer than its sales page, that's a good sign. Full doc free: [lead magnet link]`
- `FB11` `Milestone: [n] customers. 🎉 Thank you. A stat we're weirdly proud of: several are still in paper mode after weeks — watching, learning the cadence, in zero rush. That's exactly the customer we built this for. Go live when YOU'RE convinced. Or don't.`
- `FB12` `The most honest sentence in our documentation: "Many days with zero trades are correct behavior." We put it in writing because someday your bot will have a quiet Tuesday and you'll wonder if it's broken. It isn't. Bitcoin was boring. The bot noticed. That's the job.`
- `FB13` `What the $99/month actually pays for: your own isolated bot deployment, your own Telegram alert bot, state that survives restarts, monitoring and heartbeats, and a human being who watches the fleet daily. The strategy is public — the reliability engineering is the product. [link]`
- `FB14` `Bitcoin had a wild day today. Quick note on what FlipPulse bots did: mostly nothing. Violent, spiking markets get classified HIGH_VOL and the doctrine forbids trading them — spike-and-reverse moves invalidate every 15-minute signal. Sitting out days like this is why the strategy survives to trade calm ones. ⚠️ Not financial advice.`
- `FB15` `We made the "go live" step deliberately inconvenient. No Telegram command can switch a bot from paper money to real money — not /golive, not a setting, nothing. It's a manual, human, double-checked step that only happens when the customer explicitly asks. Some friction is a safety feature.`

---

## §6 — TikTok/Reels captions
Video captions live with their scripts in `04_VIDEO_SCRIPTS.md` (each script V01–V30
includes its TikTok caption + IG caption pairing). Hashtags: §10.2.

---

## §7 — Reddit posts (R01–R06) & comment kit
**Rules recap:** no links in posts (unless a mod says OK / it's asked for), no
pricing, mention FlipPulse only in comments when asked or in your profile.
Post from u/FlipPulse_Founder after 2 weeks of commenting. These are REAL value
posts — that's why they work.

- `R01` — r/algotrading, Week 3. **Title:** `Lessons from building a bot for Kalshi's 15-min BTC binaries (the postmortem that rewrote it)`
  **Body:** `I run a small bot on Kalshi's KXBTC15M series (15-minute BTC up/down binaries). An early version lost half its test-session capital in two days, and the rewrite that followed taught me more than a year of green days. Sharing the big ones:\n\n1) Regime detection is worth more than your entry signal. My primary signal is near-money order-book imbalance. It has measurable predictive value in trending tape and is pure noise in chop. Adding a simple regression-based regime gate (only trade when R² of recent price action > 0.65) eliminated 50–70% of trades and most of the bleeding.\n\n2) "Neutral" confirmation is not confirmation. I originally let flat spot momentum pass the gate. BTC is flat most of the time, so most trades were single-signal. Requiring explicit directional agreement between book pressure and spot momentum cut false positives dramatically.\n\n3) Microstructure thresholds matter more than they look. A $5 depth threshold let a single retail order fake a "smart money" signal. Raising the near-money depth floor to $50 with a 70% imbalance requirement changed the character of what gets through.\n\n4) Fees decide small-account viability. Taker fees at even moderate frequency will eat the whole edge on a small bankroll. Maker-only limit orders 1¢ inside the spread, with a cleanup job for stale unfilled orders, was the difference between negative and positive expectancy after costs.\n\n5) Statistical self-doubt as a feature: after 20 settled trades the bot computes a Wilson CI lower bound on its own live win rate and stands down if it can't clear 50% at 90% confidence. It has benched itself before. That's the feature working.\n\nHappy to go deeper on any of these — especially regime classification, which I still think is underrated relative to signal-hunting.`
- `R02` — r/Kalshi, Week 4. **Title:** `The 15-minute BTC markets: some microstructure observations after months of watching all 96 daily windows`
  **Body:** `I've been programmatically watching (and selectively trading) the KXBTC15M series for a while. Observations that might interest people here:\n\n• Liquidity is very unevenly distributed across the day. The UTC 0–4 windows (post-US-close) are consistently thin enough that one or two orders can move the visible book — I treat them as untradeable.\n\n• The market closest to 50¢ mid is almost always the most liquid and cheapest to trade. The far-from-money windows have wide spreads and near-certain pricing (>85¢/<15¢) where there's minimal EV net of costs.\n\n• Near-money depth imbalance has been a meaningfully predictive signal in trending conditions and roughly a coin flip in ranging ones. If you're doing anything systematic here, some form of regime filter seems close to mandatory.\n\n• Maker vs taker matters a lot at this cadence. Posting inside the spread gets filled surprisingly often near the money, and the fee difference compounds fast.\n\n• Last 3 minutes before expiry, the book reflects resolution certainty rather than directional pressure — I ignore it entirely.\n\nCurious what others trading these windows are seeing, especially around liquidity at different hours.`
- `R03` — r/algotrading, Week 6. **Title:** `Position sizing state machines: how I stopped my bot from revenge trading (and from wedging)`
  **Body:** `Sharing a design that's been reliable for me. Percentage-of-balance sizing with a two-tier recovery mode:\n\n• Normal: stake = X% of current balance (compounds up, de-risks down — no fixed dollar stakes).\n• A full-size trade settles as a loss → enter recovery: stakes drop to ~1/3 of normal, and the recovery TARGET is the realized balance stamped immediately before that losing trade was entered (recorded at order placement, never reconstructed from PnL — reconstruction drifts).\n• Balance ≥ target → recovery exits automatically. Exit is checked every cycle AND on boot, independent of whether trades fire, so it can't wedge in recovery forever.\n• A loss during recovery does NOT move the target — entry is event-driven, exit is balance-driven, so it can't oscillate.\n\nSeparately: a hard consecutive-loss pause (bad luck and dead regimes look identical in-sample; the pause outlasts both) and a catastrophic session stop as the backstop of last resort.\n\nThe meta-lesson: sizing logic is a state machine and deserves the same rigor as your signal. Persist the state atomically, reconcile it on boot, and enumerate the stuck states — mine were "wedged in recovery" and "target drift," both killed by the stamp-at-entry + check-on-boot design. What are other people's recovery/de-risking schemes?`
- `R04` — r/CryptoCurrency (or r/BitcoinMarkets), Week 8. **Title:** `Kalshi's 15-minute BTC binaries are a genuinely interesting instrument and nobody talks about them`
  **Body:** `Not affiliated with Kalshi, just fascinated by the structure. Every 15 minutes there's a contract: will BTC be above X at expiry. Pays $1 or $0. What makes it interesting vs spot/perps:\n\n• Risk is capped at the premium. No leverage, no liquidation cascade, no funding.\n• The price IS the market's probability estimate, so "edge" is precisely defined: your true win probability minus the implied one. It's the cleanest expression of "are you actually right more often than the market thinks" I've seen.\n• It's CFTC-regulated, USD-denominated, and boring in all the ways that matter.\n• The books are still young/inefficient at certain hours, which cuts both ways — spreads can be wide, but pricing anomalies exist.\n\nThe catch: 96 windows a day is a firehose. Trading it manually with discipline is basically impossible — it's either a systematic/automated game or a "pick your 2 windows a day" game.\n\nHappy to answer questions about the mechanics; I've spent way too long watching these books.`
- `R05` — r/sidehustle or r/passive_income, Week 10 (⚠️ tread carefully; lead with anti-hype). **Title:** `A reality check on "trading bots" as a side income idea (from someone who builds one)`
  **Body:** `I build trading automation, so take this as an insider's warning label rather than a pitch.\n\n1) Any bot marketed with guaranteed returns, "passive income," or screenshots of only winning days is lying to you by construction. Markets have variance; anyone hiding it is hiding worse things.\n\n2) Custody is the only question that matters first. If the product wants you to deposit funds TO THEM, stop. Legit automation trades your own account at a regulated venue via an API key that can't withdraw.\n\n3) Demand a paper/simulation mode and actually use it for weeks. If a vendor discourages paper trading, they're selling urgency, not software.\n\n4) Understand the fee model's incentives. Performance fees reward variance. Flat fees reward retention. AUM fees reward asset-gathering. None are evil, but know what behavior you're paying for.\n\n5) Expect boredom. Real systematic trading is mostly the machine declining to trade. If you want entertainment, casinos are more honest about it.\n\nTrading bots are not passive income. They're a tool that removes execution errors and emotional mistakes from a strategy that still carries real risk. Size accordingly.`
- `R06` — r/Kalshi, Week 12. **Title:** `AMA-ish: I run automated strategies on Kalshi full-time-ish — ask me anything about the API, the books, or the boring parts`
  **Body:** `There are more "how do I automate on Kalshi" questions here every week, so: I build and operate bots on the BTC 15-min series. Ask me anything — API quirks, rate limits, order lifecycle, maker fills, state persistence, monitoring, the works. I'll answer everything I can without turning this into an ad (mods: happy to keep product mentions out of the thread entirely).`

**Comment kit (use verbatim when relevant threads appear):**
- `RC1` (someone asks "is there a bot for Kalshi?"): `A few people have built private ones (I run one on the BTC 15-min series — details in my profile if you're curious). Whatever you use, insist on: your own API key (trade-only, no withdrawal), a paper mode you can watch for weeks, and published entry rules. The 15-min BTC books are thin at off-hours, so anything without time-of-day and regime filters will bleed. Happy to answer specifics. Not financial advice, obviously.`
- `RC2` (someone posts losses from manual trading): `Rough one. FWIW the pattern in your screenshots looks less like bad reads and more like sizing/discipline (the doubling after losses especially — that's the account killer). One thing that helped me: hard rules written BEFORE the session — max consecutive losses, fixed % stakes, no trades in the last minutes before expiry — and something external enforcing them, because in the moment we're all liars.`
- `RC3` (someone asks "is Kalshi legit?"): `It's a CFTC-regulated US exchange (DCM) — same regulator as CME. Funds sit at the exchange in your name, withdrawals are normal ACH. Whether the CONTRACTS are worth trading is a separate question, but the venue itself is about as legitimate as this category gets in the US.`

---

## §8 — Outreach scripts

### 8.1 Micro-influencer DM (X/IG, 10–100K finance/prediction-market creators)
`Hey [name] — been following your [Kalshi/prediction market/BTC] content, the [specific video/post] was genuinely great.\n\nI built FlipPulse — an automated bot for Kalshi's 15-min BTC markets. The angle your audience might actually care about: it starts in paper mode, publishes its full entry doctrine, and streams every decision (incl. refusals) to Telegram. Anti-hype by design.\n\nWant a free account to poke at? No strings — if you hate it, say so publicly, honestly. If you like it, we do 20% recurring for 6 months on anyone you send. Either way I'll send you the doctrine doc, it's a fun read.\n\n[you] — founder`

### 8.2 Follow-up (5 days later, once)
`No worries if this got buried — one-line version: free access to a Kalshi trading bot that starts in paper mode, 20% recurring affiliate if it's a fit, zero obligation. If it's a no, a "no" is genuinely helpful too 🙏`

### 8.3 Newsletter/blog pitch (email)
Subject: `Guest post: how Kalshi's 15-minute BTC markets actually work (microstructure, not hype)`
`Hi [name],\n\nI write about and build automation for Kalshi's 15-minute BTC binaries — a market with 96 daily windows that almost nobody covers properly.\n\nI'd love to write a piece for [newsletter]: "[How 15-minute binary markets work — and why they're nearly impossible to trade by hand]". Real microstructure content — liquidity patterns by hour, maker/taker math, regime effects on order-book signals. No product pitch in the body; a one-line bio mention is plenty.\n\nRecent example of my writing: [link to best thread/Reddit post]. 800–1,200 words, exclusive to you, delivered within a week.\n\n[you], founder of FlipPulse`

### 8.4 X engagement target list (reply under these daily — build in week 1)
Build a private X List named "Engage" containing: Kalshi's official account +
its founders/employees; prediction-market commentators; fintwit accounts
covering BTC microstructure; build-in-public/indie-hacker accounts with fintech
audiences; 5–10 mid-size crypto educators who are anti-hype. (Search X for
"Kalshi", "prediction markets", "event contracts" and add the recurring
voices — roughly 25–40 accounts.) Reply early (first 30 min after they post),
add substance from the doctrine, never link-drop.

### 8.5 Customer testimonial request (DM/email, day 14 of their subscription)
`Hey [name] — you've had your bot for two weeks! Two quick things:\n\n1) Anything confusing, annoying, or missing? Brutal honesty helps most.\n2) If you're enjoying the feed: would you screenshot your favorite bot alert (paper-mode ones are perfect) and let us share it (with your handle or anonymously — your call)? Real screenshots from real customers are the only marketing that works in this category.\n\nAs thanks: refer a friend and you both get a month adjusted — they skip the $150 setup, you get a free month. They just need to put your handle in the "how did you hear about us" box.`

---

## §9 — Reply templates & comment strategy

**Our-post replies (respond within 12h, first 60 days = 100% response rate):**
- Price objection → `Totally fair. The way to think about it: $99/mo flat, no % of anything, and you start in paper mode — so the real question costs $99+$99 to answer properly, not your bankroll. And cancel is one click. ⚠️ Not advice — trade only what you can afford to lose.`
- "Is this a scam?" → `Healthy default in this category! Three checkable facts: (1) your money stays in YOUR Kalshi account — a CFTC-regulated exchange — we never hold funds; (2) every account starts in simulated paper mode; (3) we publish a live unedited decision feed at t.me/flippulse, losses included. Verify all three before trusting a word we say 👍`
- "What are the returns?" → `We don't publish return figures — simulated numbers mislead and live results vary with market conditions, format, and timing. What we publish instead: the full entry doctrine and a live decision feed (t.me/flippulse). Trading involves real risk of loss; anyone quoting you a % is selling something.`
- "Why not just do it myself?" → `You genuinely could — the doctrine's public. You're paying for the deployment, monitoring, state persistence, and upkeep (the 80% that isn't strategy). If you build one, seriously, show me — I love comparing notes.`
- Troll/hostile → one calm factual reply max, then disengage: `All fair to question. The verifiable bits: CFTC-regulated venue, funds stay in the customer's account, paper mode first, live decision feed public at t.me/flippulse. Beyond that, reasonable people can disagree 🤝`
- Genuine technical question → answer fully + `Great question — adding this to the FAQ.` (then actually add it; these become T59 posts.)

**Outbound comment strategy (the 15/day on X, 10/day TikTok+IG):**
Formula = *specific acknowledgment + one substantive addition from the doctrine
+ (optional) light question.* Never link. Never "great post!". Example under a
BTC volatility post: `The underrated part of days like this: most short-horizon signals (esp. order-book pressure) lose their predictive value entirely in spike-reverse conditions. Systems that classify "violent" as untradeable skip the whole mess. Sitting out IS a position.`

---

## §10 — Hashtag banks

### 10.1 X — use sparingly (0–1 per post; hashtags are weak on X)
`#Kalshi` `#PredictionMarkets` — only these two, only when topical.

### 10.2 TikTok (pick 4–6 per video: 2 broad + 2 niche + 1 community + 1 trending-that-day)
- Broad: `#fintok #moneytok #trading #investing #bitcoin #crypto`
- Niche: `#tradingbot #algotrading #kalshi #predictionmarkets #quanttrading #daytrading #automatedtrading`
- Community: `#buildinpublic #techtok #sidehustlecheck #fintech`
- Avoid: `#passiveincome #getrichquick #forexsignals` (scam-adjacent, hurts credibility & triggers moderation)

### 10.3 Instagram (3–5 per Reel, in caption)
Core rotation: `#tradingbot #kalshi #predictionmarkets #algotrading #bitcoin #fintech #quant #btc #tradingdiscipline #buildinpublic` — pick by topic, never the same 5 twice in a row.

### 10.4 Facebook — none (hashtags do nothing on FB).

---

## §11 — CTA & hook banks

### CTAs (rotate; one CTA per post, not three)
- `Watch it decide, live: t.me/flippulse` (proof CTA — use most)
- `The 9 rules it checks, free: [lead magnet link]` (capture CTA)
- `Start in paper mode: go.flippulse.com` (conversion CTA — max 1/day)
- `Question about how it works? Comments are open — founder answers everything.` (engagement CTA)
- `Follow for the daily receipts 🧾` (follow CTA — on viral-candidate posts)

### Hook bank (first lines that stop the scroll — reuse across platforms)
1. `Our trading bot did nothing today. Here's why that's the product.`
2. `This is a screenshot of a bot refusing to make money. Look closer.`
3. `Every trading bot ad lies to you the same way.`
4. `96 Bitcoin markets a day. A human can trade maybe 5 of them well.`
5. `My bot benched itself last month. On purpose. Statistically.`
6. `The most expensive words in trading: "one more trade."`
7. `A trading bot with a public diary. Every decision. Even the ugly ones.`
8. `We made "going live" deliberately annoying. Here's why.`
9. `Your money never touches our hands. That sentence should be standard.`
10. `Rule #1 of trading bots: if you can't watch it on paper first, run.`
11. `It's 2am. The order book looks juicy. The bot says no. Here's what it knows.`
12. `Three losses in a row. Watch what happens next. (Nothing. That's the point.)`
13. `Discipline as a subscription. $99/month. Weirdly, it works.`
14. `The bot that texts you its homework before every trade.`
15. `Stop asking "what's the win rate." Start asking THIS.`
