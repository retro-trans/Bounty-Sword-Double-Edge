# Changelog

## 0.3.19
- Shadow made subtler: shadow colour (10,9,8) instead of (8,7,6). Menus (drawn at 2x) now show it as
  about (160,144,128) on the (184,176,152) beige; the dialogue shadow on blue is slightly lighter.
- Checked in game: load prompt, first tavern dialogue.

## 0.3.18
- Menu text shadow toned down: menu glyphs are tinted 2x instead of 1.5x (0x80019084, the black
  text is unaffected), and the shadow colour is a warm grey (8,7,6) instead of (6,6,6). The dialogue
  shadow uses the same colour at 1x, so it is very slightly lighter and warmer.
- Checked in game: load screen and load prompt.

## 0.3.17
- Party names from old saves: saves made before 0.3.15 kept Japanese names for units already in the
  party (e.g. Griffith, Void No. 3 on the party screen). The game now swaps any party name that
  matches a Japanese unit name for the English one while such a name is drawn (EXE glyph hook +
  overlay 1 party_fix; docs/VWF.md). Hero / rival names you typed are not touched.
- Menu text (beige windows: camp menu, party, save / load, name entry, map labels) is black with a
  1-px drop shadow instead of grey. Dialogue and narration (white text) are unchanged.
- Hardware note: the shadow doubles the sprites drawn for menu text (the game already does this for
  dialogue); same draw routine and primitive path as the original.
- Checked in game: load from memory card, map, camp menu, party screen (Japanese names written into
  the party slots were replaced), Set Master submenu, save / load prompt, name entry grid, telegram.
- New tool: tools/disasm.py (capstone disassembly of the EXE / overlays).

## 0.3.16
- Name entry prompts translated: "Please enter the hero's name." / "Please enter the rival's name."
  (skip 9: the strings start with a 9-cell window header).
- Checked in game: both prompts on a fresh boot.
- Checked in game: the save prompt "File1 : Write it." (0.3.15 spacing), map savestate plus RAM patch.

## 0.3.13 - 0.3.15
- UI scan now accepts all-kanji strings (it only counted kana before): 313 more rows found and
  translated or marked as data (camp menu Map/Party/Equip/Tactic/Config, tactics values, config
  values, plateau and town labels, skill / item / class names in overlay 1, zodiac labels...).
- Unit records (overlay 1, 23 records, 8-cell names): Kane, Cerbera, Griffith, ... Void No. 1-3.
  Saves made before this keep the old names for units already in the party.
- Map day counter: "Day 1" (第 string rewritten to "Day ", 日 string emptied).
- Save / load prompts: the Yes / No line was broken (its first cell is the second argument of the
  c002 control code); skip 1 for those rows and "Can't equip". Saving... / Loading... headers
  translated (skip 7 template words). "File 1: Save" / "File 1: Load".
- Jungle plateau label (the box shows 5 cells): skip 2, "Jungle Plt".
- Tactics labels shortened so they no longer run into their values (Foe Near / Heal at / Cure by).
- Font gradient toned down (white 29 -> 24, was 31 -> 21).
- Checked in game: map, camp menu, party list, tactics, config, save and load prompts.

## 0.3.12
- Dialogue alignment: the text is drawn 4 px further right (hooks.py DLG_SHIFT), so the opening
  quote sits on the box edge instead of outside it and the text lines up under the speaker name;
  the quote glyph is redrawn 4 px wide (= the indent space), so every line's text starts in the
  same column. Line limit in apply_draft / check_all lowered to 236 px; 10 rows re-wrapped
  (K071_0222, K073_0137, K091_0005, K096_0018, S095_0033, S095_0062, S101_0125, S111_0120 and copies).
  Checked in game (tavern dialogue).

## 0.3.11
- Font gradient (tools/fontgrad.py): light text (and the two reds) is brighter at the top of each
  letter and darker at the bottom, with a dithered blend on cell rows 5-6. Uses the font page's
  spare bit 3 (cleared on the lower rows) and the unused CLUT entries of the six font CLUT sets
  (WIN.BIN entry 0 +0x8084, entry 6 +0x10594); shadows and the dark menu text stay flat.
  Checked in game: dialogue, telegram, name entry.

