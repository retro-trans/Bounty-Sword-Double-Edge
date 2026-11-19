# Brief for a scene review agent (accuracy review, then editorial pass)

You review the already translated scenes named in your task (for example `K041 K042`) of the
PlayStation game Bounty Sword: Double Edge. Work only on those scenes. You run two stages, in
this order, over each scene: 1) accuracy review against the Japanese, 2) editorial pass over the
corrected English. Final proofreading is done later by someone else.

Python: Python 3.11+ (called `PY` below).
Run commands from `E:\Projects\Bounty Sword 2`. Set `PYTHONIOENCODING=utf-8` when a command prints
Japanese; prefer reading files with the Read tool.

## Read first

1. `BASE_RULES.md`: "When translating dialogue", "When translating any kind of text", and the review
   sections ("Review translated scripts in three stages...", "When reviewing translation accuracy",
   "When doing an editorial pass"). They are binding.
2. `docs/AGENT_BRIEF.md`: the translators' brief. Its text rules (quotes, `{n}`, tags, allowed
   characters, 3 lines, 240 px, 150 glyphs) and its story / voice section apply to you unchanged.
3. `work/glossary/speakers.json`, `work/glossary/terms.json`: approved spellings. Do not change a
   glossary name; if you think a glossary entry is wrong, report it.
4. `work/translation/en/review_todo.md`: open consistency items. Settle the ones that concern your
   scenes (say which in your report); the canonical choices written there are decided.

## Your input

    PY tools/slice_view.py K041

writes `work/source/dump/view_K041.txt`: `row id, block, kind, speaker | Japanese => English`.
Rows marked `(SKIP: copy of ...)` belong to another scene: read them for context, never edit them.
The English you edit is in `work/translation/en/drafts/K041.py` (`EN = {row index: text}`).

## Stage 1: accuracy

Read each scene in order with its neighbours, comparing English with Japanese: full meaning,
missing or added details, who speaks to whom, referents, restored subjects, emotional force,
insults and threats unsoftened, deliberate fragments and pauses. Fix wrong meaning in the draft.
Report the calls you were unsure of, even when you left the row as it is.

## Stage 2: editorial

Then read the corrected English of the whole scene again, in order, as an English reader. Fix
identifiable problems only: awkward or unclear phrasing, a line that does not sound spoken, a
broken character voice, inconsistent terms, wrong tone. Fix what is wrong; leave what is merely
different. Do not add explanations, invent details or soften. If an editorial change alters the
meaning, check it against the Japanese again.

## Editing and applying

Edit the draft entries with the Edit tool (keep the file's format; one row in, one row out; keep
every tag exactly). Then:

    PY tools/apply_draft.py K041 --dry

until it prints `problems 0`, then

    PY tools/apply_draft.py K041

which must print `applied`. Do NOT run any other tool that writes (`propagate.py`, `strip_jp.py`,
`build.py`, `fix_terms.py`, ...), do not edit scene JSON, glossary files or other scenes' drafts,
do not start emulators, do not spawn sub-agents.

## Report (your final message)

At most 20 lines, no headings:
- line 1: scenes, rows examined, rows edited (stage 1 / stage 2 counts);
- edited rows with a substantive meaning change: `row id: what was wrong` (one line each, at most 8);
- review_todo items you settled (short);
- uncertainties: row id + a few words (inferred referent, unclear source, voice decision);
- glossary entries you think are wrong.
Do not paste Japanese into the report.

## Settled conventions (from earlier review batches; follow them)

* Polite suffixes: Sera, Aerial, Faust and Tethys say "Mr. {hero:6}"; Faust says "Miss {name:6}"
  and "Miss Aerial"; Aerial says "Mr. Faust"; Ozunu says "Sir {hero:6}" / "Lady {name:6}".
  Sera drops the "Mr." suffix on monsters ("that zombie", not "Mr. Zombie").
* The Professor's catchphrase: "I'm a professor, you know!".
* Kane's insult for Sera: "old hag"; the milder form (others, or Kane softening): "old lady".
* Silent / speechless rows: exactly 6 dots ("......").
* Laius (the Slaughter Knight) is Kane's late father; Hector is Sera's husband.
* 重機 = heavy MG; Parsifal's title stays "Heavy Gunner".
