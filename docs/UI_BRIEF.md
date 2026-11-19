# Brief for a UI translation agent

You translate the menu and system strings of one or more source files (named in your task, e.g. `O020`) of the PlayStation game Bounty Sword: Double Edge from Japanese to English. Work only on those files.

Python: Python 3.11+ (called `PY` below). Run commands from `E:\Projects\Bounty Sword 2`. Read JSON with the Read tool (it contains Japanese; the console may garble it).

## Read first

1. `BASE_RULES.md`, section "When translating any kind of text" (binding).
2. `work/glossary/terms.json` (names, places, terms, and menu terms of type `menu`) and `work/glossary/speakers.json`. Use these spellings. Item, skill, menu and Void-part names that already appear in the translated script (for example in `work/translation/en/drafts/K004.py` rows 182-217 for skills, `K038.py` for Void parts, `K017.py` for items) must be spelled the same way; grep the drafts for the Japanese term's English when in doubt.

## Your input

`work/translation/en/ui/<FILE>.json`: one row per line of text:

    {"id": "O020_0267e4", "slots": 4, "jp": "キャンプ", "kind": "item_name" (EXE only), "en": ""}

* `slots` = how many 16-bit cells the line has. English is stored two letters per cell, so a row holds at most `2 * slots` letters (spaces and punctuation count). Shorter is fine; the rest is blank.
* Rows come in file order; neighbouring rows usually belong to the same menu or record, so read them together.
* EXE rows: the item database. `item_name` rows (9 cells: up to 18 letters) are the names shown in item and equipment lists; `item_help` rows (16 cells: up to 32 letters) are the one-line help text shown for the item. Names like 予備剣４ / 予備... ("spare ...") are unused placeholders: translate them plainly ("Spare Sword 4").
* Some rows are not text at all: program data or tables that happen to decode as characters (runs of random symbols and kanji with no sense, long runs of the alphabet in order, repeated patterns). Mark them with `"-"` and they will never be written. When unsure whether a row is real text, mark it `"-"` and list it in your report: writing over data crashes the game.

## Your output

`work/translation/en/ui_drafts/<FILE>.py`:

    EN = {
    'O020_0267e4': 'Camp',
    'O020_000e64': '-',
    }

Rules:

* One row in, one row out: never move text between rows; each row is a separate field on screen.
* Allowed characters ONLY: A-Z a-z 0-9 space and `! ? : ( ) / & % + - = ~ , . ' " ;`. No accented letters, no curly quotes, no ellipsis character (write `...`), no `*` or `#`.
* Keep it short and clear; menus should read like a polished English game menu (Camp, Search, Info, Save, Load, Equip, Items, Buy, Sell, Exit, Yes, No). Abbreviate when needed (HP, SP, AT, DF, MG, DX, MS, AS stay as they are; "Lv", "Atk", "Def", "Spd" are fine).
* Fixed full-width spacing in the source (`探 索`) is only layout: write the word normally ("Search").
* Digits are stored one per cell (never paired: in some tables a digit is a number the game fills in at run time), so each digit costs a whole cell. Keep numbers that are part of the text. Keep the meaning of every help line; compress wording, never drop a fact (an item's effect, a target, a restriction).
* Lines that belong to one sentence split over several rows: cut the English at the matching point.
* Dialogue-like rows (shopkeepers, messages with 「」): use straight double quotes `"` where the source has corner brackets; keep the speaker's voice.
* Do not soften anything.

## Check and apply

    PY tools/ui_insert.py apply <FILE> --dry

Fix every `TOO LONG` / `NO GLYPH` / `NO SUCH ROW` and run again until `problems 0` and `still empty 0`. Then:

    PY tools/ui_insert.py apply <FILE>

It must print `applied`. Work in slices of about 80 rows (keep adding to the same draft file).

Do NOT run any other tool that writes, do not edit the JSON by hand, the glossary, or other files' drafts. Do not start emulators. Do not spawn sub-agents.

## Report (your final message)

At most 15 lines: rows translated / marked "-" per file; every row you marked "-" while unsure (id + why); names or terms you had to coin that are not in the glossary (`Japanese -> English`); anything a reviewer must re-check.
