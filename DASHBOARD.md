# FlipPulse — Customer Dashboard

Every customer bot serves its own **login-protected web dashboard** so the
customer can fine-tune their setup themselves — no redeploy, no operator work.
Changes save instantly (except Trading Format, which applies on the next restart).

What the customer can change:

| Control | What it does | Applies |
|---|---|---|
| **Risk %** | Full-size stake as a % of balance (same knob as the Telegram `/risk` command). Clamped to the safe range. | Instantly |
| **Set aside ($)** | Ring-fences a dollar amount the bot will never stake — it trades only the balance above it. | Instantly |
| **Telegram alerts** | Mute routine trade-entry / win / loss alerts. Safety, halt and recovery alerts always stay on. | Instantly |
| **Trading format** | Overall posture: Conservative / Balanced / Aggressive. | Next restart |

> The dashboard **only changes bot settings**. Funds never leave Kalshi, and it
> cannot place trades, withdraw, or switch a bot from paper to live.

---

## For the customer — how to access your dashboard

You'll receive two things from us after your bot is set up:

1. **Your dashboard link** — looks like `https://your-bot-name.up.railway.app`
2. **Your password**

Then:

1. **Open the link** in any browser (phone or computer).
2. Enter your **password** and tap **Sign in**. You stay signed in on that device
   for 12 hours.
3. You'll see your balance, the amount in play, and today's PnL, followed by the
   settings cards.
4. Change any setting and tap its **Save** button. A green confirmation appears.
   - **Risk %** — type a number like `8` for 8% and Save.
   - **Set aside** — type the dollars to hold back (e.g. `500`) and Save. The
     "In play" figure updates to your balance minus this.
   - **Trading format** — pick one and Save. *This one takes effect the next time
     your bot restarts.*
   - **Telegram alerts** — toggle the routine alerts you want, then **Save alert
     settings**. (You'll always still get safety/halt alerts.)
5. Tap **Sign out** when you're done (optional).

**Forgot your password?** Contact us — we'll reset it for you.

Prefer Telegram? You can also change your risk without the dashboard by messaging
your bot **`/risk 8`** (and `/risk` to check it). See the setup guide.

---

## For the operator — setup

### Automatic (the normal path)

The dashboard is **fully handled by autoprovisioning**. When a paid signup is
provisioned (`onboarding/provisioner.py`), it automatically:

1. Injects a strong, unique **`DASHBOARD_PASSWORD`** into the customer's bot
   (stable — it does not rotate on redeploys or reconciles).
2. Sets **`DASHBOARD_PORT=8080`** and the dashboard override paths on `/data`.
3. **Generates a public Railway domain** for the bot service, targeting port 8080.
4. Sends you the **dashboard URL + password** in the provisioning success alert on
   Telegram (the same alert that reports the bot is live):

   ```
   ✅ FlipPulse bot provisioned
   Customer: Jane Doe (jane-doe)
   ...
   Dashboard: https://jane-doe-bot-production.up.railway.app
     ↳ Password: 8kQ2v7Rf...
     ↳ Send both to the customer (see CUSTOMER_ONBOARDING.md).
   ```

**Your only step:** copy the **Dashboard URL** and **Password** from that alert and
send them to the customer (email/text). That's it.

Nothing extra needs configuring beyond the provisioning you already run — the same
`RAILWAY_API_TOKEN` that creates the project also mints the domain.

### Manual fallback

If the success alert says the domain was **NOT auto-created** (Railway declined, or
you deployed a bot by hand), do it in the Railway UI:

1. Open the customer's bot **service → Settings → Networking → Generate Domain**.
   When asked for a **target port, enter `8080`**.
2. Confirm the service has **`DASHBOARD_PASSWORD`** set (Variables tab). If not, add
   one — any strong value — and redeploy. (For provisioned bots it's already set;
   the password is also printed in the provisioning alert.)
3. Give the generated `https://…up.railway.app` URL and the password to the customer.

### Rotating a password

Set a new **`DASHBOARD_PASSWORD`** in the bot's Railway Variables and redeploy, then
send the customer the new value. (Existing signed-in sessions stay valid until they
expire; a redeploy that changes the signing secret ends them sooner.)

### Notes & security

- The dashboard is **disabled unless `DASHBOARD_PASSWORD` is set** — a bot without it
  simply doesn't serve the page.
- Always serve over **HTTPS**. Railway's generated domain terminates TLS, so the
  auto-provisioned URL is already HTTPS — don't hand out a plain-HTTP address.
- The password is the only gate; keep it strong and unique per customer (the
  provisioner does this for you).
- The dashboard runs as a background thread inside the bot and **never affects
  trading** — if it fails to start, the bot keeps trading normally.
- Every setting the customer changes is **re-validated and re-clamped by the engine**,
  so the dashboard can only ever request a safe change.

Config reference for all the knobs: **[`.env.example`](.env.example)** (the
"Self-service customer dashboard" block).
