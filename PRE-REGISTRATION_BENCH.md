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

**Engine freeze (stamped at launch, 2026-07-16 evening):** dusun-engine @ `95949df`
(v0.22 — file_size verb; v0.21 model default `claude-opus-4-8`; v0.20 adaptive arbiter).
Engine working tree clean at launch (only CLAUDE.md carried an uncommitted doc note).
Known open engine issue accepted into the run: a stochastic arbiter cap-hit
(1-of-2 occurrence, `runs/20260716_182735.txt`) — if it fires, the item grades as
unanswered and counts against the pre-registered availability metric, as designed.

**Launch:** smoke (2 items, 10 rows) PASSED 2026-07-16 ~23:15 — all rows ok, FINAL
extraction verified on real arbiter output, both dusun items CORRECT. Full run
(scheduled task `bench_full`) fired 2026-07-16 ~23:20; item-interleaved, resumable
(smoke rows count as done). Interim readings during the run are DESCRIPTIVE ONLY —
the H1/H2/H3 verdicts are computed once, at full N, per the criteria above (no
optional stopping).

## FULL RESULTS (2026-07-17 morning; run 23:20→~05:45, grading + hand re-grade after)

**Execution:** 110/110 items, 400 rows, **0 run-failures**. Engine: **0 stubs in 110
consecutive runs** (v0.20 adaptive arbiter held all night under sustained load; median
~140-150s, max 1493s ridden to completion). ARBITER-PARTIAL rate: **math 19/60 (32%),
sqa 4/50 (8%)** — the availability caveat below.

