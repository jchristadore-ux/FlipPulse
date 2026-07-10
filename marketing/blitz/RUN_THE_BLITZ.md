# Run the Blitz — the daily execution spreadsheet

**[`Run_the_Blitz.xlsx`](Run_the_Blitz.xlsx)** is the one document you open each
morning to run the 90-day blitz without hunting through this folder. Instead of
navigating files full of assets, you open one workbook, go to this week's tab,
and work the rows top to bottom.

## What's inside

- **`▶ Start Here` tab** — the Founders 100 Club offer, the legend (Status /
  Priority / posting clock), an editable "your links" table (fill in
  `go.flippulse.com`, `t.me/flippulse`, the lead-magnet URL, etc. once), and a
  clickable-style week index.
- **`Week 01` … `Week 13` tabs** — one execution checklist per campaign week.
  Each row is a scheduled task, in clock order (8:15 X-am → 7:30 X-pm), with:

  | Column | What it holds |
  |---|---|
  | Date | The calendar date (rows are grouped by day with a divider band) |
  | Platform | Channel + post time (X, IG Story/Reel, Facebook, TikTok) |
  | Deliverable | The asset ID(s) for the slot (e.g. `T14`, `TH02 (thread)`, `V10`) |
  | Caption | The **full post text** for X/FB, or a film/build pointer for video/carousel |
  | Image prompt | Screenshot / carousel / thumbnail / Founders-card pointer (into `05`) |
  | Video prompt | Film + export instructions for TikTok/Reel slots (into `04`) |
  | CTA | The call-to-action for that post (Founders / proof / capture / story) |
  | Status | Dropdown: ☐ To do · ▶ In progress · ✅ Done · ⏭ Skipped |
  | Priority | ★ High (Founders / pinned / viral) · Med · Normal |
  | Notes | Flags: PIN, fresh screenshot, thread, poll, rerun, Reddit, BATCH, freeze |

  Each week tab also carries the **standing daily checklist** (from
  `08_DAILY_OPERATING_PROCEDURE.md`) and, during the launch phase, the
  **Founders 100 Club** banner + a ★ High "post the Club + update the seat
  count" task at the top of every day from **Day 2 (Jul 14)** onward.

## Founders 100 Club & the freeze

- The Founders 100 Club is threaded in from **Day 2 (Jul 14)** — early and often,
  until the 100 seats fill. Update the live `[N]/100 seats left` count as you go,
  and stop advertising it the day the cap fills (`11_COMPLIANCE_KIT.md` §7).
- **Week 1 and Day 1 (Jul 13) are COMPLETE / frozen** — their rows are marked
  ✅ and greyed for reference only. Do not modify them.

## Regenerate

The workbook is generated from the live campaign, so it never drifts from the
calendar or the copy:

```bash
pip install openpyxl          # one-time (also in requirements-dev.txt)
python3 marketing/blitz/build_run_the_blitz.py
```

It reads `02_CONTENT_CALENDAR_90D.md` (what goes where), `03_POST_LIBRARY.md`
(the caption text + Founders `FL-*` assets), and `04_VIDEO_SCRIPTS.md` (video
titles + the TikTok/Reels idea banks). Edit the source files, re-run, and the
spreadsheet updates. When the 100th seat sells, remove the Founders daily task
by setting the launch-phase window in the builder (or just stop actioning those
rows) and re-run.
