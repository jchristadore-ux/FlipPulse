#!/usr/bin/env python3
"""Generate a Metricool bulk-upload CSV from the post library + content calendar.

Reads 03_POST_LIBRARY.md, extracts every single-line X (T##) and Facebook (FB##)
asset, and writes a Metricool-ready CSV for Weeks 1-4 of the 90-day blitz.

Columns match Metricool's bulk importer (06_SCHEDULER_SETUP.md §5):
    Text, Date, Time, Draft, Network, Media URL, Shortener

Draft convention (this is the whole "schedule and forget" trick):
    Draft = FALSE  -> Metricool auto-publishes it. Fire-and-forget.
    Draft = TRUE   -> held as a DRAFT for you to finish at the 8am check, because
                      the slot needs something a scheduler can't supply:
                        * a fresh <48h screenshot   (calendar [shot] slots)
                        * a fill-in number/milestone ([n], [milestone], ...)
                        * an X thread (add tweets 2..N via + Add tweet)
                        * an X/FB poll (native polls can't be API-scheduled)
                        * a link that isn't live yet (lead magnet, wk2+)

Threads, TikTok, Reels and Stories are intentionally NOT in this CSV — they are
manual by platform rule or by strategy (see 06 §4-6). Thread slots appear as a
DRAFT stub pointing you at the library.

Regenerate for later weeks by extending SCHEDULE with the calendar rows.
"""

import csv
import re
from pathlib import Path

HERE = Path(__file__).parent
LIBRARY = HERE / "03_POST_LIBRARY.md"
OUT = HERE / "metricool_bulk_weeks1-4.csv"

# --- 1. Parse single-line assets (T## and FB##) out of the library ----------
# Library lines look like:   - `T01` `...post text with \n for newlines...`
# Some lines carry a parenthetical marker after the id, e.g. `- `FB01` (pin) `...``
ASSET_RE = re.compile(r"^- `((?:T|FB)\d+)`(?: \([^)]*\))? `(.*)`\s*$")


def load_assets() -> dict[str, str]:
    assets: dict[str, str] = {}
    for line in LIBRARY.read_text(encoding="utf-8").splitlines():
        m = ASSET_RE.match(line)
        if m:
            asset_id, text = m.group(1), m.group(2)
            # The library stores newlines as the two literal chars: backslash + n
            assets[asset_id] = text.replace("\\n", "\n")
    return assets


# Thread slots become a draft stub (build the chain by hand with + Add tweet).
THREAD_STUB = (
    "⚠️ THREAD ({tid}) — DRAFT. Build the tweet chain manually in Metricool "
    "(+ Add tweet for each numbered tweet). Full text in 03_POST_LIBRARY.md §2/§3.2."
)

