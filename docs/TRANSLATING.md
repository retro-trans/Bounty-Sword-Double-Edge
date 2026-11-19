# Translating Bounty Sword: Double Edge

Rules: `BASE_RULES.md`. Glossary: `work/glossary/speakers.json` (speaker id -> name), `work/glossary/terms.json`.
Script format: `docs/text_formats.md`. Insertion: `docs/VWF.md`.

## Working files

`python tools/extract_scenes.py` -> `work/translation/en/scenes/K###.json` (first scenario, KIVE.BIN) and `S###.json` (second scenario, SIVE.BIN). Re-running keeps existing `en`.

Row: `id`, `off`/`end` (file offsets of the run), `block`, `bank` (`scene`, `battle`, `bank7`, `orphan`), `spk` (opcode:speaker id), `kind` (`dlg`, `choice`), `jp`, `en`.

Tags: `{n}` new line, `{hero:N}` first hero's name (N characters), `{name:N}` second name, `{w:N}` pause, `{num:a,b}` number, `{var}` run-time name (battle lines), `{8031}`, `{800c}`. Keep every tag; `{n}` may move.

62,460 rows, 11,241 unique (337,543 characters). Most of the volume is the common banks repeated in every file: translate them once and let `propagate.py` copy them.

## Flow per scene

1. `python tools/slice_view.py K000 [start end]` -> `work/source/dump/view_K000.txt` (id, block, kind/bank, speaker name, text; rows already translated show `=> English`).
2. Write `work/translation/en/drafts/K000.py` (`EN = {row index: text}`).
3. `python tools/apply_draft.py K000 --dry`, fix what it reports, then without `--dry`.
4. `python tools/propagate.py --dry`, read the sample, then without `--dry` (fills rows with identical source text: 8+ characters, choices, and every row of the common banks).
5. `python tools/relink.py K000` (report: rows inserted, dictionary, whether a bank continues after the file end, verify result).
6. `python tools/strip_jp.py` -> `*.en.json` (the only translation files to commit).
7. `python tools/build.py` builds the disc (stop the emulator first: it keeps the image open).

## Limits checked by `apply_draft.py`

* Characters: A-Z a-z 0-9 space and `! ? : ( ) / & % + - = ~ , . ' " ;`. Nothing else exists in the font. Write an ellipsis as three periods.
* Line width 240 px (about 40 characters; `enfont.text_width('text')` gives pixels). A name tag counts 12 px per character.
* 3 lines per page (more only if the source row has more).
* 150 visible glyphs per page.
* Dialogue rows start and end with a straight double quote when the source has corner brackets; after `{n}` put one space so the text lines up under the first line.

## Status

| Scene | Rows | State |
| --- | --- | --- |
| K000 (opening tavern scene, first scenario) | 33 of 139 | drafted, self-checked only; seen in the emulator on 0.2.0 |
| everything else | - | not started |

The three review stages of `BASE_RULES.md` (accuracy, editorial, proofreading) have not been run.

## Translator's notes (for the accuracy review)

* K000_0038 (the hero, after the soldiers' boasting): the source does not say what "does not suit" whom; kept open ("...Doesn't suit you.").
* K000_0012: the barkeep speaks of the hero as a young man with a future; "his" rests on the soldiers calling him "兄ちゃん" in the same scene.
* K000_0032: 動乱 rendered "War" ("Ordoba War"); the first game's project uses its own wording for the same event, to be unified.
* K000_0015 / 0019: wordplay on "oil" (machine oil for the Void / alcohol for the men) kept.
* Speaker 27 `主人` is rendered "Barkeep" in the glossary (he runs the tavern); names in the name box are still Japanese.