## 0.3.10
- FIX (K161 "sound keeps repeating"): the text glyph list (200 entries at 0x800D5560) had no
  overflow guard: when full, add_glyph wrote entry 200 = 0x800D5EC0, the sound library's tick rate
  (60). Overlong English pages (the 0.3.2-0.3.4 telegram) overwrote it with 2 and the music played
  at the wrong tempo from then on (the user's 0.3.2 state shows exactly that write). Both add_glyph
  copies now search 199 entries, so a full list reuses entry 199 and never writes past the list
  (EXE 0x80019290 / 0x800192F0, original-instruction checked). Verified: the tick stays 60 through
  the telegram. Saves made on 0.3.2-0.3.4 may still carry the bad tempo until the music restarts.
- Narration: blank and space glyphs no longer take glyph-list entries (they draw nothing).
- Epilogue header for Griffith (first ending) lost "Romu": the epilogue table points two cells into
  the row; overrides.json skip 2 and a 17-cell header.
- Town descriptions (Asgard, the DMZ camp, the crash-site village) tightened to 175-185 glyphs so
  they fit the glyph list (their printer cannot page); every fact kept.
- All 29 epilogue blocks and the 3 town descriptions rendered in game through the narration printer
  (tools/narr_shots.py; captures in work/ui/narration2..4).

## 0.3.9
- Name entry: the typed name in the name field is drawn at the original fixed 12-px cells again, so
  each letter sits over its underline (menu hook: the window-printer call 0x80127758 in overlay 20,
  via 0x80026F0C / helper 0x80026D94, keeps the fixed advance). Verified in game.
- War prologue (overlay 20, 0x2FF02): no code reads it (the narration text pointer has only two
  writers: telegram and epilogues), so it is unused data in this release; the English copy stays.
- Area descriptions: the table at 0x8015F054 covers Asgard and two later towns, shown on the first
  visit; same pair-expanding printer hook as the telegram and epilogues (both verified in game).
  The town screen itself not yet seen.
- Epilogue text verified in game by pointing the narration printer at Kane's epilogue (0.3.8).
- Tested on a fresh boot through name entry, telegram, the tavern and Ixion's camp briefing.

## 0.3.8
- 機人 is now "Machine Man" / "Machine Men" (Kane's coinage on 機神 Machine God); 機改機人 =
  Clockwork Machine Man; Fluid / Plant / Composite / Insect Machine Man. Mission objectives
  "Beat Machine Ixion" / "Beat Machine Hector". Glossary updated.
- お姉さん as the answer to オバさん is "young lady" everywhere (S008, S050, S159); "big sister" stays
  where Sera refers to herself comforting someone and in "Big Sister Diana".
- Reviewer-flagged wording rewritten: K021_0179, K021_0188, K108_0131, K160_0135, S161_0211;
  K069_0207.
- K161 "repeating sound" investigation (user's 0.3.2 state): game not frozen, no CD commands, hook
  memory intact; music is SPU-sequenced. Cause not found yet.

## 0.3.7
- Review of the whole scene script (BASE_RULES three stages): accuracy review + editorial pass in 8
  batches (12,029 owned rows, about 775 rows edited: wrong meanings, dropped details, reversed
  directions, glossary terms, forms of address), then proofreading in 4 batches (9 fixes).
  Conventions settled in docs/REVIEW_BRIEF.md (honorifics, the Professor's catchphrase, "old hag" for
  ババァ, six-dot silences, Laius = Kane's father, Hector = Sera's husband).
- New tools/sync_owners.py: copy rows inside drafted scenes take their owner's text (665 + 213 stale
  copies fixed; propagate.py --sync leaves drafted scenes alone). Sera's "~" drawl gone everywhere.
- Glossary-consistent names: "Thunder Storm", "Daze Dagger", "Back Cut", Holy Nation of Assyria.
- Checks: check_all 62,460 rows 0 problems; UI 2,420 rows 0 problems; every event file relinked
  and verified. Not boot-tested yet (text-only changes since 0.3.6).

## 0.3.6
- Telegram split into three pages: the narration printer keeps a 200-glyph buffer per page, and the
  English text overran it (the telegram stopped at "from Special"). Page break = FFFC FFFD FFFE.
- War prologue (Divine Calendar 4199, Third Great Europea War) translated and placed after the
  telegram, as in the original layout (not shown in the EASY EDGE opening; kept for wherever it is used).
- UI extractor: a control-code "argument" that is a kana/kanji glyph is text (C0AF / C067 / C00A ...
  take none), so rows like 防御 / 移動指示 / を使用します are whole again and translated.
- overrides.json skips for template headers: Funds, File, Move, AT, Weapon, "No Voids in the Carrier!",
  "Target here!"; save prompt "File N: Save it."; data rows marked "-".
- Comma and semicolon get a two-pixel tail (read as periods before).
- Verified in game (0.3.4/0.3.5): name-entry grid alignment, typed letters, Confirm/Cancel popup,
  telegram pages 1-3 with the player's name, new periods. Not seen yet: the comma fix, epilogues,
  area descriptions, the prologue.

## 0.3.3
- Name entry: the letter grid is drawn at the fixed 12-px cell again, so letters line up with the cursor (glyph codes 0x0A00 + glyph = fixed advance in the menu hook; only the displayed grid copies use them, the typed-character table keeps plain codes).
- Font: '.', ',', ':' and ';' hand-drawn as 2x2 dots on the baseline (Silver's dot looked like '+').
- Includes all 0.3.2 changes below. Verified: name-entry grid alignment. Not yet verified in game: typed names, the new punctuation, epilogues.

## 0.3.2 (not released)
- Telegram/narration printer hook moved to its own block (0x80101A48) and now expands letter pairs.
- Epilogues and area descriptions (overlay 20) inserted in place; {hero}/{name} tags for the player's names; digits pair in those ranges.
- New UI rows translated for O001, O002 and O020 (rows with template prefixes left as "-", need overrides).
- Not yet boot-tested; the 0.3.2 image predates the last UI rows, so rebuild it.

## 0.3.1 - English name box, name entry and telegram (not released)

Output: `work/output/BountySword2-en-v0.3.1.bin/.cue`. Same layout as 0.3.0 (KIVE/SIVE relocated to the end of the image).

- Speaker name box: English names drawn proportionally (`name_box` in `tools/hooks.py`, replaces 0x800FC120; the second 6-glyph part at 0x800FC208 is disabled). Names are stored byte-packed where the old 6-glyph table was (0x8010BA58, 1,988 of 2,136 bytes). The box tracks at most 16 glyphs (list at 0x80062998, counter 0x80062860): blanks take no slot, the routine stops at 16, and 25 long names have a short `box` form in `work/glossary/speakers.json` (e.g. "Rhein. Soldier A"). Found by a crash: a 19-letter name overflowed the list.
- Hero names in the name box are drawn proportionally too (`hero_box`, replaces 0x800FC048).
- Op 8031 (inline speaker name, unused by the script) and interpreter state 23 now print an empty name instead of reading the old table.
- Name entry (overlay 20, `tools/nameentry.py`): the Latin page (digits, A-Z, a-z) is shown first, swapped with the hiragana page in all three copies (the third is the table the typed character is read from); menu row "Fwd Bck OK"; default names Kane and Sera.
- Opening telegram: English text relocated to 0x80167000 (overlay 20, zero in the file and in RAM while it shows), pointer at 0x8012CF40 changed; overlay 20's two narration printers (0x80121290, 0x801210A4) advance by the real glyph width (`tele_bc` / `tele_b4`).
- Width tables and pair table moved to a second free block in overlay 1 (0x80104F60, 232 of 312 bytes); hook code 1,084 of 1,116 bytes at 0x801014D8.
- Tested in the emulator: name entry (typing gives Latin letters), the telegram, the name box with short and long names, the hero name box. Screenshots `work/ui/v031_*.png`.
- Still Japanese: the confirm popup on the name-entry screen (決定 / キャンセル), the 4199 war prologue block that follows the telegram in overlay 20 (no direct code reference found), menus and system text in the EXE and overlays, shop tables.

## 0.3.0 - full event script in English (not released)

Output: `work/output/BountySword2-en-v0.3.0.bin/.cue` (+ `.xdelta` against the original), log `work/output/build_v0.3.0.log`. 0.1.0 and 0.2.0 are kept as xdelta only. BIN/KIVE.BIN and BIN/SIVE.BIN grew (2,598,824 / 2,585,700 bytes) and now sit after the original last sector; the image is 2,532 sectors longer. OVLFILE.BIN and BIN/WIN.BIN are replaced in place.

- Event script translated: all 62,460 rows of both scenarios (12,029 unique rows translated by one agent per scene from `docs/AGENT_BRIEF.md`, the rest filled by `tools/propagate.py`). Every row passes `tools/check_all.py` (tags, font coverage, 240 px lines, lines per page, glyphs per page). All 287 event files rebuild and verify; the largest (S108) is 37,812 of 37,896 bytes. No row was left in Japanese.
- Row ownership (`tools/rowkeys.py`): identical text shares one translation in every bank; short lines only match a copy with the same speaker and neighbouring rows. `propagate.py --unify` makes every copy take its owner's wording (185 rows translated twice were unified).
- Spellings unified with `tools/fix_terms.py` (about 320 replacements: 機改 = machine everywhere, Machine Soldier, Defense Machines, Almighty Treasure, Blessed Isle, Esper Girl Corps, heavy MG, and others). Glossary: 178 speakers, about 330 terms.
- Charmap fix: glyph 1320 is 斬, not 漸 (found by a translator through the Severed Plateau joke).
- The three review stages of BASE_RULES.md have NOT been run. Open questions and consistency items are listed in `work/translation/en/review_todo.md` (stale speaker labels, address forms, Sera's "young lady" / "big sister", quoted choices, item-name joins, rows flagged as sensitive).
- Tested in the emulator: boot, both name entries, the opening telegram (still Japanese), the whole opening tavern scene with the fight, the English narration screen, the start of the Sera rescue scene. Not tested: anything later, battles, menus, saving, the second scenario, real hardware.
- Still Japanese: speaker names in the name box, menus and system text (EXE, overlays), the opening telegram (overlay 20), shop/service tables in WIN.BIN (extracted, not translated).
- Savestate: `v030_k000_sera_rescue.sav`. Screenshots: `work/ui/v030_k000_pages_a..e.png`.

## 0.2.0 - relinker and packed text (not released)

Output: `work/output/BountySword2-en-v0.2.0.bin/.cue` (+ `.xdelta` against the original), log `work/output/build_v0.2.0.log`. 0.1.0 is kept as `BountySword2-en-v0.1.0.xdelta` only. Image size unchanged; OVLFILE.BIN, BIN/WIN.BIN, BIN/KIVE.BIN replaced in place.

- `tools/relink.py`: script banks laid out again per bank, block tables and absolute/file-relative jump operands remapped, overflow continues after the file end through a jump, per-file word dictionary (offset in header slot 17). Self-check: all 294 scripted event files rebuild and verify with no translation.
- Packed text: letter pairs (0x1000+) and dictionary words (0x5000+), expanded by a fetch hook at the two token-read sites 0x800FA724 and 0x800FAB28 (`tools/hooks.py`, 856 of 1,116 bytes).
- `tools/scene.py` finds banks embedded inside other banks (no header slot); no raw data words remain in any stream.
- `tools/build.py` rebuilds KIVE.BIN / SIVE.BIN (filler bytes and aliased entries preserved; reproduces the originals byte for byte when nothing is translated).
- Row tools ported: `slice_view.py`, `apply_draft.py`, `propagate.py`, `strip_jp.py`; `docs/TRANSLATING.md`.
- Translated: K000 rows 7-39 (33 rows, draft, no review pass). Everything else is Japanese.
- Tested in the emulator: boot to the tavern scene, all 33 translated pages (pairs, dictionary words, the part stored after the original file end, two-part speaker names), then the next untranslated row.
- Found and fixed: the game writes to the last four bytes of an event file (header slot 1); a dictionary ending there was corrupted at run time. A spare word is now kept at the end.
- Not done: `docs/VWF.md` and `docs/text_formats.md` not yet updated for this build; name box, menus, overlay 20 text; choice menus and name inserts not seen in game; second scenario untested; no real-hardware test.
- Savestate: `v020_k000_after_row39.sav`. Screenshots: `work/ui/v020_k000_pages_a..d.png`.

## 0.1.0 — first test build: dialogue VWF (not released)

Output: `work/output/BountySword2-en-v0.1.0.bin/.cue`, log `work/output/build_v0.1.0.log`. No xdelta (this is the only version). The image has the original size; OVLFILE.BIN, BIN/WIN.BIN and BIN/KIVE.BIN are replaced in place.

- English font: Silver (CC BY 4.0) drawn into the game font page, 80 glyphs, width tables (`tools/enfont.py`).
- Dialogue VWF hook in overlay 1 at 0x801014D8 (404 bytes), four call sites (`tools/hooks.py`, `docs/VWF.md`).
- Build script `tools/build.py` (+ `tools/masm.py`, `tools/build_disc.py`, `tools/cdsector.py` copied from the sister project).
- This build contains **no translation**: seven VWF test lines are written over the first tavern conversation of the first scenario (`work/translation/en/test_inplace.json`). Everything else is Japanese.
- Tested in the emulator: boot, title, scenario select, both name entries, opening telegram, the seven test pages (one and two lines, widest and narrowest letters). Not tested: anything after that conversation, battles, menus, saving, the second scenario, real hardware.
- Known: the opening telegram's corner brackets show as straight quotes (those cells are redrawn); speaker names, menus and all other text are Japanese; only one of the four hooked call sites was exercised; the hook area is not proven free in battle.
- Not done: relinker and packed text (needed before real translations can be inserted), name box, overlay 20 text, menu text path.
- Debug tools: `tools/gdbdbg.py` grabs now run from the pad breakpoint (half a second each); savestates `jp_k000_first_dialogue.sav`, `v010_k000_dialogue_end.sav`.

## Unreleased — analysis and tooling

- Disc reader/extractor `tools/psxiso.py`; OVLFILE.BIN, KIVE.BIN, SIVE.BIN and WIN.BIN unpacked to `work/source` (git-ignored).
- Text encoding identified (u16 glyph indices + control words, not Shift-JIS); font located in WIN.BIN entry 0 and decoded (`tools/font.py`); `work/glossary/charmap.json` (1,323 glyphs) built with `tools/build_table.py` + `tools/make_charmap.py`.
- Event script format decoded (`tools/scene.py`): all 308 non-empty event files parse cleanly. Differences from Bounty Sword First are listed in `docs/text_formats.md` (absolute jump addresses, load address 0x8010C84C, nine new or changed opcodes, 37,896-byte file ceiling).
- `tools/extract_scenes.py`: 62,461 dialogue rows (11,242 unique, 337,552 characters) to `work/translation/en/scenes/`.
- Text outside the event files located with a scanner (EXE, overlays 1, 2, 20 and others, WIN.BIN tables); not extracted yet.
- Code located: script interpreter, opcode table, dialogue glyph placement and its position tables (see `docs/text_formats.md`).
- Tools: `tools/bdis.py` / `tools/mdis.py` (disassembly, references), `tools/timdump.py`, `tools/sjis_scan.py`, `tools/sigmap.py` (address mapping from the sister project by instruction signature), `tools/bs2_text.py`.
- Portable DuckStation copied from the Bounty Sword First project to `work/emulator/duckstation` (muted, GDB port changed to 2348 so both projects can run at once). Not started yet.
- `tools/ref_bsf/`: unmodified copies of the Bounty Sword First tools, kept as reference while porting.
