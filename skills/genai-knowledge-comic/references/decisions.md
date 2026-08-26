# Design decisions and rationale

Background for the fixed choices baked into `SKILL.md`. Read this if you want to understand
*why* something is fixed rather than asked interactively — not required to actually run the skill.

## Why a thin wrapper around baoyu-comic, instead of a standalone skill

The team already has a working, general-purpose comic-generation skill (`baoyu-comic`) and wants
to keep using it unmodified. Re-implementing comic generation here would duplicate a lot of
logic and drift out of sync every time `baoyu-comic` improves. Instead, this skill supplies a
fixed set of decisions (art style, cast, backend policy) and invokes `baoyu-comic` through the
normal `Skill` tool interface for everything else, trusting its own defaults wherever this skill
has no genuine reason to override them (see "Why output stays at baoyu-comic's own default
location" below for a case where an earlier version of this skill got that balance wrong). It
never reads or depends on `baoyu-comic`'s internal files directly — if `baoyu-comic`'s internal
implementation changes, this skill keeps working as long as `baoyu-comic` itself still exists and
is invokable.

## Why the shared cast is fixed rather than generated per-story

Without a fixed cast, every new comic reinvents character designs, and the same "new hire" or
"generative AI" character ends up looking different across stories, which undermines the sense
that these comics are a single ongoing series. Two genders per human role (newcomer/employee/
manager) exist specifically so that scenes comparing two people in the same position (e.g. "person A
vs person B") can tell them apart at a glance without relying on labels.

The two robot mascots are deliberately drawn as a contrast pair: rounded/organic/glowing-eyed
for the generative-AI character vs. boxy/mechanical/fixed-display for the legacy rule-based
system, so a reader can tell which is which even in a small panel with no dialogue. Their names
went through a couple of rounds of feedback (first informal, then literal) — see
`assets/characters/prompts/00-characters-sheet.md` for the full naming history — landing on
plainly descriptive names ("generative AI" / "logic") since more playful names were reported as
unclear about what they represent.

## Why output stays at baoyu-comic's own default location (`comic/{topic-slug}/`)

An earlier version of this skill redirected output to a dedicated location
(`.agents/state/genai-knowledge-comic/outputs/`), reasoning that this skill's output should read
as a distinct, ongoing series, separated from ad-hoc `baoyu-comic` usage. That was reverted after
review: `baoyu-comic` is an instruction-based skill with no formal "output location" parameter —
overriding it only works because the executing agent happens to prioritize this skill's `args`
text over baoyu-comic's own stated default. That's not a guarantee, and it directly contradicts
this skill's own stated principle of trusting baoyu-comic's instructions once invoked. The
separation this override bought was a nice-to-have, not a requirement, so it was dropped in favor
of reliability: this skill now always lets `baoyu-comic` use its own default location.

## Why the image-generation backend has a hard fallback instead of asking every time

Most people who would ask for one of these comics do not have an image-generation API key
configured. Asking the same question every single time would be repetitive friction. Checking
Codex CLI availability up front and falling back to a prompts-only + "paste into ChatGPT"
result when it's unavailable means the skill still produces a complete, usable deliverable
(the story, the panel breakdown, the exact image prompts) even with zero image-generation
infrastructure on the machine.

## Known operational limitations (found via testing)

- **Concurrency**: `codex-cli` generation shares a single lock file on the machine. Running many
  generations from this skill at the same time (e.g. several people, or several parallel test
  runs) causes lock contention and incomplete pages. Prefer generating one comic at a time on a
  given machine.
- **Topic-slug collisions**: the output folder name is derived from story content. Two
  requests on a similar topic run around the same time can land on the same folder name and
  overwrite each other. See the "Collision safety" note in `SKILL.md`.
- **Sandboxed environments may block the filename `analysis.md`**: some tool permission setups
  refuse to create a file with that exact name. `SKILL.md` specifies `content-brief.md` as the
  standard substitute so this doesn't produce inconsistent ad-hoc names across runs.
