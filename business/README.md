# FlipPulse — Business Model

**[`FlipPulse_Business_Model.xlsx`](FlipPulse_Business_Model.xlsx)** is a live,
formula-driven operating/budget model. Change the shaded **Inputs** cells and every
output on the other sheets recalculates.

## Sheets

| Sheet | What it does |
|---|---|
| **Inputs** | All editable assumptions — pricing, per-customer costs, fixed costs, Stripe fees, churn, growth ramp, and hardware. Edit the yellow cells. |
| **Monthly Model** | 12-month P&L: customers (start/new/churn/end), revenue (setup + subscription + optional performance fee), costs (Claude, Railway, Stripe, misc), hardware capex, net & cumulative profit. |
| **Summary** | Quarterly + annual rollups, key metrics (ending MRR/ARR, gross margin, cumulative profit), a hardware-affordability check, and the illustrative performance-fee upside. |
| **Cost Notes** | The researched pricing behind the defaults, with sources. |

## Assumptions baked in (all editable)

- **Pricing:** $150 startup + $99/month per customer. Optional 20% performance fee is
  kept **out** of headline totals (toggle `Inputs!B8=1` to include it — see the compliance
  note in the admin guide first).
- **Growth:** slow ramp to **100 customers by month 6** and **500 by month 12** (the
  `Cust. end` column on *Monthly Model* is editable if your curve differs), with 4% monthly
  churn.
- **Costs:** Claude Max $100/mo, Railway $20 base + ~$5/mo per active bot, GitHub $0
  (Free), Stripe 2.9% + $0.30 (+0.7% Billing), misc $30/mo.
- **Hardware (from profits):** top-spec Mac mini ($2,000) + large curved monitor ($1,000)
  + peripherals ($300), purchased in month 5 — the Summary confirms cumulative profit
  covers it first.

## Headline (with the shipped defaults)

| Metric | Year 1 |
|---|---|
| Ending customers | 500 |
| Ending MRR / ARR | ~$49.5K / ~$594K |
| Total revenue (setup + subscription) | ~$272K |
| Total operating costs | ~$21K |
| **Net profit (after hardware)** | **~$247K** |
| Gross margin | ~92% |
| Performance-fee upside (illustrative) | +~$38K |

> Numbers move the moment you change an input. The performance-fee upside assumes an
> average account size and monthly return you set on the Inputs sheet — it is **unproven**;
> treat it as a ceiling, not a forecast.

## Regenerate

```bash
pip install openpyxl
python business/build_model.py
```
