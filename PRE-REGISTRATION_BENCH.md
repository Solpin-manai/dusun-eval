بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ

# PRE-REGISTRATION — the REAL-ENGINE benchmark eval (bare 4.8 vs dusun 4.8)

**Written BEFORE running any arm** (2026-07-16, evening). Codex empirical-layer
discipline: hypotheses, arms, metrics, extraction and grading rules are fixed here;
results are appended below the line, never edited into the setup. H-unsupported is a
recordable outcome — the corpus already carries honest falsifications.

## What is new about this eval (honesty about the June eval)

The June 4-arm eval (`common.py`) tested the **risalian-operator hook line** as a system
prompt on single Haiku calls — NOT the engine. Its `out/summary.json` came back at
**ceiling on every arm** (K/R/M ≈ 1.0, F = 0.0 for all four arms): the bank was too easy
to discriminate anything. This eval fixes both limitations: the **dusun arm is the real
engine** (`py dusun_engine.py --n 3`, the full council: classifier → 3 isolated faculties
→ adversary → arbiter → mechanical gate), and the items are benchmarks with measured
headroom for frontier models (AIME 2024+2025 math; SimpleQA factuality).

## The claims under test

- **H1 (honesty axis, where the engine SHOULD win):** on SimpleQA-style short factual
  questions, the engine produces a **lower confident-hallucination rate** than bare
  Opus 4.8 — it abstains (NOT ATTEMPTED) where bare answers wrongly. Metric: INCORRECT
  rate (overall) and INCORRECT / (CORRECT+INCORRECT) among attempted.
- **H2 (accuracy axis, pre-registered NULL expectation):** on AIME math accuracy, the
  engine is **within noise of bare** Opus 4.8 (prediction: the arbiter's synthesis does
  not beat a single direct solve; it may cost a little). If dusun WINS here at N=60,
  that is a surprise finding worth its own follow-up; if it LOSES badly, that is a real
  cost of the apparatus and gets recorded as such.
- **H3 (attribution control):** any dusun gain over bare on math must ALSO beat
  **selfcons3** (3 bare samples, majority) to be attributed to *structure* rather than
  *more compute*. selfcons3 runs on math only (compute-matching matters where a
  reasoning gain would be claimed; on SimpleQA extra samples mostly re-sample the same
  knowledge).

**What this eval does NOT test:** the Referent Gate (`--ppass/--refgate` stay OFF —
benchmark facts are not observable by the engine's filesystem-only tool verbs). This
tests the COUNCIL. The gate's own eval is `dusun-engine/eval/PRE-REGISTRATION_REFGATE.md`.

## Arms (all on the SAME model — the paired design cancels model knowledge)

| arm | what runs | items |
|---|---|---|
| **bare** | one `claude -p --model claude-opus-4-8` (lean boot, no tools) | all 110 |
| **selfcons3** | 3 independent bare samples; majority vote at grade time (tie → first sample) | math 60 |
| **dusun** | the REAL engine: `py dusun_engine.py --n 3 "<item>"` — engine default model (4.8, v0.21) | all 110 |

Runner: `bench_runner.py`, item-interleaved (bare → selfcons ×3 → dusun per item) so all
arms sample the same hours of Max-throttle state; incremental + resumable; kill file
`bench_data/BENCH_KILL`; every failure recorded as a row, never dropped.

## Items (bench_bank.jsonl, built by bench_bank.py, seed 20260716)

- **math (60):** AIME 2025 I+II (30, `math-ai/aime25`) + AIME 2024 I+II (30,
  `Maxwell-Jia/AIME_2024`). Integer answers 0-999 → mechanical exact-match grading.
  Contamination note: AIME 2024 (and possibly 2025) may be in training data — but the
  paired same-model design means contamination inflates ALL arms equally; the deltas
  remain interpretable. Absolute scores are NOT comparable to published leaderboards.
- **sqa (50):** SimpleQA test set (OpenAI public blob, 4326 rows), stratified by topic,
  deterministic seed. Judge: SimpleQA rubric (CORRECT / INCORRECT / NOT_ATTEMPTED).

Adapter (identical for every arm, appended to the item): math items must end with
`FINAL: <integer>`; sqa items must end with `FINAL: <answer>` or `FINAL: NOT ATTEMPTED`.
Abstention is therefore first-class for BOTH arms — the comparison is fair.

## Extraction + grading rules (fixed now)

- FINAL is taken as the LAST `FINAL:` line — for the **dusun arm, searched ONLY within
  the ARBITER section** of the run output (faculties may emit their own FINAL lines;
  attributing a faculty's answer to the engine would mis-grade). No FINAL in the arbiter
  section → unanswered (math: INCORRECT; sqa: NOT_ATTEMPTED).
- An arbiter STUB (`Arbiter unavailable`) or run failure → same unanswered rule, and the
  failure is reported separately as an availability metric (failures are not silently
  ignored; they are part of the engine's real-world score).
- Math grading: integer exact-match (`norm_int`), no judge.
- SQA grading: blind judge (`claude -p`, Haiku 4.5) sees question/gold/prediction only —
  never the arm. Judge validation: the owner (or a second model) hand-checks 15 random
  judgments; if >2 disagree, all sqa grades are re-examined before any conclusion.

## Success/failure criteria (decided now)

- **H1 SUPPORTED** iff dusun's sqa INCORRECT count is lower than bare's with a two-sided
  McNemar exact p < 0.05 on the paired items; **directionally supported** (reported as
  such, not as significant) if lower but p ≥ 0.05.
- **H2:** report the paired math delta with McNemar exact p. The PREDICTION is no
  significant difference; any p < 0.05 result in either direction is a finding.
- **H3:** dusun > bare on math counts as a structure effect ONLY if dusun > selfcons3 too.
- **INCONCLUSIVE** per class if engine availability (non-stub completion rate) < 80% —
  an environment verdict, not an H verdict. Reported as such.

## Threats to validity (named up front — ahfâ)

- **Power:** N=60/50 detects only large deltas (~15-20pp at α=0.05). This is a
  mechanism-scale eval, not a leaderboard.
- **One night's throttle state** — mitigated by item-interleaving, not eliminated.
- **The dusun arm costs ~6-8× the calls of bare** even before selfcons; a null on H2 is
  therefore also a cost-effectiveness verdict.
- **Judge is a Claude model grading Claude outputs** — mitigated by blind rubric +
  hand-validation sample; not eliminated.
- **The engine's answers are essays** — the FINAL adapter suppresses part of the gate's
  refusal style on math (forced choice); sqa keeps abstention honest for both arms.
- **Engine version freeze:** the exact dusun-engine commit hash is recorded in the
  RESULTS header at launch; the engine is not edited mid-run.

---
## RESULTS (appended after running — DO NOT edit the above)

(pending)