# --- 2. The Weeks 1-4 schedule, straight from 02_CONTENT_CALENDAR_90D.md -----
# (date, HH:MM, network, asset_id, draft)
#   times ET: X am 08:15 / X mid 12:30 / X pm 19:30 / FB 13:00
#   draft=True whenever the slot needs a human (see module docstring).
T, F = True, False
SCHEDULE = [
    # ---- WEEK 1 (Jul 6-12) ----
    ("2026-07-06", "08:15", "twitter",  "TH-PIN", T),
    ("2026-07-06", "12:30", "twitter",  "T09",    F),
    ("2026-07-06", "19:30", "twitter",  "T41",    T),  # [shot]
    ("2026-07-06", "13:00", "facebook", "FB01",   F),  # pin
    ("2026-07-07", "08:15", "twitter",  "T11",    F),
    ("2026-07-07", "12:30", "twitter",  "TH01",   T),  # thread
    ("2026-07-07", "19:30", "twitter",  "T05",    T),  # [shot]
    ("2026-07-07", "13:00", "facebook", "FB04",   F),
    ("2026-07-08", "08:15", "twitter",  "T01",    T),  # [shot]
    ("2026-07-08", "12:30", "twitter",  "T36",    F),
    ("2026-07-08", "19:30", "twitter",  "T04",    T),  # [shot]
    ("2026-07-08", "13:00", "facebook", "FB02",   T),  # [shot]
    ("2026-07-09", "08:15", "twitter",  "T15",    F),
    ("2026-07-09", "12:30", "twitter",  "T21",    F),
    ("2026-07-09", "19:30", "twitter",  "T08",    F),
    ("2026-07-09", "13:00", "facebook", "FB12",   F),
    ("2026-07-10", "08:15", "twitter",  "T26",    T),  # fill-in [milestone]
    ("2026-07-10", "12:30", "twitter",  "T37",    T),  # poll
    ("2026-07-10", "19:30", "twitter",  "T02",    T),  # [shot]
    ("2026-07-10", "13:00", "facebook", "FB07",   T),  # fill-in
    ("2026-07-11", "08:15", "twitter",  "T19",    F),
    ("2026-07-11", "12:30", "twitter",  "T25",    F),
    ("2026-07-11", "19:30", "twitter",  "T51",    F),
    ("2026-07-11", "13:00", "facebook", "FB09",   T),  # poll
    ("2026-07-12", "08:15", "twitter",  "T12",    F),
    ("2026-07-12", "12:30", "twitter",  "T33",    F),
    ("2026-07-12", "19:30", "twitter",  "T60",    F),
    ("2026-07-12", "13:00", "facebook", "FB10",   T),  # lead-magnet link not live yet
    # ---- WEEK 2 (Jul 13-19) ----
    ("2026-07-13", "08:15", "twitter",  "T29",    F),
    ("2026-07-13", "12:30", "twitter",  "T38",    F),
    ("2026-07-13", "19:30", "twitter",  "T07",    T),  # [shot]
    ("2026-07-13", "13:00", "facebook", "FB05",   T),  # [shot]
    ("2026-07-14", "08:15", "twitter",  "T14",    F),
    ("2026-07-14", "12:30", "twitter",  "TH02",   T),  # thread + [shot]
    ("2026-07-14", "19:30", "twitter",  "T17",    F),
    ("2026-07-14", "13:00", "facebook", "FB03",   F),
    ("2026-07-15", "08:15", "twitter",  "T06",    T),  # fill-in + [shot]
    ("2026-07-15", "12:30", "twitter",  "T39",    F),
    ("2026-07-15", "19:30", "twitter",  "T03",    T),  # [shot]
    ("2026-07-15", "13:00", "facebook", "FB08",   F),
    ("2026-07-16", "08:15", "twitter",  "T10",    F),
    ("2026-07-16", "12:30", "twitter",  "T23",    F),
    ("2026-07-16", "19:30", "twitter",  "T56",    F),
    ("2026-07-16", "13:00", "facebook", "FB15",   F),
    ("2026-07-17", "08:15", "twitter",  "T27",    F),
    ("2026-07-17", "12:30", "twitter",  "T40",    F),
    ("2026-07-17", "19:30", "twitter",  "T49",    T),  # [shot]
    ("2026-07-17", "13:00", "facebook", "FB07",   T),  # fill-in (wk2)
    ("2026-07-18", "08:15", "twitter",  "T20",    F),
    ("2026-07-18", "12:30", "twitter",  "T24",    F),
    ("2026-07-18", "19:30", "twitter",  "T53",    F),
    ("2026-07-18", "13:00", "facebook", "FB06",   F),
    ("2026-07-19", "08:15", "twitter",  "T13",    F),
    ("2026-07-19", "12:30", "twitter",  "T31",    F),
    ("2026-07-19", "19:30", "twitter",  "T58",    F),
    ("2026-07-19", "13:00", "facebook", "FB13",   F),
    # ---- WEEK 3 (Jul 20-26) ----
    ("2026-07-20", "08:15", "twitter",  "T30",    T),  # milestone [n]
    ("2026-07-20", "12:30", "twitter",  "T36",    T),  # rerun-style fresh QT
    ("2026-07-20", "19:30", "twitter",  "T45",    T),  # lead-magnet link
    ("2026-07-20", "13:00", "facebook", "FB11",   T),  # milestone [n]
    ("2026-07-21", "08:15", "twitter",  "T18",    F),
    ("2026-07-21", "12:30", "twitter",  "TH03",   T),  # mega-thread
    ("2026-07-21", "19:30", "twitter",  "T57",    T),  # lead-magnet link
    ("2026-07-21", "13:00", "facebook", "FB04",   F),  # rerun w/ new angle
    ("2026-07-22", "08:15", "twitter",  "T02",    T),  # [shot]
    ("2026-07-22", "12:30", "twitter",  "T37",    T),  # poll
    ("2026-07-22", "19:30", "twitter",  "T04",    T),  # [shot]
    ("2026-07-22", "13:00", "facebook", "FB02",   T),  # [shot]
    ("2026-07-23", "08:15", "twitter",  "T22",    F),
    ("2026-07-23", "12:30", "twitter",  "T25",    F),
    ("2026-07-23", "19:30", "twitter",  "T15",    F),
    ("2026-07-23", "13:00", "facebook", "FB12",   F),
    ("2026-07-24", "08:15", "twitter",  "T26",    T),  # fill-in (wk3)
    ("2026-07-24", "12:30", "twitter",  "T59",    T),  # real question
    ("2026-07-24", "19:30", "twitter",  "T50",    T),  # [shot]
    ("2026-07-24", "13:00", "facebook", "FB07",   T),  # fill-in
    ("2026-07-25", "08:15", "twitter",  "T52",    F),
    ("2026-07-25", "12:30", "twitter",  "T21",    F),
    ("2026-07-25", "19:30", "twitter",  "T54",    F),
    ("2026-07-25", "13:00", "facebook", "FB06",   F),
    ("2026-07-26", "08:15", "twitter",  "T35",    F),
    ("2026-07-26", "12:30", "twitter",  "T43",    F),
    ("2026-07-26", "19:30", "twitter",  "T60",    F),
    ("2026-07-26", "13:00", "facebook", "FB10",   T),  # lead-magnet link
    # ---- WEEK 4 (Jul 27-Aug 2) ----
    ("2026-07-27", "08:15", "twitter",  "T28",    F),
    ("2026-07-27", "12:30", "twitter",  "T38",    F),
    ("2026-07-27", "19:30", "twitter",  "T42",    F),
    ("2026-07-27", "13:00", "facebook", "FB13",   F),
    ("2026-07-28", "08:15", "twitter",  "T16",    F),
    ("2026-07-28", "12:30", "twitter",  "TH04",   T),  # thread
    ("2026-07-28", "19:30", "twitter",  "T43",    F),
    ("2026-07-28", "13:00", "facebook", "FB03",   F),
    ("2026-07-29", "08:15", "twitter",  "T06",    T),  # fill-in + [shot]
    ("2026-07-29", "12:30", "twitter",  "T39",    F),
    ("2026-07-29", "19:30", "twitter",  "T03",    T),  # [shot]
    ("2026-07-29", "13:00", "facebook", "FB05",   T),  # [shot]
    ("2026-07-30", "08:15", "twitter",  "T08",    F),
    ("2026-07-30", "12:30", "twitter",  "T24",    F),
    ("2026-07-30", "19:30", "twitter",  "T56",    F),
    ("2026-07-30", "13:00", "facebook", "FB15",   F),
    ("2026-07-31", "08:15", "twitter",  "T26",    T),  # fill-in (wk4)
    ("2026-07-31", "12:30", "twitter",  "T37",    T),  # poll
    ("2026-07-31", "19:30", "twitter",  "T49",    T),  # [shot] / news-override T46/T47
    ("2026-07-31", "13:00", "facebook", "FB07",   T),  # fill-in
    ("2026-08-01", "08:15", "twitter",  "T19",    F),
    ("2026-08-01", "12:30", "twitter",  "T44",    F),
    ("2026-08-01", "19:30", "twitter",  "T51",    F),
    ("2026-08-01", "13:00", "facebook", "FB09",   T),  # poll
    ("2026-08-02", "08:15", "twitter",  "T12",    F),
    ("2026-08-02", "12:30", "twitter",  "T33",    F),
    ("2026-08-02", "19:30", "twitter",  "T53",    F),
    ("2026-08-02", "13:00", "facebook", "FB10",   T),  # lead-magnet link
]


def main() -> None:
    assets = load_assets()
    rows = []
    missing = []
    for date, time, network, asset_id, draft in SCHEDULE:
        if asset_id.startswith("TH"):
            text = THREAD_STUB.format(tid=asset_id)
        elif asset_id in assets:
            text = assets[asset_id]
        else:
            missing.append(asset_id)
            continue
        rows.append(
            {
                "Text": text,
                "Date": date,
                "Time": time,
                "Draft": "TRUE" if draft else "FALSE",
                "Network": network,
                "Media URL": "",
                "Shortener": "FALSE",
            }
        )

    if missing:
        raise SystemExit(f"Assets not found in library: {sorted(set(missing))}")

    fields = ["Text", "Date", "Time", "Draft", "Network", "Media URL", "Shortener"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    auto = sum(1 for r in rows if r["Draft"] == "FALSE")
    drafts = sum(1 for r in rows if r["Draft"] == "TRUE")
    print(f"Wrote {len(rows)} rows -> {OUT.name}")
    print(f"  auto-publish (Draft=FALSE): {auto}")
    print(f"  needs-you   (Draft=TRUE):  {drafts}")


if __name__ == "__main__":
    main()
