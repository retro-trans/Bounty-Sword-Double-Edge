# Contributing

Start with [docs/TRANSLATING.md](docs/TRANSLATING.md) — it covers the
extract/draft/apply loop and the limits the tools enforce.

## What is most useful

1. **Playtesting.** The script has been read through end to end, but most of
   the game has not been played in English. Menus, battles, shops and the
   second scenario are where layout problems hide.
2. **Proofreading.** No fluent human has read the script against the
   Japanese yet. Wrong-but-well-formed lines are what is left.
3. **Screenshots of anything Japanese.** UI strings are found by scanning the
   executable and overlays; anything the scan missed only shows up on screen.

## House rules

**Verify against the image, not against a tool's report.** Boot the built
disc fresh and look at the screen.

**Run the checks before every build:** `python tools/check_all.py` and
`python tools/ui_insert.py check`.

**Do not commit** disc images, extracted game files, screenshots, savestates,
the original Japanese script, or third-party binaries. Run
`python tools/strip_jp.py` and commit only the `*.en.json` copies.
`.gitignore` covers the obvious cases.

## Reporting a bug in the translation

A screenshot is worth more than a description. Say where in the game it was
and, if you can, attach a memory-card save from just before it.
