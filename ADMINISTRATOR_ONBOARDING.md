# Administrator Onboarding — Deploying a New Customer Environment

This is the operator/administrator runbook for standing up **one new customer** on
FlipPulse. Every customer gets their own Railway project, their own Kalshi key, and
their own Telegram bot. There is no shared dashboard, no signup, and no multi-tenant
supervisor — one repo/template → one Railway project → one bot per customer.

> **Customer-facing intake:** customers sign up through the **digital onboarding
> form** (the Flask service in [`onboarding/`](onboarding/README.md)) — it collects
> their details + chosen Trading Format, encrypts their keys, takes payment via
> Stripe, and alerts you. The
> [`docs/FlipPulse_Customer_Onboarding.pdf`](docs/FlipPulse_Customer_Onboarding.pdf)
> is the branded leave-behind (how it works, formats, pricing). This runbook is what
> **you** do once a submission lands.

Every customer starts in **paper mode** (`DEMO_MODE=true`). Going live is a separate,
deliberate step (last section). Budget ~15 minutes per customer.

> ## ⚡ This runbook is now automated
> Everything below from §2 through §6 (project, service, volume, variables, deploy,
> verify) is executed automatically by the onboarding service the moment Stripe
> confirms payment — see **[`AUTOMATED_PROVISIONING.md`](AUTOMATED_PROVISIONING.md)**
> for the one-time setup (`RAILWAY_API_TOKEN`) and how it works. With automation on,
> a signup's happy path needs **zero** operator action: you get a
> "✅ FlipPulse bot provisioned" Telegram alert with the project link, and `/admin`
> shows the bot as running. Manual fallbacks: the **Provision bot now** button on the
> `/admin` deploy view, or `python admin_cli.py provision <id>`.
>
> The steps below remain as the **manual fallback** and as the reference for what the
> automation does. Going live (§8) is still deliberately manual.

---

## 0. A signup lands (from the digital form)

When a customer completes the onboarding form you get a **Telegram alert** and a
**submission file** in the onboarding service's `submissions/` inbox. Two ways to pull the
deploy values out of it:

- **Operator dashboard:** open `https://<onboarding-host>/admin?token=<ADMIN_TOKEN>` — it
  lists every signup and each links to a deploy view with the ready-to-paste variables.
- **CLI:**
  ```bash
  cd onboarding
  ONBOARDING_FERNET_KEY=<your key> python admin_cli.py list          # find the id
  ONBOARDING_FERNET_KEY=<your key> python admin_cli.py show <id>     # decrypt → env vars
  ```

Either one gives the ready-to-paste Railway variables (decrypted Kalshi key + PEM,
Telegram token/chat id, `PAPER_BALANCE` = their starting balance, `TRADING_FORMAT` =
their pick). That is everything you need for the steps below. Confirm `payment_status`
is `paid` (see §9 Billing) before you deploy live.

> Doing it manually instead (no form)? You just need the same items: Kalshi API Key ID +
> RSA private-key PEM, Telegram bot token + chat id, starting balance, chosen format
> (`conservative`/`balanced`/`aggressive`, default balanced), and a short handle.

---

## 1. How sizing works (why you don't set dollar amounts per customer)

FlipPulse sizes **every trade as a percentage of the current balance**, resolved to
dollars at one place in the code (`active_trade_size` in `bot.py`). Consequences for

## 1. How sizing works (why you don't set dollar amounts per customer)

FlipPulse sizes **every trade as a percentage of the current balance**, resolved to
dollars at one place in the code (`active_trade_size` in `bot.py`). Consequences for
you as the deployer:

- You **do not** tune per-customer dollar stakes. You pick a **Trading Format** and the
  percentages scale automatically to whatever balance the customer funds.
- The stake **compounds** as the account grows and **de-risks** as it shrinks — no
  manual resizing when a customer adds funds.
- The three formats seed these percentage knobs (run `python formats.py` to print them):

  | Format | Normal | Recovery | Max/trade | Ladder | Gates |
  |---|---|---|---|---|---|
  | `conservative` | 5% | 2% | 8% | off | strictest |
  | `balanced` *(default)* | 10% | 3% | 15% | off | doctrine default |
  | `aggressive` | 20% | 5% | 30% | on (≤2×) | relaxed |

- To override a format for one customer, set `NORMAL_TRADE_PCT`, `RECOVERY_TRADE_PCT`,
  or `MAX_TRADE_PCT` (fractions, e.g. `0.12`) explicitly — an explicit env var always
  wins over the format's default.

---

## 2. Create the Railway service for the bot

Each customer bot is just **another Railway service pointed at the FlipPulse repo** — the
code is identical for everyone; only the Variables (step 4) differ. You do **not** need a
separate repo per customer.

