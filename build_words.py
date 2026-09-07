#!/usr/bin/env python3
"""Pull the vocabulary sheet as CSV and write words.json.

Reads column B (Ukrainian) and column C (English). Everything else on the
worksheet is ignored. The sheet has no header row, so every row is treated as
data.

Reads SHEET_ID (required) and SHEET_GID (optional) from the environment.
The sheet has to be shared as "anyone with the link can view".
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

# Which columns to pull, in Google's query language. Column B first, then C.
# If you later add a part of speech column in D, change this to "select B, C, D"
# and set POS_INDEX to 2 below.
QUERY = "select B, C"
POS_INDEX = None

# Column B has to contain at least one Cyrillic letter to count as a word.
# This is what filters out blank rows, section labels, and notes to yourself.
CYRILLIC = re.compile(r"[\u0400-\u04FF]")


def stable_id(uk, en):
    return hashlib.sha1((uk + "|" + en).encode("utf-8")).hexdigest()[:10]


def main():
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id:
        sys.exit("SHEET_ID is not set")

    params = {"tqx": "out:csv", "headers": "0", "tq": QUERY}
    gid = os.environ.get("SHEET_GID", "").strip()
    if gid:
        params["gid"] = gid

    url = "https://docs.google.com/spreadsheets/d/%s/gviz/tq?%s" % (
        sheet_id,
        urllib.parse.urlencode(params),
    )

    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8")

    words, seen = [], set()
    skipped = 0

    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2:
            skipped += 1
            continue

        uk = row[0].strip()
        en = row[1].strip()

        if not uk or not en or not CYRILLIC.search(uk):
            skipped += 1
            continue

        wid = stable_id(uk, en)
        if wid in seen:
            skipped += 1
            continue
        seen.add(wid)

        word = {"id": wid, "uk": uk, "en": en}
        if POS_INDEX is not None and len(row) > POS_INDEX:
            pos = row[POS_INDEX].strip()
            if pos:
                word["pos"] = pos
        words.append(word)

    if not words:
        sys.exit(
            "The sheet downloaded but no rows had Ukrainian in column B and "
            "English in column C. First 300 characters of what came back:\n"
            + text[:300]
        )

    with open("words.json", "w", encoding="utf-8") as f:
        json.dump({"count": len(words), "words": words}, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("Wrote words.json with %d words (%d rows skipped)" % (len(words), skipped))
    print("First entry: %s = %s" % (words[0]["uk"], words[0]["en"]))
    print("Last entry:  %s = %s" % (words[-1]["uk"], words[-1]["en"]))


if __name__ == "__main__":
    main()
