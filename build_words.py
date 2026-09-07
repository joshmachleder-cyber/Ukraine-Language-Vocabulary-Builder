#!/usr/bin/env python3
"""Pull the vocabulary sheet as CSV and write words.json.

Reads SHEET_ID (required) and SHEET_GID (optional) from the environment.
The sheet has to be shared as "anyone with the link can view".
"""

import csv
import hashlib
import io
import json
import os
import sys
import urllib.request

GVIZ = "https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv"

# Column headers this script will accept, in order of preference.
ALIASES = {
    "id":  ["id", "key", "uid"],
    "uk":  ["uk", "ukrainian", "word", "українська", "слово"],
    "en":  ["en", "english", "translation", "meaning", "definition"],
    "pos": ["pos", "part of speech", "part_of_speech", "type"],
    "note": ["note", "notes", "example", "comment"],
}


def pick(headers, names):
    lowered = {h.strip().lower(): h for h in headers if h}
    for n in names:
        if n in lowered:
            return lowered[n]
    return None


def stable_id(uk, en):
    return hashlib.sha1((uk + "|" + en).encode("utf-8")).hexdigest()[:10]


def main():
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id:
        sys.exit("SHEET_ID is not set")

    url = GVIZ.format(sid=sheet_id)
    gid = os.environ.get("SHEET_GID", "").strip()
    if gid:
        url += "&gid=" + gid

    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    cols = {k: pick(headers, v) for k, v in ALIASES.items()}

    if not cols["uk"] or not cols["en"]:
        sys.exit(
            "Could not find a Ukrainian column and an English column.\n"
            "Headers found: %s" % ", ".join(h for h in headers if h)
        )

    words, seen = [], set()
    for row in reader:
        uk = (row.get(cols["uk"]) or "").strip()
        en = (row.get(cols["en"]) or "").strip()
        if not uk or not en:
            continue

        wid = (row.get(cols["id"]) or "").strip() if cols["id"] else ""
        if not wid:
            wid = stable_id(uk, en)
        if wid in seen:
            continue
        seen.add(wid)

        word = {"id": wid, "uk": uk, "en": en}
        for extra in ("pos", "note"):
            if cols[extra]:
                val = (row.get(cols[extra]) or "").strip()
                if val:
                    word[extra] = val
        words.append(word)

    if not words:
        sys.exit("The sheet parsed but produced no usable rows")

    out = {"count": len(words), "words": words}
    with open("words.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("Wrote words.json with %d words" % len(words))


if __name__ == "__main__":
    main()