1. In Railway: **New Project → Deploy from GitHub repo →** pick **`FlipPulse`** (the repo
   that actually has the code). Name the service after the customer.
2. Service → **Settings → Source → Root Directory → leave it BLANK/empty.**

> ⚠️ **Root Directory is the make-or-break setting, and it's the OPPOSITE of the sign-up
> site.** A **customer bot** = Root Directory **blank** → Railway reads the repo-root
> `railway.toml` → runs `python bot.py` (the trader). The **onboarding form** = Root
> Directory `onboarding` → runs the website. Don't mix them up.
>
> **Do NOT** create a new empty GitHub repo (e.g. `Bird_Bot`) and point Railway at it —
> an empty repo has no `main` branch, which is why Railway shows *"Connected branch does
> not exist."* Always deploy from the **FlipPulse** repo.

Railway builds with Nixpacks and runs `python bot.py`. It will crash-loop on first boot
until env vars are set (step 4) — that's expected.

*(If you truly want a dedicated repo per customer, make it via GitHub's **Use this
template** on the FlipPulse repo — never an empty "New repository" — so it ships with the
code and a `main` branch.)*

---

## 3. Attach a volume for state

The bot writes its recovery/probation/ladder/bucket/status files to `/data` so they
survive redeploys.

1. In the Railway service → **Volumes → New Volume**.
2. Mount path: **`/data`**.
3. 1 GB is plenty.

The `.env.example` `*_STATE_PATH` variables already point at `/data/...`, so as long as
the mount path is exactly `/data` you just copy them in (step 4) and state persists. If
you leave them unset, the bot falls back to a container-local file wiped on every
redeploy — so keep them set.

---

## 4. Set the environment variables

**Easiest:** copy the whole block from the customer's `/admin` deploy view (or
`admin_cli.py show <id>`) and paste it into Railway's **Variables → Raw Editor**. Every
value is a single line — including the key — so nothing can get mangled. Then add the
`/data` path variables from `.env.example`.

Set the following (see `.env.example` for the full annotated list):

| Variable | Value |
|---|---|
| `KALSHI_API_KEY_ID` | The customer's Kalshi API Key ID |
| `KALSHI_PRIVATE_KEY_PEM_B64` | The customer's key as a **single-line base64 blob** (from the `/admin` deploy view / `admin_cli.py`). Foolproof — a single line can't be mangled by a multi-line paste. |
| `DEMO_MODE` | `true` (always start in paper) |
| `PAPER_BALANCE` | The customer's starting balance, e.g. `1000` |
| `TRADING_FORMAT` | `conservative` \| `balanced` \| `aggressive` — the format they chose |
| `TELEGRAM_BOT_TOKEN` | From BotFather (step 5) |
| `TELEGRAM_CHAT_ID` | The customer's chat id (step 5) |
| `TELEGRAM_OPERATOR_CHAT_ID` | *(optional)* your own chat id to also receive every alert — see step 7 |

**Optional per-customer sizing overrides** (only if you want to deviate from the chosen
format; all are fractions of balance):

| Variable | Meaning |
|---|---|
| `NORMAL_TRADE_PCT` | Full stake fraction (e.g. `0.10`) |
| `RECOVERY_TRADE_PCT` | Reduced stake while clawing back a loss (e.g. `0.03`) |
| `MAX_TRADE_PCT` | Hard ceiling on any single trade (e.g. `0.15`) |

Copy the `*_STATE_PATH`, `STATUS_SNAPSHOT_PATH`, and `HEALTH_LOG_PATH` values from
`.env.example` as-is (they point at `/data`). Do **not** leave them blank — the code's
fallback writes to a container-local file that is lost on redeploy. Only change them if
you mounted the volume somewhere other than `/data`.

---

## 5. Create the customer's Telegram bot (BotFather)

Each customer gets a dedicated bot so their alerts and commands are isolated.

1. In Telegram, open **@BotFather → `/newbot`**.
2. Name it, e.g. `FlipPulse <Customer>` with username `flippulse_<customer>_bot`.
3. BotFather returns a **token** → that's `TELEGRAM_BOT_TOKEN` (step 4).
4. Have the customer open a chat with their new bot and send `/start`.
5. Get the **chat id**: message the bot, then visit
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and read
   `result[].message.chat.id`, or use `@userinfobot`.
6. Put that value in `TELEGRAM_CHAT_ID` (step 4).

---

## 6. Deploy & verify

1. After setting all variables, trigger a redeploy (Railway → **Deploy**).
2. Watch the deploy logs until the bot boots cleanly (Kalshi auth OK, Telegram
   connected, no crash loop). The boot banner logs the active percentages, e.g.
   `Sizing (% of balance): normal=10.0% recovery=3.0% max=15.0%`.
