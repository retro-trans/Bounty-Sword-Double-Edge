# Tools

Every tool lives in `tools/`. Run them from the repository root with Python 3.11+
(Pillow for the font tools, capstone for `disasm.py`). Most read the original disc from the
repository root and write under `work/`; nothing touches the original image.

## Text and script

| Tool | What it does |
|---|---|
| `extract_scenes.py` | Extract dialogue rows from the event files (KIVE.BIN = K###, SIVE.BIN = S###). Ported from Bounty Sword First. |
| `scene.py` | Event file (KIVE.BIN / SIVE.BIN entries) script parser. Ported from the Bounty Sword First tools. |
| `bs2_text.py` | Bounty Sword Double Edge text encoding helpers (16-bit glyph indices + control words). Script code == glyph index in the font page (WIN.BIN entry 0); see tools/font.py. |
| `extract_tables.py` | Extract string tables that are 'u32 offset table + strings ended by FFFF' (FFFE = new line). |
| `slice_view.py` | Write a compact view of a scene's rows for translating: slice_view.py K000 [start end] -> work/source/dump/view_<scene>.txt |
| `apply_draft.py` | Apply a draft (work/translation/en/drafts/<scene>.py, dict EN: row index -> text) to the scene file. |
| `check_all.py` | Check every translated scene row with the same rules as tools/apply_draft.py. |
| `propagate.py` | Copy finished translations to untranslated rows whose Japanese text is identical. |
| `sync_owners.py` | Every copy row (owners.json: row -> owner row) takes its owner's current English. |
| `rowkeys.py` | Which rows share one translation, and which scene owns it. |
| `fix_terms.py` | Unify spellings that different translators coined for the same term (BASE_RULES: scripts fix names). |
| `relink.py` | Rebuild an event file's script banks with the English text (ported from the Bounty Sword First relinker; see docs/VWF.md). |
| `strip_jp.py` | Write committable copies of the translation working files without the Japanese script text. |
| `make_glossary.py` | Build work/glossary/speakers.json (note: the 'box' field, a <=16-letter short form for the name box, is kept by hand in the JSON; re-running this script drops it) from the speaker name table in overlay 1 (file offset 0x1B278, 178 entries of 6 glyphs; a long name uses two consecutive entries) and fill the English names. Speaker id = argument of script ops 8002 / 804F / 8024 / 8033 / 8061 / 8064. No English release or wiki exists for this game: every spelling is a romanization. Cast names follow car makes and chassis codes (TVR Cerbera / Griffith, Jaguar, Mazda FD3S / SA22C, Lotus Elise, Ford Cortina), as the first game's follow gun makers; those spellings are used. '~' = second half of the previous entry's name. |

## UI strings

| Tool | What it does |
|---|---|
| `ui_scan.py` | List real UI strings (u16 glyph runs ended by FFFF, FFFE = new line) in the EXE, overlays and WIN.BIN entries. Writes work/source/dump/ui_strings.txt (contains Japanese: never commit). |
| `ui_extract.py` | Extract UI / system strings for translation (in-place insertion with letter pairs). |
| `ui_insert.py` | UI strings: apply translator drafts and patch the files in place. |
| `nameentry.py` | Name-entry screen (overlay 20): Latin letters first, English default names, English menu row. |
| `validate_release.py` | Validate a published release's uploaded assets (run by the GitHub workflow). |
| `hot_ui.py` | Write translated UI rows (text only) into the running game, for testing without a rebuild/reboot. |

## Font and VWF

| Tool | What it does |
|---|---|
| `font.py` | Game font access: WIN.BIN entry 0, chunk at 0x1f8 (type 0x12, 4bpp 256x256, VRAM 768,0). Bits 0..2 of each 4bpp pixel are three independent 1bpp planes; bit 3 is always set. Glyphs are 12x12 cells, 21 per row, 21 rows per plane -> 441 cells x 3 planes = 1323 glyphs. Glyph index g -> plane g % 3, cell g // 3. |
| `enfont.py` | English font for the VWF: Silver (CC BY 4.0, Poppy Works) drawn into the game's font page. |
| `fontgrad.py` | Vertical gradient on the game font (two tones with a dithered blend). |
| `build_table.py` | Build glyph-index -> Unicode table by matching the game font against MS Gothic 12px bitmaps. Writes work/glossary/charmap.json: list of {idx, ch, dist, alt}. |
| `make_charmap.py` | Finalize charmap: auto-match (tools/build_table.py) + manual fixes for the custom kana/ASCII glyphs. Output work/glossary/charmap.json : {"<glyph index>": "<char>"} ; script code == glyph index. |
| `hooks.py` | MIPS hooks for the English build (assembled with tools/masm.py). |
| `masm.py` | Tiny two-pass MIPS R3000 assembler for game hooks (no delay-slot magic). |

## Disc build

| Tool | What it does |
|---|---|
| `build.py` | Build the English test disc. |
| `build_disc.py` | Patch files inside a copy of the Riot Stars BIN (Mode 2 Form 1, ISO9660). |
| `psxiso.py` | Minimal ISO9660 reader/writer helpers for PS1 MODE2/2352 images. |
| `cdsector.py` | CD-ROM Mode 2 sector helpers: EDC and ECC (P/Q) generation. |
| `timdump.py` | Scan a file for PS1 TIM images and dump them as PNG (for locating fonts / UI graphics). |
| `sjis_scan.py` | Scan files for Shift-JIS text runs (full-width + half-width kana + ASCII). Counts only to console; full text goes to a UTF-8 file (kept out of git under work/source). |

## Debugging

| Tool | What it does |
|---|---|
| `gdbdbg.py` | Drive the game through DuckStation's GDB server: virtual pad + VRAM grabs. |
| `gdbmem.py` | Minimal GDB remote-protocol client for DuckStation's GDB server (port 2348, RS_GDB_PORT; 2345 is often taken by other emulators). |
| `gdbreset.py` | Remove stale breakpoints left by an interrupted gdbdbg run and resume the CPU. |
| `dsstate.py` | Read DuckStation save states (format 'DUCC', zstd data): RAM and VRAM. |
| `narr_shots.py` | Render overlay-20 narration blocks (epilogues, town descriptions) in game through the telegram's narration printer and save each page: boots through name entry over GDB (tools/gdbdbg.py), waits for the telegram, then for every block points the printer's text at it (struct at *(0x80062884) +0x5C, index *(0x80062610)+0xA = 1), resets the pen and the glyph buffer, presses Circle at page waits and grabs the screen. |
| `bdis.py` | Disassemble this game's code: bdis.py exe\|ovlN <addr> [count] \| bdis.py exe\|ovlN xref <addr> Overlay load addresses: 1 -> 0x800F07E0, 2 and 20 -> 0x8011888C (others: pass base as 4th arg). |
| `mdis.py` | MIPS disassembly helpers for SLPS_007.57 / RAM dumps. mdis.py <file> <addr> [count] disassemble (file: exe or 2MB ram dump) mdis.py <file> xref <addr> find lui/addiu\|ori\|load pairs and jal referencing addr mdis.py <file> str <text> find ascii string, print address |
| `disasm.py` | Disassemble the EXE or an overlay: python tools/disasm.py EXE\|O001\|O020 start_addr count |
| `sigmap.py` | Map code addresses from Bounty Sword First (sibling project, same engine) to this game by instruction signature: opcode + registers are compared, immediates and jump targets are ignored. python tools/sigmap.py <addr> [<addr> ...] (addresses in the sibling's EXE / overlay 1) |

`tools/emu.ps1` drives the portable DuckStation in `work/emulator/` (keyboard input, savestates).
`tools/ref_bsf/` holds the Bounty Sword First tools this project was ported from, kept for reference.

The full edit loop is in [docs/TRANSLATING.md](docs/TRANSLATING.md); the debugger workflow is in
[docs/debug_tools.md](docs/debug_tools.md).
