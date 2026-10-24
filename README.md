# dusun-eval

Evaluation harness and records for **TAHKIK / DUSUN**, a gated multi-perspective verification layer built on Claude (engine: `dusun-engine`, separate repository). Hypotheses, arms, metrics and grading rules are fixed in writing before any arm runs; results are appended below the line and never edited into the setup. Null results are recorded as outcomes.

## Start here

- `PRE-REGISTRATION_BENCH.md` — the paired benchmark of the real engine against bare Opus on the same model and items (AIME 2024/2025 math, SimpleQA factuality). Setup, then full results: 110 items, 400 rows, 0 run failures; SimpleQA hallucination 12% engine vs 18% bare at n=50 (McNemar p=0.51, directional, not significant); AIME within noise as predicted; the pooled n=139 power run and why it stopped; the blind-judge failure that hid 15 hallucinations and the hand re-grade that followed.
- `out/bench_summary_hand.json`, `out/pow_pooled_grades.json` — graded results. Original judge outputs are kept beside the corrected ones.
- `bench_runner.py`, `bench_grade.py`, `bench_bank.py` — runner, grader and bank builder. Items come from public benchmark releases (SimpleQA, AIME via Hugging Face); absolute scores are not comparable to leaderboards, only the paired deltas are interpreted.

The Referent Gate's own pre-registration lives in the engine repository (`dusun-engine/eval/PRE-REGISTRATION_REFGATE.md`).

Earlier files (`bank*.jsonl`, `hard*.py`, `screen.py`, `common.py`, `out/summary.json`) belong to the June 2026 single-call evaluation, which came back at ceiling on every arm and is superseded by the benchmark above.
