# Re-enabling the Performance Fee — checklist

The 20% performance fee was **temporarily removed** (see PR #8). Everything is a
disabled placeholder set to **0%**, and the billing engine in `bot.py` is intact — so
turning it back on is a small, well-defined job. Work top to bottom.

> ⚠️ **Do step 0 first.** Charging a percentage of trading profits on accounts your
> software trades can trigger investment-adviser / CTA rules (SEC Rule 205‑3 "qualified
> client" thresholds; CFTC CTA/CPO rules — Kalshi is CFTC-regulated). *Not legal advice.*

- [ ] **0. Compliance sign-off** — get a lawyer/compliance OK before any of the below.

## A. Flip it on (you can do these yourself in Railway — no code)

- [ ] **Each customer's bot service** → add variable **`PERF_FEE_PCT`** = `0.20`
      (the bot then *reports* the monthly fee to you via Telegram + `billing.log`; it never
      charges automatically).
- [ ] **Onboarding form service** → add variable **`ONBOARDING_PERF_PCT`** = `20`
      (so the form/receipt shows the fee). *Note: the form's pricing text still needs the
      code change in section B to actually display a third line — the variable alone only
      sets the number.*

## B. Restore the wording + artifacts (code change — ask Claude, or revert PR #8)

The fastest path is to **revert the removal commit** (PR #8) and then keep the Railway
vars from section A. Otherwise, restore these by hand and regenerate:

- [ ] `onboarding/templates/form.html` — re-add the 3rd pricing box (`{{ perf_pct }}%` /
      "of monthly profit"), the high-water-mark hint, and the perf clause in the agreement.
- [ ] `onboarding/templates/success.html` — re-add the performance-fee sentence.
- [ ] `onboarding/app.py` — set `ONBOARDING_PERF_PCT` default back to `"20"` (optional).
- [ ] `docs/FlipPulse_Customer_Onboarding.html` — re-add the **Performance** pricing tier +
      guarantee line → regenerate the PDF with headless Chromium.
- [ ] `marketing/build_demo.py` — scene 7 CTA → add `+ 20% of profits` → rerun
      `python marketing/build_demo.py`.
- [ ] `business/build_model.py` — Inputs perf % `0.0` → `0.20` (and set include-in-totals
      `Inputs!B8` = 1 if you want it in headline numbers) → rerun `python business/build_model.py`.
- [ ] `business/build_onepager.py` — restore the "20% of monthly profit" revenue line + the
      upside bullet → rerun + re-render the PDF.
- [ ] `ADMINISTRATOR_ONBOARDING.md` §9 — restore the performance-fee row and the active §9b
      wording. Update `business/README.md`, `onboarding/README.md`, `marketing/README.md`,
      `CUSTOMER_ONBOARDING.md`.
- [ ] `bot.py` / `.env.example` — optionally change the `PERF_FEE_PCT` **default** from
      `0.0` back to `0.20` (not required if you set the env var per section A).

## C. Monthly, once live

- [ ] Read each customer's fee from the **operator Telegram** (`💵 MONTHLY BILLING …`) or
      `billing.log`; skip paper-mode months.
- [ ] In Stripe → the customer → **Add invoice item** for that amount (charged against the
      card already on file). See `ADMINISTRATOR_ONBOARDING.md` §9b.

## Where the fee lives (reference)

| Piece | File | Current placeholder |
|---|---|---|
| Bot billing engine | `bot.py` (`BillingState`, `PERF_FEE_PCT`) | `0.0` — report dormant |
| Bot env default | `.env.example` | `PERF_FEE_PCT=0.0` |
| Form display | `onboarding/app.py`, `templates/` | `ONBOARDING_PERF_PCT=0`, not shown |
| Customer PDF | `docs/FlipPulse_Customer_Onboarding.html` | tier removed |
| Demo video | `marketing/build_demo.py` | CTA line removed |
| Business model | `business/build_model.py` | Inputs perf % = 0 |
| One-pager | `business/build_onepager.py` | "TBD (not currently charged)" |
| Admin guide | `ADMINISTRATOR_ONBOARDING.md` §9 | "on hold" |