3. In the customer's Telegram chat, exercise the read-only commands (from
   `command_bot.py`, started by `bot.py` on boot):
   - **`/status`** — mode (paper/live), trading format, balance and session PnL, W/L
     record, ladder/recovery/probation mode and **the active stake % (and ~$)**, open
     positions, session state, last signal, last-tick time.
   - **`/health-log [n]`** — tails the recent health/activity log.
   - **`/help`** — lists the commands.

   > The bot only *answers* these read-only commands; it also *sends* alerts on its own,
   > but **only when something happens**: boot, trade entry, win/loss settlement, and
   > triggered guardrails. There is no heartbeat and no scheduled summary — a quiet chat
   > means no trades fired; use `/status` to check liveness on demand. It does **not**
   > accept any command that changes trading — no order placement, no `DEMO_MODE` flip.

4. Confirm the boot message arrives in Telegram. If you set
   `TELEGRAM_OPERATOR_CHAT_ID`, confirm it reached you too.

A green verify = bot booted, Kalshi authenticated in paper mode, `/status` responds and
shows the expected format and stake percentage.

---

## 7. Operator oversight (watching all customers)

No central dashboard needed. Pick one:

- **Operator chat id (simplest, recommended):** set `TELEGRAM_OPERATOR_CHAT_ID` to your
  own chat id (comma-separated for several operators). `telegram_utils.py` fans every
  alert out to the customer chat *and* each operator chat. Your operator commands
  (`/status`, `/health-log`) are answered too, since operator chat ids are authorized
  alongside the customer's.
- **Shared group:** create a Telegram group per customer, add the customer's bot and
  both of you, and set `TELEGRAM_CHAT_ID` to the group's id.

---

## 8. Going live (later, deliberate step)

Do **not** do this during initial onboarding. When the customer is ready:

1. Confirm the customer's Kalshi account is funded and the key has trade permissions.
2. Set `DEMO_MODE=false` in Railway Variables.
3. Redeploy and immediately verify via `/status` that it reports **live** mode.
4. Watch the first few trades / alerts closely. Because sizing is a percentage of the
   real balance, the first live stake will be `NORMAL_TRADE_PCT × funded balance`.

---

## 9. Billing — pricing & Stripe

**Pricing (the numbers baked into the form + PDF):**

| Charge | Amount | When | How |
|---|---|---|---|
| **Setup fee** | **$150** | Once, at signup | Stripe (first invoice) |
| **Subscription** | **$99 / month** | Monthly | Stripe recurring |
| ~~Performance fee~~ | **— on hold (not charged)** | — | Placeholder — see §9b to re-enable later |

> **Performance fee is temporarily removed.** It's a placeholder set to 0% everywhere
> (`PERF_FEE_PCT=0`), so nothing about profit share is shown to customers or billed. Only
> the flat **setup + subscription** run today — ordinary SaaS.

> **You never touch customer funds.** Money stays on Kalshi; you bill separately via
> Stripe with a **card on file**.

### 9a. One-time Stripe setup

1. Create a **Stripe account** and grab your secret key (`sk_live_...`).
2. **Products & Prices:**
   - Product "FlipPulse Membership" → recurring **Price $99/month** → copy its
     `price_...` id → `STRIPE_MONTHLY_PRICE_ID`.
   - Product "FlipPulse Setup" → one-time **Price $150** → copy its id →
     `STRIPE_SETUP_PRICE_ID`.
3. In the **onboarding service** (`onboarding/`) set `STRIPE_SECRET_KEY`,
   `STRIPE_MONTHLY_PRICE_ID`, `STRIPE_SETUP_PRICE_ID`, and `PUBLIC_BASE_URL` (its public
   https URL). The form then runs Checkout in `subscription` mode: the setup fee lands on
   the first invoice, the subscription recurs monthly, and the **card is saved** on file
   for any future invoices.
4. Add a Stripe webhook to `POST /stripe/webhook` for
   `checkout.session.completed` and set `STRIPE_WEBHOOK_SECRET` — the submission is then
   auto-marked `paid`, **and (with `RAILWAY_API_TOKEN` set) the customer's bot is
   provisioned automatically** — see
   [`AUTOMATED_PROVISIONING.md`](AUTOMATED_PROVISIONING.md).

See [`onboarding/README.md`](onboarding/README.md) for the full env-var list and how to
deploy the form as its own Railway service.

### 9a-i. Early-adopter offer — "Founder 100" (live)

The launch offer: **the first 100 subscribers pay $0 on their first invoice** — the
$150 setup fee **and** the first month ($99) are both waived — then normal $99/month
billing begins from month 2. Regular list price stays **$150 setup + $99/mo**, so the
discount is real and time-limited. It never touches the recurring price, so LTV is
intact.

