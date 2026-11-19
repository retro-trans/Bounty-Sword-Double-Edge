# Bounty Sword: Double Edge (SLPS-01479) — analysis notes

Status: analysis done for the event scripts; UI/system strings located but not extracted. No build exists yet.
Sister project with the same engine family: `E:\Projects\Bounty Sword First` (its tools were the starting point; unmodified copies are in `tools/ref_bsf/` for reference only).

## Disc

MODE2/2352, single track. `tools/psxiso.py <bin> [outdir]` lists/extracts (extracted to `work/source/disc`, git-ignored).

| File | Content |
| --- | --- |
| `SLPS_014.79` | main EXE, load 0x80010000, size 0x52800 |
| `OVLFILE.BIN` | overlays: (u32 sector, u32 size) per entry, 34 entries, sector*2048 = offset. Entry 1 = main game overlay (load 0x800F07E0; its last 37,896 bytes are zero = the event file buffer). Entries 2 and 20 load at 0x8011888C. |
| `BIN/KIVE.BIN`, `BIN/SIVE.BIN` | event files for the two scenarios (K = first hero, S = second hero): u32 header size, u32 total, then (u32 offset, u32 size) x 162. Entries 143/145..158 are empty. |
| `BIN/WIN.BIN` | archive: u32 offset table (104 slots). Entry 0 = font + UI graphics; 5, 76, 77 = string tables; 8 = copy of LVD.BIN; most others TIM images. |
| `BIN/KBG.BIN`, `SBG.BIN`, `FCG.BIN`, `CHAR/*`, `MOV/*`, `BGM.MXA`, `SND.ARC` | backgrounds, faces, sprites, movies, sound. No text found (`CHAR/PLY.BIN` scan hits are sprite data). |

## Text encoding

Not Shift-JIS. Text is u16 little-endian words:

* `< 0x52B` : glyph index in the game font (0 = space). `work/glossary/charmap.json` maps index -> character.
* `0xFFFE` new line, `0xFFFF` end, in UI strings (EXE, overlays, WIN.BIN tables).
* `0x80xx` : script opcodes in the event files (see below).

Font layout: 0-18 punctuation, 19-28 digits, 29-54 A-Z, 55-80 a-z, 81-160 hiragana, 161-242 katakana, 243+ kanji in reading order, 1291+ late additions and symbols.

## Font

