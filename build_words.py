#!/usr/bin/env python3
"""
Build words.json from the Google Sheet, and report everything it discarded.

Changes from the previous version:
  - reads columns A through E instead of B and C, and finds the Ukrainian in
    whichever cell actually has Cyrillic in it
  - skips spreadsheet error values (#VALUE!, #N/A, #REF!, #ERROR!)
  - strips English that got glued onto the end of the Ukrainian cell
    ("вік age" -> "вік", "Востаннє --- last" -> "Востаннє")
  - de-duplicates on the normalised Ukrainian rather than on an exact
    Ukrainian+English match, so near-duplicate rows collapse too
  - writes dropped.csv listing every row that did not make it, with a reason
"""

import csv
import hashlib
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

SHEET_ID = os.environ.get("SHEET_ID", "")
SHEET_GID = os.environ.get("SHEET_GID", "")

CYRILLIC = re.compile(r"[\u0400-\u04FF]")
LATIN = re.compile(r"[A-Za-z]")
ERRORS = ("#VALUE!", "#N/A", "#REF!", "#ERROR!", "#NAME?", "#DIV/0!")

# Letter pairs that are almost never right in Ukrainian and usually mean the
# word was typed on the wrong layout. These rows are kept but flagged.
SUSPECT = re.compile(r"цг|иа|иу|иі|сг|тсі")


def fetch_rows():
    """Pull the sheet as CSV via the gviz endpoint. Columns A through E."""
    if not SHEET_ID:
        sys.exit("SHEET_ID is not set")
    query = urllib.parse.quote("select A, B, C, D, E")
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&headers=0&tq={query}"
    )
    if SHEET_GID:
        url += f"&gid={SHEET_GID}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.reader(io.StringIO(text)))


def cell(row, i):
    return row[i].strip() if len(row) > i else ""


def find_ukrainian(row):
    """Prefer column B. Fall back to any other cell that has Cyrillic in it."""
    b = cell(row, 1)
    if CYRILLIC.search(b):
        return b, "B"
    for i in (0, 2, 3, 4):
        v = cell(row, i)
        if CYRILLIC.search(v):
            return v, chr(ord("A") + i)
    return "", ""


def strip_glued_english(uk):
    """
    Remove English that was pasted onto the end of the Ukrainian cell.
    Everything from the first run of Latin letters onward goes, along with any
    dash or punctuation left dangling.
    """
    m = LATIN.search(uk)
    if not m:
        return uk, False
    head, tail = uk[: m.start()], uk[m.start():]
    # Only strip when the Latin run is genuinely trailing English. A stray
    # Latin letter inside a word (мені цьоgо досит) has Cyrillic after it,
    # so leave that alone and let the flag catch it instead.
    if CYRILLIC.search(tail) or not CYRILLIC.search(head):
        return uk, False
    if len(head.strip(" -–—.,;:")) < 2:
        return uk, False
    return head.strip(" -–—.,;:"), True


def normalise(uk):
    s = uk.lower().replace("\u02bc", "'").replace("\u2019", "'")
    s = re.sub(r"[^\u0400-\u04FF' ]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def tidy_english(en):
    """Collapse 'interview interview' and 'peers peer' style doubling."""
    parts = en.split()
    if len(parts) == 2 and parts[0].lower().startswith(parts[1].lower()[:4]):
        return parts[0]
    return en


def better(a, b):
    """Given two candidate English glosses for the same word, keep the better."""
    if len(a) != len(b):
        return a if len(a) < len(b) else b
    return a


def main():
    rows = fetch_rows()
    kept = {}
    dropped = []
    flagged = []

    for n, row in enumerate(rows, start=1):
        if not any(c.strip() for c in row):
            continue

        uk, col = find_ukrainian(row)
        en = cell(row, 2)

        if not uk:
            dropped.append((n, cell(row, 1), en, "no Ukrainian in any column"))
            continue
        if not en:
            dropped.append((n, uk, "", "no English translation"))
            continue
        if any(e in en for e in ERRORS) or any(e in uk for e in ERRORS):
            dropped.append((n, uk, en, "spreadsheet error value"))
            continue
        if uk.lower() == "ukrainian" and en.lower() == "english":
            dropped.append((n, uk, en, "header row"))
            continue

        uk, stripped = strip_glued_english(uk)
        en = tidy_english(en)

        if stripped:
            flagged.append((n, uk, en, "English was glued onto the Ukrainian cell"))
        if SUSPECT.search(uk.lower()):
            flagged.append((n, uk, en, "looks mistyped, check spelling"))
        if LATIN.search(uk):
            flagged.append((n, uk, en, "Latin letter inside the Ukrainian word"))

        key = normalise(uk)
        if not key:
            dropped.append((n, uk, en, "nothing left after cleanup"))
            continue

        if key in kept:
            prev = kept[key]
            prev["en"] = better(prev["en"], en)
            dropped.append((n, uk, en, f"duplicate of row {prev['row']}"))
        else:
            kept[key] = {"row": n, "uk": uk, "en": en, "col": col}

    words = []
    for key, v in sorted(kept.items()):
        wid = hashlib.sha1((v["uk"] + "|" + v["en"]).encode("utf-8")).hexdigest()[:10]
        words.append({"id": wid, "uk": v["uk"], "en": v["en"]})

    with open("words.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(words), "words": words}, f,
                  ensure_ascii=False, indent=1)

    with open("dropped.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sheet_row", "ukrainian", "english", "reason"])
        for r in dropped:
            w.writerow(r)

    with open("flagged.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sheet_row", "ukrainian", "english", "issue"])
        for r in flagged:
            w.writerow(r)

    print(f"rows read:   {len(rows)}")
    print(f"words kept:  {len(words)}")
    print(f"rows dropped:{len(dropped)}  (see dropped.csv)")
    print(f"rows flagged:{len(flagged)}  (see flagged.csv, kept but worth fixing)")


if __name__ == "__main__":
    main()
