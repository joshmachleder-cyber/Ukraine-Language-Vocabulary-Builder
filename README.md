# Ukrainian words

A 20-question drill built from a Google Sheet. Ukrainian word on top, four English
options below. Runs as a static page on GitHub Pages, installs to a phone home
screen, works offline, keeps review history in the browser.

## What the sheet needs

One row per word. Headers are matched case-insensitively, and any of these work:

| Field | Accepted headers | Required |
|---|---|---|
| Ukrainian | `uk`, `ukrainian`, `word`, `слово` | yes |
| English | `en`, `english`, `translation`, `meaning` | yes |
| Part of speech | `pos`, `part of speech`, `type` | no, but see below |
| Note | `note`, `notes`, `example` | no |
| Stable key | `id`, `key`, `uid` | no |

Add the part of speech column if you can. The app draws the three wrong answers
from the same part of speech first, which is what keeps the question from
answering itself. Without it, distractors come from anywhere in the sheet and the
drill gets easier than it should be.

The `note` column, if present, shows up under the answer as feedback. Good place
for a case, an aspect pair, or a short example.

If you leave out `id`, the app derives one by hashing the Ukrainian and English
together. That is stable across reordering rows, but editing either word creates a
new key and resets that word's history. Adding a real `id` column avoids this.

Sharing: set the sheet to "anyone with the link can view."

## Setup

1. Push this repo to GitHub.
2. Settings > Pages, deploy from `main`, root folder.
3. Settings > Secrets and variables > Actions, add a secret `SHEET_ID` with the
   long id from your sheet URL. Add `SHEET_GID` too if the words are not on the
   first tab.
4. Actions tab, run "Refresh word list" once by hand to confirm it parses your
   columns. It commits `words.json` only when something changed.
5. Open the Pages URL on your phone and add it to the home screen.

`words.json` currently holds twenty sample words so the app runs before you wire
up the sheet. The first successful refresh overwrites it.

## The Saturday refresh

The workflow runs `0 12 * * 6`, which is Saturday at noon UTC. Four things to know:

- Scheduled runs are best effort. Delays of ten to thirty minutes are normal and a
  run can be skipped entirely under load.
- The workflow file has to be on the default branch or the schedule never fires.
- In a public repository, scheduled workflows are automatically disabled after 60
  days with no repository activity. You get a warning email, then silence.
  See https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-a-workflow
- `workflow_dispatch` is enabled, so you can always run it by hand.

The job refreshes the word list only. It does not pre-build sessions. The 20
questions get chosen when you open the app, so they reflect what you missed on
Wednesday rather than what was true on Saturday.

## How the 20 get chosen

Priority order: words that are due for review, oldest due first, then words you
have never seen, then whatever you have seen least recently to top up a short
list. The end screen tells you how many are still due so you can decide whether
to run a second round.

## Scheduling

Intervals live in the `LADDER` array in `index.html`: 1, 3, 7, 16, 35, 75, 150
days, advancing on each correct answer in a row. A miss resets the streak and
brings the word back in ten minutes.

This is deliberately simple. If you want a real scheduler later, swap the
`record` function for `ts-fsrs`, which runs in the browser:
https://github.com/open-spaced-repetition/ts-fsrs

## Keyboard

`1` through `4` to answer, `Enter` or space to advance.

## Where progress lives

`localStorage`, per device and per browser. Clearing site data wipes it, and your
phone and laptop keep separate histories. Syncing would need a backend, which this
deliberately does not have.
