# RAIM: Regime-Adaptive, Inventory-Aware Market Making

**Status: Gate 1 (Requirements), awaiting approval.** This folder contains **no trading code**: no simulator and no strategy. It does not place orders, and nothing here implies profitability.

| Path | Contents |
|---|---|
| `docs/01_REQUIREMENTS.md` | Requirements spec, Gate 0 rule, unknowns register, decisions requested |
| `docs/PARAMETER_REGISTRY.md` | Living parameter registry. Every entry is currently a PRIOR or UNSET. |
| `research/spread_probe.py` | One-off public top-of-book spread probe (stdlib only, no keys) |
| `research/evidence/` | Dated outputs of research runs |

RAIM is independent of FlipPulse and must not import from it.