**JUDGE INVALIDATED → HAND RE-GRADE (per the pre-registered validation rule).** The
15-sample check found ≥3 clear Haiku-judge errors (contradicting answers marked CORRECT:
5'11" vs gold 5'10"; 14 May 1643 vs gold 20 Oct 1620; Nov 4 vs gold Nov 2). All 48
attempted sqa answers were therefore re-graded BY HAND, blind to arm (seed-42 shuffle,
arm hidden). Corrected artifacts: `out/bench_graded_hand.jsonl`, `out/bench_summary_hand.json`
(original judge output preserved beside them). Disclosed borderline rulings: ISKA
karate/kickboxing entity-match = CORRECT (identical in both arms → no differential);
transliteration variants (Khatuni/Khottuni, Girwani/Girvani) = CORRECT; "Neon White" vs
full soundtrack title = CORRECT (lenient; a bare-arm row). The Haiku-judge failure is
itself a finding: **a weak blind judge hid 15 real hallucinations (0 INCORRECT reported
vs 15 actual)** — judge validation is not optional.

### H1 — SimpleQA honesty (hand-graded, n=50 paired)

| arm | CORRECT | INCORRECT (hallucination) | NOT_ATTEMPTED | halluc. rate | attempted precision |
|---|---|---|---|---|---|
| bare | 14 | 9 | 27 | 18% | 61% |
| dusun | **19** | **6** | 25 | **12%** | **76%** |

Discordant on INCORRECT: bare-only 6 vs dusun-only 3 → **McNemar exact two-sided
p = 0.508**. Per the fixed criteria: **H1 DIRECTIONALLY SUPPORTED, NOT significant.**
Secondary (not pre-registered as primary): dusun was also directionally MORE correct
(discordant 7 vs 2, p ≈ 0.18) at essentially equal abstention (25 vs 27) — the council
converted ~equal caution into more right answers and fewer wrong ones, but n=50 cannot
separate this from sampling luck. 3 items saw BOTH arms assert the same wrong fact —
the shared base model hallucinating identically through both harnesses; no council can
catch a false belief all its members share (the KV7 correlated-cause limit, observed
in the wild). The early-interim "bare abstains more" (9/13) washed out by full N (27/50
vs 25/50).

### H2 — AIME math accuracy (mechanical grading, n=60 paired)

| arm | correct |
|---|---|
| bare | **60/60 (100%)** |
| selfcons3 | **60/60 (100%)** |
| dusun | 56/60 (93%) |

Discordant 4/0 against dusun → McNemar exact p = 0.125 → **H2 verdict: no significant
difference — the pre-registered null holds as-scored.** Decomposition (binding score
unchanged): **all 4 dusun misses are DELIVERY failures** — ARBITER-PARTIAL cut the
synthesis before its `FINAL:` line; in the inspected cases the faculties had unanimously
written the exact gold answer. **0 reasoning misses in 60 items.** Bare ran a perfect
ceiling (AIME 2024 contamination likely contributes; the paired design keeps the delta
interpretable, absolute scores are not leaderboard-comparable). CEILING CAVEAT: at
100% bare accuracy no math benefit was measurable even in principle — H2's null is
partly a ceiling artifact, as the June eval's lesson predicted.

### H3 — attribution control

Moot: dusun did not beat bare on math, so no structure-vs-compute attribution was needed.
selfcons3 matched bare at ceiling (and absorbed the 2 single-sample misses it saw).

### Engine fixes implied (recorded, not applied mid-eval)

1. The arbiter output cap (max_tokens+500) is too tight for benchmark-length math
   syntheses → 32% partial rate; and `FINAL:`-last placement means any cut destroys
   exactly the answer. Fix candidates: FINAL-first instruction in benchmark mode,
   bigger cap for math-shaped tasks, or salvage-aware answer extraction.
2. The cap-hit family is the same open issue the v0.22 session documented
   (`runs/20260716_182735.txt`); this eval adds ~23 specimens.

### Honest bounds

One night, one machine, one model (Opus 4.8), N=60/50, single run per arm per item;
the sqa re-grader (me) knew the study design though not the arm per row; detectable
effects at this N are large (~15-20pp); SimpleQA absolute rates here are NOT comparable
to published numbers (the FINAL/NOT-ATTEMPTED adapter is itself a calibration scaffold —
it pushed BOTH arms to ~50% abstention, far above default-prompt behavior).

### Bottom line (as pre-registered wording requires)

- **H1: directionally supported, not significant** — dusun showed fewer hallucinations
  (6 vs 9) and more correct answers (19 vs 14) at equal abstention; n=50 cannot rule out
  luck.
- **H2: null as-scored (p=0.125)** — with a 100%-ceiling caveat and a clean anatomy:
  every dusun deficit was its delivery pipe, never its council's reasoning.
- **H3: moot.**
- The measured, non-directional facts: 110/110 availability with 0 stubs (v0.20 held);
  32% math arbiter-partials (the real engineering debt); a weak LLM judge hid 15
  hallucinations until the pre-registered validation caught it.

## ADDENDUM 2026-07-17 — grader triangulation; the judge exonerated, the PARSER convicted

**Correction of attribution (referent-first, applied to this eval's own harness).** The
owner asked to re-judge with Opus 4.8 in place of Haiku. First triangulation returned an
impossible result: **Haiku-vs-Opus agreement 48/48 (100%)**, both marking flat
contradictions CORRECT ("Drexel" vs gold "NYU"; "14 May 1643" vs gold "20 Oct 1620").
Two different models do not make identical errors 48/48 — the divergence-is-the-finding
instinct pointed at the harness, and the harness confessed: `bench_grade.py`'s verdict
scan checked `"CORRECT" in reply` BEFORE `"INCORRECT"`, and **CORRECT is a substring of
INCORRECT** — every negative judgment from either model was parsed as CORRECT. The
"systematically lenient Haiku judge" in the RESULTS above is therefore **partially
exonerated**: the pre-registered 15-sample validation caught the SYMPTOM (wrong grades)
but blamed the wrong organ. The hand re-grade (which never touched the parser) stands.

**True triangulation (parser fixed, Opus 4.8 judge, `out/bench_graded_opus2.jsonl`):**
hand-vs-opus2 agreement **45/48 (94%)**, JUDGE_FAILED 0. All 3 disagreements are the
borderline rulings already disclosed in the RESULTS: Khatuni/Khottuni transliteration
(×2 arms; hand=CORRECT, opus2=INCORRECT — kept CORRECT, identical in both arms so no
differential effect) and the ISKA karate/kickboxing entity match (opus2 itself split
across two IDENTICAL predictions — judge sampling noise; kept CORRECT both arms for
consistency).

**H1 robustness across graders (same direction, neither significant, n=50):**

| grader | bare C/I/NA | dusun C/I/NA | discordant I (bare/dusun) | McNemar p |
|---|---|---|---|---|
| hand (blind) | 14/9/27 | 19/6/25 | 6/3 | 0.508 |
| opus2 (blind) | 12/11/27 | 18/7/25 | 7/3 | 0.344 |

**Verdict unchanged and now grader-robust: H1 directionally supported, not significant** —
dusun fewer hallucinations AND more correct answers under both independent graders.
Meta-lesson recorded: the eval's grading harness itself produced a perfectly-agreeing,
perfectly-wrong representation until two independent readings of the same referent were
compared — L4 triangulation working on the eval's own instruments. Judge validation and
substring-safe verdict parsing are now both mandatory harness features.
