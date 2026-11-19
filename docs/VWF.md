# VWF (variable-width font)

Code: `tools/hooks.py` (MIPS source, patch sites), `tools/enfont.py` (font), `tools/build.py` (disc).
State: dialogue path done and seen in the emulator (0.1.0). Everything else below "Not done" is still fixed-width Japanese.

## Font

Silver (CC BY 4.0, Poppy Works — attribution required; `tools/fonts/silver/source.json`) at its native 19 px size, drawn into the game's own font page (`WIN.BIN` offset 0x20C). 80 glyphs, 3-7 px wide (`work/ui/font_en_cells.png`):

* digits, A-Z, a-z redraw the game's full-width Latin cells (19-80);
* `! ? : ( ) - = %` redraw the matching full-width symbols; `,` `.` redraw the Japanese comma and full stop (1, 2); `"` redraws both double corner brackets (13, 14); `/` redraws the multiplication sign (16); `+` redraws 1314;
* the font has only two cells the game's text never uses (1312, 1322): they hold the narrow space and the apostrophe;
* `;` `&` `~` take three kanji cells that the whole script uses once each (740, 1120, 1160).

Side effect: untranslated Japanese text shows those cells in the new shapes (seen: the opening telegram's brackets are now straight quotes; Latin letters and digits in menus will be proportional-looking glyphs on a fixed grid).

Width table: one nibble per glyph for codes 0-80, plus a (code, width) list for the six other cells. Not listed = the game's fixed 12 px.

## Dialogue path

The printer in overlay 1 puts glyph number idx (0x80062656) at slot idx of a position table (0x8010B8BC): 20 columns of 12 px per line starting at x = 56, three lines, 21 slots per line; the 21st slot's kind byte (0x8010BA14) makes the printer jump to the next line. New line (0x8005) looks up the next line start in a table at 0x8010B9BC.

Hook `vwf_dialogue` replaces `jal 0x80019268` (add glyph to the pool) at four sites that share the same placement code: 0x800FAAC8 (dialogue text), 0x800FC6B0, 0x800FD42C, 0x800FE06C (name insert / inline text handlers). It

* keeps its own pen x per line (reset when the column is 0) and places the glyph at line start + pen;
* advances the pen by the glyph's width (12 if it has none);
* holds both slot counters at column 19 while the pen is below 240 px, so the 20-column wrap never fires on English; past 240 px the counters run on and the game wraps by itself (mid-word: the translation checker must keep lines under 240 px);
* gives a space no pool slot (it returns the first free slot index, which the caller only tags with the window number).

Seen in the emulator on 0.1.0 (`work/ui/v010_vwf_first_dialogue.png`, `work/ui/v010_vwf_test_pages.png`): one- and two-line pages, a 140 px line of 20 W, a line of 25 i, punctuation, apostrophes.
Only site 0x800FAAC8 has been exercised. The other three have the same code shape but were not triggered in the test.

## Hook placement and risks (as of 0.3.6; source of truth: tools/hooks.py)

| Block | Address | Size | Contents | Evidence it is free |
| --- | --- | --- | --- | --- |
| overlay 1 | 0x801014D8 | 1,108 of 1,116 bytes | dialogue VWF, packed-token fetch, glyph_w, name_box / hero_box, name_ptr, narr_add, party_fix (part A) | zero in the file and in RAM dumps (boot, telegram, first dialogue) |
| overlay 1 | 0x80101A48 | 256 of 262 bytes | tele_bc / tele_b4: overlay-20 narration printers with pair expansion | zero in every RAM dump |
| overlay 1 data | 0x80104F60 | 304 of 312 bytes | width tables, pair table, pf_tab (old-save name keys) | same |
| overlay 1 | 0x8010BA58 | names blob + 144 bytes | English speaker names (speakers.json, `box` short forms); pf_b (party_fix part B) in the unused tail | replaces the original 178 x 12 table |
| EXE | 0x80060A60 | 508 of 510 bytes | ui_glyph (menu VWF, pairs, fixed digits, fixed range 0x0A00+glyph, party_fix call), xglyph_w | zero in the file and RAM dumps |
| EXE data | 0x800608D0 | tables | EXE copy of width and pair tables | same |
| overlay 20 | 0x80167000 | 1,916 bytes | English telegram + war prologue (pointer at 0x8012CF40) | zero in the file and in RAM while the telegram shows |

Patched entry points: add_glyph 0x80019268 (4 dialogue sites), token fetch 0x800FA724 / 0x800FAB28,
menu glyph 0x80018DF4 (`j ui_glyph`), narration jal sites 0x80121290 / 0x801210A4, name box
0x800FC120 / 0x800FC048.

Glyph list: 200 entries x 12 bytes at 0x800D5560; entry 200 would be 0x800D5EC0 (the sound
library's tick rate). add_glyph searches 199 entries (patched), so a full list reuses entry 199.
Keep every screen / narration page under about 190 drawn glyphs (blanks and spaces in narration
do not count).

Old-save party names (0.3.17): party slots are 24 x 0xB8 bytes at 0x800C94B4 (EXE BSS, saved with
the game); a unit's 8-cell name is copied from its overlay-1 template (0x800FFD60 + k x 0xB8) when it
joins, so saves made before 0.3.15 keep Japanese names. ui_glyph jumps to party_fix when overlay 1
holds it (signature word `lui t9, 0x5046`); party_fix runs only while a Japanese glyph (0x81..0xA00)
is being drawn and replaces every slot name whose key ((cell0 | cell1 << 8) + cell4) matches a
Japanese unit name with the English template name. Hero / rival (typed) names are left alone.

Menu text colour (0.3.17): beige windows draw colour 0x30 (CLUT group 1, was grey 2529, now near-black
0421; 0 would be transparent). The renderer's built-in drop shadow (second sprite at +1,+1 with the
CLUT group 0x60 above) was only used for colour 0 with flag != 1 (dialogue); the test at 0x80019168
now gives it to colours 0 and 0x30 whatever the flag. Shadow colour: CLUT group 2 (light warm grey 10,9,8);
menu sprites are tinted 0xFF (2x, patched at 0x80019084, was 0xC0) so their shadow is lighter.

Text rules the hooks impose:
* Menu / UI rows: letter pairs 0x1000 + a*128 + b; digits never paired (shop placeholders), except in
  the overlay-20 narration ranges; 0x0A00 + glyph = drawn at the fixed 12-px cell (name-entry grid).
* Narration (telegram, prologue, epilogues, area texts): pairs; at most about 190 glyphs per page
  (the printer's glyph buffer holds 200); page break FFFC FFFD FFFE.
* The name-entry field draws the typed name proportionally over fixed underlines (the field is drawn
  by the shared window printer and cannot be told apart from menus).

Real hardware: files are replaced in place, except KIVE.BIN / SIVE.BIN which move to the end of the
image (2532 more sectors); EDC/ECC rewritten. Hooks use only caller-saved registers or save what they
use on the stack. Not tested on hardware.
