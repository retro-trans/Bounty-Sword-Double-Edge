# Brief for a scene translation agent

You translate the scene files named in your task (for example `K041`) of the PlayStation game Bounty Sword: Double Edge from Japanese to English. Work only on those scenes.

Python: Python 3.11+ (called `PY` below). Run commands from the project root `E:\Projects\Bounty Sword 2`. Set `PYTHONIOENCODING=utf-8` when a command prints Japanese; prefer reading the view file with the Read tool.

## Read first

1. `BASE_RULES.md` — sections "When translating dialogue" and "When translating any kind of text". They are binding.
2. `work/glossary/speakers.json` (speaker id, Japanese name, English name) and `work/glossary/terms.json` (places, organizations, terms). Use these spellings exactly. Do not invent another spelling for a name that is listed.
3. `work/translation/en/drafts/K000.py` — a finished slice, as a model of register and format.

## Your input

    PY tools/slice_view.py K041

writes `work/source/dump/view_K041.txt`, one row per line:

    K041_0012 b3 dlg Tethys[804f] | <Japanese text>  => <English, if the row is already translated>

* row index = the number after the underscore (`K041_0012` -> 12);
* `b3` = script block (roughly one conversation or one branch); rows of the same block belong together;
* `dlg/battle`, `dlg/bank7`, `dlg/orphan` = rows of the common banks (battle cries, skill and system lines shared by many files);
* the name before `[` is the speaker of the dialogue box. On narration rows (text that does not start with a Japanese opening bracket) ignore it: it is left over from the previous box. A label can be stale: when the voice clearly is not the labelled speaker, translate by voice and say so in your report;
* `choice` rows are menu answers (keep them short);
* rows that end in `=> English` are already translated, and rows that end in `(SKIP: copy of ...)` are copies owned by another scene: do NOT translate either kind and do not put them in your draft. Read them for context.

Scenes are in story order by number. K = first hero's scenario (Kane), S = second hero's scenario (Sera); the same number in K and S is the same place in the story seen from the other side. For context you may read neighbouring scenes' views (`PY tools/slice_view.py K040`) and finished drafts in `work/translation/en/drafts/`. Do not edit them.

## What is known about the story (for voice)

Setting: an island battlefield ("this island of steel") where several armies fight over a buried treasure: the Republic of Romulus, the Kingdom of Rheinmetall, Rhodes, Assyria, the Folgore. People pilot or command "Voids" (combat machines; Void artisans modify them). A hundred years ago there was the Ordoba War.

