# Testing Auto-Provisioning — No Terminal Required

This guide shows how to test FlipPulse's automated provisioning using **only
the browser**: GitHub, Railway, and Stripe web dashboards. You never open a
terminal or run a command.

There are two independent things you can test, from cheapest to most complete:

| Test | What it proves | Where | Cost |
|---|---|---|---|
| **A. Run the test suite** | The provisioning *logic* is correct (state machine, paid gate, resume, verification) | GitHub Actions tab | Free, ~1 min, no side effects |
| **B. Test signup end-to-end** | The *whole chain* works: form → Stripe → auto-provision → running bot → Telegram alert | Browser + Railway + Stripe | A real (paper-mode) test bot on Railway |

Run **A** whenever you change anything. Run **B** once end-to-end whenever you
change provisioning settings or the boot markers.

---

## A. Run the test suite from GitHub (no code, no terminal)

The repo has a GitHub Actions workflow (`.github/workflows/tests.yml`) that runs
every test — including the 18 provisioner tests — on a clean cloud machine.

**It runs automatically** on every push and on every pull request. To see the
result:

1. Open the repo on GitHub.
2. Click the **Actions** tab (top of the page).
3. Click the latest **tests** run. A green ✅ means everything passed; a red ❌
   opens the log showing which test failed.
4. On a pull request, the same result appears at the bottom of the PR as a
   **check** — green means safe to merge.

**To run it on demand** (without pushing anything):

1. **Actions** tab → click **tests** in the left sidebar.
2. Click **Run workflow** (button on the right) → pick the branch → **Run
   workflow**.
3. Refresh; the new run appears at the top. Click it to watch it finish.

That's the full "does the provisioning logic work?" test, entirely in the
GitHub UI.

---

## B. End-to-end test signup (browser + Railway + Stripe)

This drives a real signup through the live onboarding service in **Stripe test
mode**, so no real money moves, but it exercises the actual Railway API and
produces a real (paper-mode) bot you then delete.

### B0. One-time: make sure the onboarding service is set up for a test

In the **Railway dashboard**, open your **onboarding** service → **Variables**
tab and confirm these are set:

| Variable | Value for a test |
|---|---|
| `RAILWAY_API_TOKEN` | your Railway token (enables all automation) |
| `ONBOARDING_FERNET_KEY` | your encryption key (already set) |
| `STRIPE_SECRET_KEY` | your **test** key, starts with `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | the signing secret for the test webhook |
| `STRIPE_MONTHLY_PRICE_ID` / `STRIPE_SETUP_PRICE_ID` | test-mode price ids |
| `AUTO_PROVISION` | `true` |
| `ADMIN_TOKEN` | any secret string — unlocks the `/admin` control page |

> **Keep the test off your customer fleet.** Set
> `PROVISION_REPO_BRANCH` to a throwaway branch name (e.g. `test-provision`)
> **before** you run the test, so the test bot does **not** track the live
> `release` branch. Change it back afterward. `RAILWAY_PROJECT_ID` and
> `RAILWAY_ENVIRONMENT_ID` are filled in by Railway automatically — leave them
> alone.

After changing variables, Railway redeploys the service. Then check readiness:

- In a browser, open **`https://<your-onboarding-host>/healthz`**.
- You want to see `"railway": true` and `"auto_provision": true` in the JSON.

### B1. Submit the signup form

1. Open **`https://<your-onboarding-host>/`** in a browser.
2. Fill in the form with **test** details (a real Kalshi **demo/paper** key id +
   private key, and a Telegram bot token + chat id you own — the form validates
   the Telegram token live, so use a real test bot).
3. Submit. You'll be sent to **Stripe Checkout**.

### B2. Pay with a Stripe test card

On the Stripe Checkout page (it will say *Test Mode*), use Stripe's test card:

- Card number: **4242 4242 4242 4242**
- Expiry: any future date · CVC: any 3 digits · ZIP: any

Complete the checkout. You'll land on the success page.

### B3. Watch it provision itself

Payment triggers everything automatically — you just watch:

- **Operator Telegram:** within a few minutes you get
  **`✅ FlipPulse bot provisioned …`** with a Railway project link, the
  customer's dashboard URL, and a generated dashboard password. (A ❌ message
  instead tells you the exact step that failed and why.)
- **Railway dashboard:** open your onboarding service's **project**. A new
  service named **`<handle>-bot`** appears *in the same project* (not a new
  project), builds, and goes green.
- **The `/admin` control page** (your browser replacement for every CLI
  command) — see next.

### B4. Use the /admin page as your control panel

Open **`https://<your-onboarding-host>/admin?token=<ADMIN_TOKEN>`** (the token
sets a cookie; the page 404s without it).

- The **list** shows every signup with its payment status.
- Click a signup to open its **deploy view**, which shows the provisioning
  status live:
  - **⏳ IN PROGRESS** — provisioning is running; refresh to update.
  - **✅ PROVISIONED** — done, with an **Open Railway project →** link.
  - **❌ FAILED** — shows the failing step and error, plus a link to the
    partial Railway project.
- If it failed (or never started), the page shows a button:
  - **🚀 Provision bot now** — starts provisioning (this is the browser
    equivalent of the CLI `provision` command; it skips the paid gate).
  - **↻ Retry provisioning** — appears after a failure; resumes from the last
    completed step. Safe to click repeatedly — it never duplicates resources.

So the entire operator workflow — provision, retry, check status — is these
buttons on the `/admin` page. You never need the CLI.

### B5. Confirm the bot is healthy

- The provisioned bot starts in **paper mode** (`DEMO_MODE=true`) by design — it
  will **not** trade real money.
- Open the **dashboard URL** from the Telegram success message and log in with
  the generated password to see the bot's self-service dashboard.
- In Telegram, the bot sends its own boot alert; send it **`/status`** to
  confirm it's alive.

### B6. Clean up the test bot (Railway UI)

When you're done testing, delete the test bot's service **in the Railway
dashboard** (this is the browser equivalent of the CLI `deprovision` command):

1. Railway → open the **project** → click the **`<handle>-bot`** service.
2. **Settings** tab → scroll to the bottom → **Delete Service** → confirm.
3. This removes **only that one test bot**. The shared project, the onboarding
   service, and every other bot are untouched.

Then, if you changed it in B0, set **`PROVISION_REPO_BRANCH`** back to
**`release`** so future real customers deploy from the live fleet branch.

---

## What "provisioning" actually does (for reference)

Behind the scenes, a paid signup runs this sequence automatically (all via
Railway's API — no UI clicks by you):

1. **Locate** the shared Railway project (the one the onboarding service runs
   in).
2. **Create** a service `<handle>-bot` from the FlipPulse repo.
3. **Attach** a `/data` volume so the bot's state survives redeploys.
4. **Generate** a public dashboard domain + password.
5. **Inject** the full variable set (customer keys, `DEMO_MODE=true`, all
   `/data` paths).
6. **Deploy** and **verify** — wait for a green deploy, then confirm the boot
   logs show the Kalshi key loaded and the sizing banner.

Full architecture, failure handling, and every configuration knob live in
[`AUTOMATED_PROVISIONING.md`](AUTOMATED_PROVISIONING.md).