**Stripe side (one-time):**
1. Dashboard → **Product catalog → Coupons → + New** → **Amount off → $249.00 USD**
   (= $150 setup + $99 first month), Duration **Once**, **Max redemptions 100**. Name it
   `FOUNDING100`. Save — copy its **coupon id** (looks like `10xGeLZu`).
2. Cap is enforced by Stripe's `max_redemptions`; when it hits 100 the coupon stops
   applying automatically.

**Onboarding service side — pick ONE delivery mode** (Stripe rejects a session that
uses both):
- **Automatic (recommended):** set `FOUNDING_COUPON_ID` to the coupon id. Every signup
  gets the discount with nothing to type. When the coupon is exhausted/expired, checkout
  **retries once at full price** so signups never break — the offer just ends. Unset the
  var to end it early.
- **Code-based:** leave `FOUNDING_COUPON_ID` unset, set `STRIPE_ALLOW_PROMO_CODES=true`,
  and on the coupon create a **promotion code** (e.g. `FOUNDER100`) to hand out. The
  Checkout page then shows an "Add promotion code" box.

### 9b. (Later) re-enabling a performance fee — currently DISABLED

> Full step-by-step: [`REENABLE_PERFORMANCE_FEE.md`](REENABLE_PERFORMANCE_FEE.md).

The performance-fee engine is still in the code but **switched off** (`PERF_FEE_PCT`
defaults to `0`, so the bot computes/reports nothing). **Do not enable it without a
compliance review** — charging a percentage of trading profits on accounts your software
trades can trigger investment-adviser / CTA rules (e.g. SEC Rule 205‑3 "qualified client"
thresholds; CFTC CTA/CPO rules since Kalshi is CFTC-regulated). *Not legal advice.*

When (and only when) you're cleared to turn it on:

1. Set `PERF_FEE_PCT` (e.g. `0.20`) on each bot service. The bot then reports — never
   charges — at each **UTC month rollover**, per customer: the month's balance change, the
   **billable profit** (balance above their all-time **high-water mark**, so a
   dip-and-recover is never billed twice), and the **fee** = `PERF_FEE_PCT` × billable
   profit. It arrives via operator Telegram (`💵 MONTHLY BILLING …`), the
   `BILLING_LOG_PATH` file, and the status snapshot's `billing` block.
2. You then raise it in Stripe as an **invoice item** on that customer's subscription
   (Dashboard → Customer → *Add invoice item*), charged against the card on file. Re-add
   the performance-fee line to the form/PDF/one-pager copy before you advertise it.

---

## Troubleshooting

**"Connected branch does not exist" when creating the service.**
The repo you picked is **empty** (no `main` branch). Deploy from the **FlipPulse** repo
instead (Settings → Source → Disconnect → reconnect to `FlipPulse`, branch `main`), and
leave **Root Directory blank**. See §2.

**Deploy crash-loops with `Could not read KALSHI_PRIVATE_KEY_PEM …` (or the older
`Unable to load PEM file … InvalidPadding`).**
The private-key value is **incomplete or altered** — almost always a multi-line paste
that got truncated (`InvalidPadding` = the key body is literally missing characters). Fix
it with the **foolproof single-line** method (no code change needed):
1. Open the customer's **`/admin` deploy view** and copy the **`KALSHI_PRIVATE_KEY_PEM_B64`**
   line — it's one long line of base64 that can't be mangled.
2. In Railway → the bot service → **Variables** → **delete any old
   `KALSHI_PRIVATE_KEY_PEM`** and add **`KALSHI_PRIVATE_KEY_PEM_B64`** = that value (Raw
   Editor is easiest). Make sure the whole line copied — nothing cut off.
3. Redeploy → the logs should show `✅ RSA private key loaded.`
   *(As a safety net the bot also auto-repairs escaped `\n`, spaces, and wrapping quotes on
   a raw `KALSHI_PRIVATE_KEY_PEM`; but the B64 var avoids the problem entirely. New signups
   are also validated at the form, so a truncated key is rejected before it ever reaches a
   bot.)*
   If it still fails, the key the customer provided is itself incomplete — have them
   **rotate the Kalshi key** and re-submit.

**Booted but `/status` doesn't answer.** Confirm `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`
are this customer's, the volume is mounted at `/data`, and the deploy logs show a clean
Kalshi auth + Telegram connect.

---

## Out of scope (by design)

- Multi-tenant supervisor or running many bots on one box
- Central monitoring dashboard
- In-app fund custody (funds always stay on Kalshi; you bill via Stripe)

One customer = one repo/template clone = one Railway project = one bot; signups arrive
via the onboarding form and billing runs through Stripe.
