# In-game debug tools (DuckStation + GDB)

General method: `debug_tools_guide.md`. Emulator: `work/emulator/duckstation` (portable copy from the Bounty Sword First project, muted, GDB port **2348** so both projects can run at once; `RS_GDB_PORT` overrides). Only this copy is started or stopped (matched by full path).

| Tool | What it does | Guide step |
| --- | --- | --- |
| `tools/emu.ps1 start <cue> [-StateFile s]` / `stop` | start/stop the project emulator; `stop` writes the resume state (`savestates/SLPS-01479_resume.sav`), which is how states are saved | 1 |
| `tools/gdbmem.py read/dumpram/regs/which` | memory and registers | 1 |
| `tools/gdbreset.py` | clears the known breakpoints and resumes after an interrupted run | 1 |
| `tools/gdbdbg.py run "press circle 6; wait 60; shot x.png [x y w h]; vram v.png"` | buttons and VRAM grabs without window focus; a grab takes about half a second | 2 |
| `tools/dsstate.py` | RAM/VRAM out of a savestate (copied, not yet tried on this game) | 3 |
| `tools/bdis.py exe\|ovlN <addr> [n]` / `xref` | MIPS disassembly and references | - |

Not built yet: function tracer, safe halt with thread checks, hot reload, scene preview, coverage scan of a built image.

## Addresses

| Address | Meaning |
| --- | --- |
| 0x8002F83C | end of the pad read, after `nor v0`: hit once per frame **from the main loop** (interrupts on, stack 0x801FFE90); OR button bits into v0 here. Not hit during disc loads (the client waits up to 90 s). |
| 0x80036EE0 / 0x80036BB8 | StoreImage / DrawSync (the grab stub calls both from the pad breakpoint) |
| 0x801F0000 | grab scratch, 0x8C00 bytes, stub at 0x801F8C00 (zero at boot; saved and restored around each grab; not proven unused in battle) |
| 0x80062754 | script read pointer (verified live: file offset 0x2F4 of K000 at the first dialogue) |
| 0x8010C84C | event file base (K000 matched 99.5% there during the first dialogue) |
| 0x80062AC6 | current token |
| 0x80062656 / 0x8006297E | dialogue slot index / wrap index |
| 0x80062800 | current window number |
| 0x800D5560 | glyph pool, 12 bytes per entry (+0 flags, +2 window, +4 glyph, +6 x, +8 y) |
| 0x800F10E0 | opcode handler table |
| 0x800F07E0 | overlay 1 (always loaded) |
| 0x8011888C | overlay 20 (title, name entry, opening telegram) or overlay 2 (event scenes) |
| 0x8010BA58 | speaker name table, 178 entries x 6 glyphs |

## Savestates (`work/emulator/states/`)

| File | Disc | Where |
| --- | --- | --- |
| `jp_k000_first_dialogue.sav` | original | first scenario (hero named with one throwaway kana), tavern scene, third dialogue page open |
| `v010_k000_dialogue_end.sav` | 0.1.0 | first scenario (default hero name), tavern scene, just after the seven VWF test pages |

## Reaching the first dialogue from boot

`wait 300; press start; wait 120; press start; wait 200` (logo, title), `press start` (menu), `press circle` (New Game), intro movie: `press start`, `press circle` (scenario "EASY EDGE" = first hero), name entry: `press start; press circle` (confirm), second hero's name entry: `press start; press circle`, `press circle`, then the opening telegram (text drawn by overlay 20 from its own data, not from the event file) and after a disc load the tavern dialogue (K000).

## Lessons

* The sister project waited for DrawSync to run its grab stub. Here DrawSync is not called in every state (after New Game it never came), while the pad read always runs in the main loop, so the stub runs from the pad breakpoint.
* The intro movie shows as noise in a 15-bit VRAM view (24-bit frames).
* Two different DuckStation copies can run at once only with different GDB ports.

## Emulator input gotcha (2026-11-18)
`tools/emu.ps1 keys` sends keyboard keys (Z = Circle, X = Cross, Return = Start, ...). The project
emulator's `work/emulator/duckstation/settings.ini` [Pad1] may be bound to an SDL gamepad
(`SDL-0/...`), and then the keys only get through by chance. For scripted tests, bind Pad1 to
`Keyboard/Z` etc. while testing and put the gamepad bindings back afterwards.
Movies: Start skips the attract and intro movies once input works. Route to name entry:
title -> Start (several times) -> NEW GAME (Circle) -> Start (skip intro) -> Circle (EASY EDGE).
A savestate inside the title already holds overlay 20 in RAM, so telegram / name-entry changes need
a fresh boot.

## Emulator killed during long runs (2026-11-19)
Another project's session on this machine restarts its own DuckStation by killing every process
named `duckstation-qt-x64-ReleaseLTCG`, which also kills this project's test emulator mid-run
(GDB connection reset). For long automated runs, copy work/emulator/duckstation to the scratch
folder, rename the exe (e.g. bs2emu.exe) and start that one; drive it with tools/gdbdbg.py (no
keyboard needed). Close it with CloseMainWindow() to get a resume state (savestates/
SLPS-01479_resume.sav). Map savestate: work/emulator/states/v0314_map_day1.sav.
