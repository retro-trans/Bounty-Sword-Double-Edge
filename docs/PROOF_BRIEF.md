# Brief for a proofreading agent (review stage 3)

You proofread the English of the scenes named in your task (PlayStation game Bounty Sword: Double
Edge). The text has already passed accuracy review and an editorial pass. Your job is the final
proofreading only.

Python: Python 3.11+ (called `PY`). Run
commands from `E:\Projects\Bounty Sword 2`.

## Read first

* `BASE_RULES.md`, section "When proofreading" (binding).
* `docs/REVIEW_BRIEF.md`, section "Settled conventions" (do not undo any of them).
* `docs/AGENT_BRIEF.md`, section "Rules for the text" (quotes, `{n}`, tags, allowed characters).
* `work/glossary/terms.json`, `work/glossary/speakers.json`: approved spellings.

## What to fix

Spelling, grammar, punctuation, typos, accidental duplication or missing words, capitalisation,
formatting (a dialogue row opens and closes with `"` unless the source row is cut off; after `{n}`
in dialogue one space; narration has no quotes and no indent), glossary spellings, damaged tags.

Do NOT fix on purpose: drawn-out vowels ("riiight", "Mr. {hero:6}"), stutters, fragments, cut-off
lines, interjections, character speech patterns (Fortune Granny's "ye", Ange's broken register,
the NEXT dolls' flat speech), six-dot silences, profanity. Do not restyle or reword a line that is
correct. If you think a line's meaning or voice is wrong, do not change it: list it in your report.

## Input, editing, applying

    PY tools/slice_view.py K041      -> work/source/dump/view_K041.txt (Japanese => English, for context)

Edit only `work/translation/en/drafts/<scene>.py` (`EN = {row index: text}`) with the Edit tool.
Then `PY tools/apply_draft.py <scene> --dry` until `problems 0`, then `PY tools/apply_draft.py <scene>`
(must print `applied`). Only scenes that you changed need applying. Do NOT run any other tool that
writes; do not edit scene JSON, glossary files or other scenes' drafts; no emulators; no sub-agents.

## Report (your final message)

At most 12 lines: scenes done, rows edited; a few typical fixes; rows you flagged for meaning or
voice (row id + few words). No Japanese in the report.