`WIN.BIN` entry 0, chunk at file offset 0x1F8 (type 0x12 header of 20 bytes, then 0x8000 bytes): 256x256 4bpp, VRAM (768,0). 12x12 cells, 21x21 cells per plane; three glyphs share a cell in bit planes 0-2 (glyph g -> plane g%3, cell g//3); bit 3 always set. 1,323 glyphs. `tools/font.py` renders them (`work/ui/font_original_by_index.png`).

Charmap: `tools/build_table.py` (nearest match against MS Gothic 12px, 892 exact) + `tools/make_charmap.py` (punctuation, Latin and kana by position; 26 kanji fixed by eye after reviewing every match with distance >= 1). Unsure: 1260 (read as 亮), 1322 (second double-circle symbol).

## Event files

Header: 18 u32. Slot 1 = offset of the last word. Slots 3, 6, 7 = script banks (3 scene dialogue, 6 common battle lines, 7 a third bank). Some files hold a bank at 0x48 that no slot points at ("orphan", e.g. K003, K119); it is extracted too. Slots 2, 16 and others hold tables with absolute pointers into overlay 1 and into the file itself.

Banks can also sit inside another bank's stream with no header slot (copies of the common banks; `tools/scene.py` splits them off as slot 0). Header slot 1 points at the last four bytes of the file, which the game writes to at run time. Header slot 17 is unused (the English build stores the dictionary offset there).

A bank = table of u32 file offsets to blocks (ends where the first block starts) + a stream of u16 tokens: glyphs, opcodes `0x8000..0x8072` with fixed arguments (`ARGS` in `tools/scene.py`).

Differences from Bounty Sword First:

* The file is loaded at **0x8010C84C** (inside overlay 1's zero tail). Jump operands of most opcodes are **absolute RAM addresses** (file offset + 0x8010C84C), kind `O`. Choice-menu targets and the operands of 8038, 804D, 804E are file offsets, kind `F`.
* New or changed opcodes: 8033 `w` (speaker, hero), 8024 `w` (speaker), 803F `w`, 8070, 800C, 8021 (no args), 8072 `wwO`, 800D `ww`, 8062/8063 `wwO`.
* `0x8009`/`0x800A` (name inserts) can occur inside choice strings.
* A data table can follow a stream without a header slot (K119): the parser cuts the stream after its last opcode.

`python tools/scene.py v` parses all 308 non-empty files with no unknown word and every block start and jump target on a token boundary.

Ceiling: an event file may not exceed 37,896 bytes (0x9408; overlay 1 ends at 0x80115C54). The largest original is 35,752 bytes, so English needs packed text as in the sister project.

## Volume

`python tools/extract_scenes.py` -> `work/translation/en/scenes/K###.json`, `S###.json` (working files with Japanese: never commit).

| | rows | characters |
| --- | --- | --- |
| all rows | 62,461 | 1,704,767 |
| unique rows | 11,242 | 337,552 |
| of which scene dialogue | 10,101 | 304,024 |
| common battle bank | 1,308 | 37,599 |
| orphan banks | 536 | 15,124 |
| bank 7 | 36 | 779 |

Other text, located by `scan_runs` (dumps in `work/source/dump/scan_*.txt`), not extracted yet: EXE (~11,400 characters), overlay 1 (~8,200), overlay 2 (~22,300), overlay 20 (~27,900; 2 and 20 look like two builds of the same module), overlays 4-33 (small), WIN.BIN 5 / 76 / 77 (string tables, ~1,100 each), WIN.BIN 82 (~4,300), 12-15, 80, 81.

## Code found

| Address | Meaning |
| --- | --- |
| 0x800FA724 | interpreter loop (overlay 1): token fetch from the read pointer |
| 0x80062754 | script read pointer |
| 0x80062AC6 | current token |
| 0x800F10E0 | opcode handler table, index = code & 0x7FFF |
| 0x800FA7E4 | glyph path of the dialogue printer |
| 0x80062656 / 0x8006297E | dialogue slot index / wrap-table index (both +1 per glyph) |
| 0x8010B8BC | slot position table (x, y as s16): 20 columns per line at x = 56 + 12*i, lines at y 23, 38, 53; slots 20, 41, 62 are dummies |
| 0x8010BA14 | slot kind table (byte): 1 at slot 20 (go to slot 21), 2 at 41 (go to 42), 3 at 62 (back to 0) |
| 0x800FAAC8 | `jal 0x80019268`: add glyph (a0 glyph, a1 x, a2 y, a3 colour, 0x10(sp) = 2) — the dialogue VWF hook point |
| 0x800D5560 | glyph pool, 12 bytes per entry (+2 = window) |
| 0x80062A9C | typewriter budget (glyphs left this tick) |
| 0x800FAB28 | look-ahead read of the next token (second place that reads the stream) |
| 0x80026DA4 | draw a UI string (menus, system text): u16 words until 0xFFFF; 0xFFFE = new line; 0xFFFA / 0xFFF9 insert names; each glyph goes through the wrapper 0x80026CF0 (which calls 0x80018DF4 at 0x80026D8C), then the cursor x is advanced by the font descriptor's fixed advance |
| 0x80062A8C / 0x80062A90 | UI text cursor x / y |
| 0x80062608 | pointer to the font descriptor: [2] advance, [3] line height, +8 left x |
| 0x8002F83C | end of the pad read (mapped from the sister project by signature; not verified in the emulator) |
| 0x80036EE0 | StoreImage (same caveat) |
