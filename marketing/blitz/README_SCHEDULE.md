# Bulk-schedule Weeks 1–4 (Metricool CSV)

`metricool_bulk_weeks1-4.csv` collapses Phases 3–4 of the prep workflow: it's
every **X and Facebook** post for Weeks 1–4 (Jul 6 – Aug 2, 2026), pre-mapped to
the calendar's slots and ready to import into Metricool.

- **112 rows** = 4 weeks × (3 X + 1 FB) per day.
- **67 auto-publish** (`Draft=FALSE`) — fire-and-forget.
- **45 held as drafts** (`Draft=TRUE`) — need a human at the 8am check.

TikTok, Reels, and Stories are **not** here — they need per-platform video
uploads / notification-publish and stay manual (`06_SCHEDULER_SETUP.md` §4–6).

## Import (10 min)

1. Set your Metricool brand timezone to **America/New_York** (times are ET).
2. Upload the CSV media-less: any `[shot]` post attaches its screenshot later.
   Put the file somewhere Metricool can read, or import then attach in Planning.
3. Metricool → **Planning → Bulk upload (CSV)** → upload
   `metricool_bulk_weeks1-4.csv` → map columns
   (`Text, Date, Time, Draft, Network, Media URL, Shortener`) → import.
4. **Planning → Week view**: confirm 3 X + 1 FB per day, no red/failed rows.
5. Paste your `dub.sh` short links into any CTA post before it goes out
   (`06 §9`).

## The `Draft=TRUE` rows (why they can't be forgotten)

Handle these live at the morning check — each is one of:

| Reason | Slots | What you do |
|---|---|---|
| `[shot]` — fresh <48h screenshot | T01/T02/T03/T04/T05/T07/T41/T49/T50, FB02/FB05 | Attach today's Telegram screenshot, then Schedule |
| Thread | TH-PIN, TH01–TH04 | Build the chain with **+ Add tweet** (text in `03 §2/§3.2`) |
| Fill-in blank | T06, T26, T30, T59, FB07, FB11 | Drop in the real number/milestone |
| Poll | T37, FB09 | Create the native poll (API can't schedule it) |
| Link not live yet | T45, T57, FB10 | Add the lead-magnet link once it's live (wk2+) |

## Regenerate / extend to later weeks

`build_schedule_csv.py` parses `03_POST_LIBRARY.md` and emits the CSV, so the
copy always matches the library. To add Weeks 5–13, append their calendar rows
to `SCHEDULE` (same `(date, time, network, asset_id, draft)` shape) and re-run:

```bash
python3 marketing/blitz/build_schedule_csv.py
```