* Kane (speaker 1; his name is player-chosen and written with the tag `{hero:6}` wherever the source has it): a young Special Service second lieutenant of the Romulus army. Terse, cool, unimpressed; plain "I".
* Sera (speaker 2; tag `{name:6}` where the source has it): the second hero. Work out her voice from the scenes and keep it consistent; say in your report what you settled on.
* Tethys (speaker 14) appears very often; also Alice, Cerbera, Griffith, Ixion (Special Service captain, Kane's contact), Faust, the Professor, FD-3S, Aerial, Ozunu, Toryu, Ayame, Diana, Jaguar, Parsifal, Ymir.
* Soldiers of the rival armies are rough and mocking. Shopkeepers and the barkeep are polite to customers.

Voices settled by finished scenes (keep them):
* Sera: polite, airy, a little ditzy; drawn-out sentence endings are written as stretched vowels ("thaat", "buut", "sooo"). She is 29; Kane calls her "old lady", she calls him "little boy".
* Alice: childish, gushing, short exclamations, stretched words; calls Kane "my prince". She is an Esper Doll; soldiers call her "it".
* Parsifal: loud and crude. Cerbera and Griffith say "sir"; Griffith addresses Kane as "Lt. {hero:6}". Faust, Ozunu, Aerial: polite, no contractions. FD-3S: clipped report style. Toryu: very few words.
* Sera's drawl is written ONLY with stretched vowels; never with "~". Kane's jab at her age is "old lady" (オバサン) or, for the harsher ババァ, "old hag"; her correction is that she is 29 and not an old lady.
* Ayame: archaic, formal English, no contractions. Aerial calls Sera "Lady {name:6}". Alice may call Kane "Prince {hero:6}" where the source uses his name.
* Titles too long for a line with a name tag may be shortened: "Special Service 2nd Lt.", "Lt. {hero:6}".
* Tethys speaks of herself in the third person as "Li'l Tethys", with over-polite tags ("if you please", "yes indeed"). The Professor is crotchety. Fortune Granny uses "ye/yer" and calls herself "Granny". Informant and Advisor are chummy hustlers.
* In speech 特務少尉 may be "Lieutenant" / "Lieutenant, sir". Skill and menu names: use the spellings in work/glossary/terms.json (type menu) and in work/translation/en/drafts/K004.py rows 182-217.
* FD-3S: ALL CAPS while broken or dormant (katakana speech in the source); once revived, plain formal English with no contractions.
* Ymir: serene, detached, polite, no contractions; says "humans"; a boy (Kane says "brat"). Lancelot: lofty, formal, no contractions. Ozunu calls Faust "Master Faust". Parsifal's shout is "C'mon, c'mon".
* Jaguar: halting, "..." between phrases, blunt. Raggadol: lofty, archaic, no contractions. Speech that decays into katakana in the source is written in ALL CAPS.
* Ange: clipped, article-dropping English for her broken speech ("Only can fight! That is fate!"). Alice says plain "Ange" and "Ayame"; Sera says "Ayame dear".
* Sigurd: grave, formal, no contractions. Juggernaut: slow, ellipses, formal. Ozunu says "Sir {hero:6}" / "Lady {name:6}"; Faust says "Master Ozunu"; Faust, Aerial and Sera say "Mr. {hero:6}" where the source has a polite suffix on his name. Sera's polite suffix on monsters and Voids is dropped.
* Alice 2nd / Ayame 2nd (the NEXT dolls): flat, emotionless, no contractions, report-style. Laius's epithet 斬殺の騎士 is "the Slaughter Knight". Laius (the Slaughter Knight) is Kane's late father; Hector is Sera's husband.
* Dragon Emperor: lofty, formal, no contractions, says "humans". Ixion and Ymir say "Miss {name:6}" for a polite suffix on Sera's name; Faust says "Miss Aerial". K159-K161 and S159-S161 are world-map comments (reports by Griffith/Cerbera and party remarks per map point).
* Kane and Ixion are childhood friends and speak casually to each other.
* 機改 is this world's spelling of "machine" (not "cyborg"). 全能の秘宝 = the Almighty Treasure; plain 秘宝 = the treasure.

Nothing else is established. Infer relationships from the scenes; do not invent backstory. Do not infer gender from a name; when a person's gender is not settled by the scenes, use a neutral construction.

## Your output

Write `work/translation/en/drafts/K041.py` (one file per scene):

    EN = {
    12: "\"I figured as much.{n} ...So, what do you want from me?\"",
    13: "Yes",
    }

Rules for the text:

* One row in, one row out. Key = row index. Only rows that are still empty and not marked SKIP.
* Dialogue rows start with a Japanese corner bracket in the source: start and end the English with a straight double quote `"` (escaped in the Python string). If the source row has no closing bracket (the line is cut off or continues in the next row), leave the English unclosed too. Double corner brackets (letters, signs, titles) also become straight double quotes.
* `{n}` is a line break. After `{n}` put ONE space before the text (so it lines up under the text after the opening quote). You choose where lines break; the source's breaks need not be kept.
* Other tags must be kept, each exactly as often as in the source, same spelling: `{hero:6}`, `{name:6}` (and other lengths), `{w:2}` (a pause: put it where the pause falls in English), `{num:a,b}`, `{var}`, `{8031}`, `{800c}`.
* Allowed characters ONLY: A-Z a-z 0-9 space and `! ? : ( ) / & % + - = ~ , . ' " ;` . Nothing else exists in the game font. Write an ellipsis as three periods `...`; no asterisk, no dash other than `-`, no accented letters, no curly quotes, no brackets other than `( )`. For a quoted term inside a line use single quotes: 'alcohol'.
* A page holds 3 lines (more only if the source row itself has more). Each line may be at most 240 pixels wide — about 40 characters, measured by the checker, not counted. A name tag takes 12 pixels per character of its length.
* At most 150 visible characters per row.
* Narration rows (no brackets in the source): no quotes in English.
* Write the line in full first, then fit it. If a faithful line cannot fit even after rephrasing, leave that row out of the draft and report it. Never drop the end of a sentence to make it fit.
* Do not soften insults or threats. Keep each character's way of speaking consistent with earlier scenes.
* Battle lines (`dlg/battle`): short shouts and reactions; keep them short and punchy, in the speaker's voice.

## Check and apply

    PY tools/apply_draft.py K041 --dry

Fix every reported problem (`WIDE`, `NO GLYPH`, `TAG MISMATCH`, `LINES`, `GLYPHS`) and run again until it prints `problems 0`. Work through a scene in consecutive slices of about 80 rows: draft a slice, dry-run, fix, then the next slice (keep adding to the same file). When the scene is done and the dry run shows `problems 0` and `still empty 0` (or only rows you are deliberately leaving), run:

    PY tools/apply_draft.py K041

It must print `applied`.

Do NOT run any other tool that writes (`propagate.py`, `strip_jp.py`, `build.py`, `extract_scenes.py`, `rowkeys.py`), do not edit the glossary files, the scene JSON by hand, or another scene's draft. Do not start emulators. Do not spawn sub-agents.

## Report (your final message)

At most 15 lines, no headings, no bold:

- line 1: scenes, rows you translated per scene, rows left empty (ids and why);
- then one line per name or term you met that is NOT in the glossary: `Japanese -> English (row)`. Do not list terms that are in the glossary;
- then at most 6 lines for the calls a reviewer most needs to re-check (row id + a few words): an inferred referent or direction, a stale speaker label, wordplay you could not keep, a meaning you are unsure of, a character voice you settled;
- a last line only if a tool failed.

Do not paste the script or Japanese sentences into the report.
