# 10 — Scaling Plan: what changes at each customer milestone

Revenue math baseline: each customer ≈ $99/mo + $99 once. Costs from
`business/FlipPulse_Business_Model.xlsx` (~$5/mo/bot infra, ~92% gross margin).
The theme of this file: **each tier, you buy back your time with margin, in a
specific order — ops first, content second, strategy never.**

---

## 100 customers (~$9.9K MRR) — "Stop doing everything yourself"
**What changes:**
- Marketing has proven channels; the constraint becomes founder hours split
  between ops (deploys, support) and growth.
**Automate:** onboarding→deploy pipeline hardening (submission → env vars →
Railway deploy as close to one command as possible — the admin CLI already
gets you most of the way); Stripe dunning emails (Stripe → Settings → Billing
→ revenue recovery ON); the Friday report (already done via Make).
**Outsource/hire:** **VA #1** (10–15 hrs/wk, $400–800/mo, hire via
OnlineJobs.ph): Metricool scheduling from the calendar, CapCut editing from
your raw takes, comment triage with the §9 templates (they draft, you approve
via Metricool Drafts). You keep: Reddit, X replies, all customer conversations.
**Marketing changes:** referral program moves to real software (Rewardful,
$49/mo, wires into Stripe); paid budget to $500–1K/mo on the 2–3 proven
creatives; testimonial/UGC engine becomes a weekly slot.
**Ops guardrail:** support inbox SLA (24h) and a status page (free:
status.railway.app-based or a pinned Telegram message). Reputation is now a
growth channel.

## 500 customers (~$49.5K MRR) — "Build the machine that runs the machine"
**What changes:** you're at the business model's year-1 target; churn math now
dominates growth math (5% churn = 25 lost/mo — retention IS marketing).
**Automate:** full onboarding self-serve (form → automated deploy → automated
paper-mode start with zero founder touch); customer health dashboard (bots
alerting, churn-risk flags = customers who muted alerts); weekly analytics
fully hands-off.
**Outsource/hire:** **Social media manager** (part-time contractor,
$1.5–2.5K/mo) owns calendar/library/scheduling/community, works from this
playbook — literally hand them this folder; **support VA** separate from
content VA. Consider a fractional video editor on retainer.
**Delegate:** all scheduling + first-draft content. You still: final approval
(compliance!), founder voice on X, Reddit AMAs, influencer relationships.
**Marketing changes:** scheduler upgrade (Vista Social/Hootsuite for team
seats + approval workflow); paid $3–5K/mo across Meta/TikTok + first YouTube
pre-roll tests; SEO becomes a real program (10+ articles, a comparison page
for every rival bot); launch a proper affiliate program publicly.
**New risk to manage:** you are now visible. Get a real compliance review of
all public claims by a securities/derivatives attorney (~$2–5K one-time) —
before someone else reviews them for you. Revisit the parked performance-fee
idea ONLY through that attorney (`REENABLE_PERFORMANCE_FEE.md`).

## 1,000 customers (~$99K MRR) — "It's a company now"
**What changes:** solo-operator ceiling is hit everywhere at once.
**Automate:** fleet operations (monitoring dashboards, auto-restarts, deploy
queues — a junior DevOps contractor's first project); billing edge cases;
compliance checklist as a literal pre-publish bot (a script that greps drafts
for banned phrases from `11_COMPLIANCE_KIT.md`).
**Hire (first real employees):** ops/support lead (FT), marketing lead (FT —
promotes your contractor or hires above them). You become: product + brand
voice + partnerships.
**Delegate:** the entire content engine (you record 2 hrs of founder footage
weekly; the team cuts everything else); influencer program management.
**Marketing changes:** $10–20K/mo paid with proper attribution (a real
analytics stack: GA4 + server-side events + Northbeam-class tool when spend
justifies); PR push (fintech podcasts, "prediction market economy" press
angle); a real brand site separate from the onboarding app; consider a free
tier (paper-mode-only free forever) as top-of-funnel — at this scale the infra
cost is noise and it's a devastating competitive moat.

## 5,000 customers (~$495K MRR) — "Moats and machines"
**What changes:** you're a category leader; copycats exist; distribution
advantages compound.
**Automate:** everything in ops that touches >1% of customers; ML-ish churn
prediction (usage/alert engagement scoring); content repurposing pipeline
(one founder video → auto-clipped by an editor team + tooling).
**Hire:** head of growth, 2–3 person content studio, dedicated compliance
officer (this is non-negotiable at this revenue in a trading-adjacent
business), community manager for the (by now) large Telegram/Discord.
**Delegate:** channel P&Ls to channel owners with CAC/LTV targets; you review
weekly, decide monthly.
**Marketing changes:** brand > performance shift (sponsorships: finance
podcasts, quant YouTube, maybe Kalshi-event presence); international/timezone
expansion of content; proprietary data as PR ("what 5,000 bots saw in the BTC
order book this quarter" — anonymized, aggregated, legal-approved: journalists
will eat it); W-2 sales isn't a thing at $99/mo, but B2B2C partnerships
(fintech apps embedding FlipPulse) become the new growth curve.

## 10,000 customers (~$990K MRR / ~$12M ARR) — "Choose the next game"
**What changes:** growth at this size comes from product surface, not posting
cadence. The playbook you're holding becomes one department's SOP.
**The strategic choices (pick deliberately, with advisors):**
1. **Product expansion** — more markets (ETH 15-min, hourly BTC, weather/econ
   series), portfolio-of-strategies per customer, an actual dashboard product.
2. **Platform play** — open the deploy/monitoring infrastructure to
   third-party strategy authors (revenue share); FlipPulse becomes the
   "Shopify of prediction-market bots."
3. **Regulated step-up** — with counsel: pursue the registrations/licensing
   that unlock managed accounts and performance fees properly.
4. **Exit** — a fintech/exchange acquirer buys distribution + fleet ops;
   10K retained subscribers at 92% margin is a real asset.
**Org:** ~15–25 people; you hold vision, brand voice (still the X account —
founders who keep posting stay beloved), and capital allocation.
**The rule that got you here still applies:** receipts over hype, discipline
over volume, and never publish a number legal hasn't blessed.

---

## The constant at every tier
Re-read `01_MASTER_MARKETING_PLAN.md` §2 before each hire and each new
channel: the brand IS the compliance-safe transparency. Scale everything
except the thing that made it work.
