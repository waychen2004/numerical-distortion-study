# Numerical Distortion in Medical LLM Source-to-Structure Transformation

Public-release package for a six-model study of numerical distortion during transformation of biomedical abstracts into structured records.

## Contents

- `study_data/01_study_design`: model prompt, English translation of the Codex adjudication prompt, output schema, E01-E10 taxonomy, and E06 rule.
- `study_data/02_frozen_corpus`: 2,000 PMID records, abstract SHA-256 hashes, corpus sampling metadata, and source-fact counts.
- `study_data/03_model_outputs`: 12,000 model outputs and run metadata. Repeated source abstract text was removed.
- `study_data/04_codex_adjudications`: 12,000 structured adjudication records and run metadata.
- `study_data/05_summary_statistics`: frozen summary statistics from the original study package.
- `study_data/06_human_review`: final Reviewer A and B structured ratings, blinded-material identifiers and outputs, and English translations of review instructions.
- `study_data/08_derived_corpus_features`: corpus-level and document-level derived descriptors.
- `analysis`: scripts for locked manuscript analyses, revision analyses, Codex-level statistics, source retrieval, and release verification.

## Important scope

This repository contains no private clinical records or newly collected patient-level data. Source documents were publicly indexed PubMed abstracts. Full abstract text is not redistributed here. Each source is represented by PMID, bibliographic metadata, and the SHA-256 hash of the exact abstract used during the experiment. The exact PMID set can be re-fetched from NCBI with `analysis/fetch_pubmed_abstracts.py`; later PubMed corrections may cause hash differences.

Model outputs are preserved exactly except that the duplicated `source_abstract` field was removed and replaced with `source_abstract_sha256`. Structured Codex adjudication labels and human ratings are retained. Chinese free-text adjudication rationales and human notes are omitted from this English-only release. Human direction labels were translated through a fixed mapping, and declared E labels were syntax-normalized to E01-E10 codes without semantic reclassification. See `PUBLIC_RELEASE_TRANSFORMATIONS.md`.

## Reproduce analyses

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./reproduce.sh
```

Generated files are written under `analysis/derived/`. The reproduction scripts use the released model outputs, adjudications, final human ratings, and frozen sampling metadata. They do not call any commercial LLM API.

## Verify release safety and integrity

```bash
python3 analysis/verify_release.py
```

The verifier checks record counts, PMID coverage, omission of full abstract fields, human-table completeness, files larger than GitHub's 100 MB limit, local paths, personal email addresses, and common credential patterns.

`FILE_MANIFEST.csv` lists released files, sizes, and SHA-256 values. `SHA256SUMS.txt` supports direct integrity checking with `shasum -a 256 -c SHA256SUMS.txt`.

## Source retrieval

```bash
python3 analysis/fetch_pubmed_abstracts.py \
  --manifest study_data/02_frozen_corpus/corpus_manifest_2000.jsonl \
  --output rehydrated_pubmed_abstracts.jsonl \
  --email YOUR_EMAIL@example.org
```

An NCBI API key is optional and must be supplied only through `NCBI_API_KEY`. No credential is stored in this repository.

## Publication status

Repository URL, archived release DOI, authors, citation, and licences remain author decisions. Complete `LICENSE_DECISION_REQUIRED.md` before making the repository public. GitHub should be paired with an archived release such as Zenodo for a persistent DOI.
