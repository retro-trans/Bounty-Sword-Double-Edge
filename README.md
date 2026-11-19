# Bounty Sword: Double Edge — translation project

An open toolchain for translating **Bounty Sword: Double Edge** (PlayStation,
SLPS-01479), plus the English translation built with it.

## Contribute

The whole script is translated and has been through accuracy, editorial and
proofreading passes, but most of the game has not been played in English yet
and no fluent human has read it against the Japanese. If you want to
contribute to this project or the next in any way — be it bug reports,
proofreading or playtesting — please join my Discord:

**[discord.gg/nZBZfTDfCP](https://discord.gg/nZBZfTDfCP)**

## Play it

The latest release is **[v0.3.19](https://github.com/retro-trans/Bounty-Sword-Double-Edge/releases/tag/v0.3.19)**,
a full patch for the original Japanese release (**SLPS-01479**). It is the
first public build: every dialogue scene in both scenarios, the menus, name
entry, save/load, the opening telegram, epilogues and town descriptions are in
English, drawn with a variable-width font.

### Apply

Use [Retro Trans](https://github.com/retro-trans/retro-trans-tools), or apply the `.xdelta` with DeltaPatcher or xdelta3. You need your own unpacked Japanese disc image (single-track BIN/CUE, MODE2/2352).

| Your source image | Patch |
|---|---|
| Original Japanese release, SLPS-01479 | `BountySword-DoubleEdge-English-v0.3.19.xdelta` |

Check the source hash in `README-v0.3.19.txt` if your patcher reports a mismatch; keep checksum verification enabled.

For example:

```
xdelta3 -d -s "Bounty Sword - Double Edge (Japan).bin" BountySword-DoubleEdge-English-v0.3.19.xdelta "Bounty Sword - Double Edge (English v0.3.19).bin"
```

The patched image is about 6 MB larger than the original. Point your CUE at the new BIN:

```
FILE "Bounty Sword - Double Edge (English v0.3.19).bin" BINARY
  TRACK 01 MODE2/2352
    INDEX 01 00:00:00
```

For manual patching of a CHD, extract it to BIN/CUE first; Retro Trans Automatic supports compatible CHD inputs.

**Boot the new image fresh and load an in-game memory-card save.** Old emulator save states keep the previous executable and text in memory.
Memory-card saves from earlier test builds load fine; party members who joined in a build older than v0.3.15 have their names switched to English when they are shown.

## Translate it

Fork it to fix the English, or to take the game into another language. Start
with **[docs/TRANSLATING.md](docs/TRANSLATING.md)**.

```sh
python tools/extract_scenes.py            # pull the script out of your disc
python tools/slice_view.py K000           # readable view of one scene
#   ... write work/translation/en/drafts/K000.py ...
python tools/apply_draft.py K000          # checks width, lines, tags, characters
python tools/check_all.py                 # every row, before every build
python tools/build.py                     # builds work/output/BountySword2-en-v<version>.bin
```

You need your own copy of the game. This repository contains no disc image, no
game data and no dump of the original Japanese script — the extract tools
read those from the disc you dump yourself, and `tools/strip_jp.py` writes the
`*.en.json` copies that are committed here.

## What is here

| Path | Contents |
|---|---|
| `docs/TRANSLATING.md` | **start here** — the edit loop and the limits the tools enforce |
| `TOOLS.md` | every tool, what it is for, and when you need it |
| `tools/` | extraction, insertion, the VWF hooks and MIPS assembler, disc builder, emulator debugging |
| `work/translation/en/scenes/*.en.json` | the English script — 62,460 rows in 578 event files |
| `work/translation/en/ui/*.en.json` | menus, items, skills, system text — 2,756 rows |
| `work/glossary/` | names, speaker labels and terms |
| `docs/VWF.md` | how the text engine draws, the hooks and where they live |
| `docs/text_formats.md` | the event-file script and string-table formats |
| `docs/debug_tools.md` | driving DuckStation through its GDB server for tests |
| `BASE_RULES.md` | portable rules for running a project like this |
| `CHANGELOG.md` | every build, what changed, and what broke |

## Real hardware

The patch changes game code (variable-width text, name entry, a few fixes) and
moves two event archives to the end of the disc. It has only been tested in
DuckStation. Hardware notes are in `CHANGELOG.md` and `docs/VWF.md`; reports
from a real PlayStation are welcome.

## Do not sell this

This patch is free. Do not sell it, and do not sell anything made with it -
no pre-patched discs or images, no loaded memory cards or consoles, no
paywalled or ad-gated downloads.

It is an unofficial fan translation. Selling it takes money for work that was
given away, and it is the surest way to get a project like this shut down.

## Credits

The English font is [Silver by Poppy Works](https://poppyworks.itch.io/silver)
(CC BY 4.0), drawn into the game's own font page. Thank you to its creators
and contributors.

The engine work builds on the sibling Bounty Sword First project; its tools
are kept in `tools/ref_bsf/` for reference.

| Role | |
|---|---|
| Project lead | pow |
| Playtesting | pow |

Translation passes, tooling and reverse engineering were done with Claude
(Anthropic), directed by pow. The translation is machine-produced and then
edited - see the release notes for what that means in practice.

The README and release-note layout follow
[retro-trans/SRW-Z](https://github.com/retro-trans/SRW-Z).

## Status

The translation is complete and in testing. `CHANGELOG.md` is the honest
record. Known open items:

- The looping-music fix in the Griffith scene (K161) needs confirming by ear.
- The Asgard town screen has not been seen in game yet.
- The war prologue text is translated but the original game never shows it.
- Only the first part of the game has been played through in English.
