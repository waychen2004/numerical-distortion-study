# Data Dictionary

## Corpus manifest

`study_data/02_frozen_corpus/corpus_manifest_2000.jsonl`

- `pmid`: PubMed identifier.
- `title`: publication title.
- `year`: publication year.
- `abstract_sha256`: SHA-256 of the exact abstract text used in the experiment.
- `abstract_characters`: character count of that exact abstract.

The public file deliberately omits the `abstract` field.

## Source-fact ledger

`study_data/02_frozen_corpus/canonical_source_fact_ledger_16715.jsonl`

- `pmid`: PubMed identifier.
- `source_count`: de-duplicated source-fact groups used by the original automated denominator.
- `source_mentions`: numerical mentions before grouping.
- `full_record_sha256`: SHA-256 of the original internal ledger record, which included extracted contexts.

## Model outputs

Each `outputs.jsonl` contains:

- `run_id`, `model`, `arm`, `pmid`, `timestamp`: run provenance.
- `llm_output`: original visible model output.
- `truncated`, `llm_error`: completion flags.
- `source_abstract_sha256`: hash linking the output to the exact source manifest record.

The duplicated `source_abstract` field is omitted.

## Codex adjudications

Each `reviews.jsonl` contains task-level `verdict` and event-level `direction`, `mechanism`, `severity`, `substantive`, `primary_scope`, `source_fact_failure`, and `source_category`. Chinese free-text rationales and evidence snippets are omitted from the English-only public records.

## Human review

`reviewer_A_final_ratings.csv` and `reviewer_B_final_ratings.csv` each contain 1,347 unique `blind_id` records. The 1,200 `random_10pct` records retain reviewer-specific ratings. The 147 `census_sev_ge3` records contain shared post-review final labels and are not used as independent A/B observations.

- `verdict`, `substantive`, and `max_severity`: final structured human ratings.
- `E`: syntax-normalized reviewer-declared E01-E10 codes. No semantic correction was applied.
- `direction`: English labels produced by the fixed mapping `alteration`, `omission`, `fabrication`, and `binding`.
- `E_normalization_status`: whether a code was parsed, explicitly absent, or omitted because the original free text did not contain a parseable code.

Chinese human-review notes are omitted from this English-only release.

## Missing values

Blank `E` or `direction` fields indicate no declared code or direction. See `E_normalization_status` before interpreting a blank E field. Verdict, substantive status, and severity were not inferred or filled.
