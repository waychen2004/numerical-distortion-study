#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DATA="$ROOT/study_data"

python3 "$ROOT/analysis/derive_locked_results.py" --study-root "$DATA"
python3 "$ROOT/analysis/posthoc_exclude_retained500.py" \
  --study-root "$DATA" \
  --construction-manifest "$DATA/02_frozen_corpus/corpus_construction_manifest.json"
python3 "$ROOT/analysis/derive_revision_analyses.py" --study-root "$DATA"
python3 "$ROOT/analysis/recompute_codex_statistics.py" \
  --runs-root "$DATA/03_model_outputs" \
  --blind-root "$DATA/04_codex_adjudications" \
  --corpus "$DATA/02_frozen_corpus/corpus_manifest_2000.jsonl" \
  --ledger "$DATA/02_frozen_corpus/canonical_source_fact_ledger_16715.jsonl" \
  --output-dir "$ROOT/analysis/derived/codex_statistics"

python3 "$ROOT/analysis/verify_release.py"
