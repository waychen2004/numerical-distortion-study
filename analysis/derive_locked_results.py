#!/usr/bin/env python3
"""Derive manuscript-locked task-level results from frozen study inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from scipy.stats import hypergeom


STAGE = Path(__file__).resolve().parent
PACKAGE_ROOT = STAGE.parent
DEFAULT_DATA = PACKAGE_ROOT / "study_data"
OUT = STAGE / "derived"
EXPECTED_TASKS = 2_000
E_CODES = [f"E{i:02d}" for i in range(1, 11)]

RUNS = {
    "G": ("aliyun/glm-5.2", "GLM-5.2", "aliyun_glm52_extract_2000_20260817"),
    "H": ("aliyun/deepseek-v4-pro", "DeepSeek V4 Pro", "aliyun_deepseek_v4_pro_extract_2000_20260817"),
    "I": ("aliyun/deepseek-v4-flash", "DeepSeek V4 Flash", "aliyun_deepseek_v4_flash_extract_2000_20260817"),
    "J": ("aliyun/qwen3.7-max", "Qwen 3.7 Max", "aliyun_qwen37max_extract_2000_20260817"),
    "K": ("aliyun/kimi-k2.6", "Kimi K2.6", "aliyun_kimi_k2_6_extract_2000_20260817"),
    "L": ("aliyun/qwen3.8-max", "Qwen 3.8 Max", "aliyun_qwen38max_extract_2000_20260817"),
}
MODEL_ORDER = [model for model, _, _ in RUNS.values()]
DISPLAY = {model: display for model, display, _ in RUNS.values()}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty output: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wilson(successes: float, total: int) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("Wilson interval requires a positive denominator")
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return center - half, center + half


def finite_population_exact_total_ci(
    sample_successes: int,
    sample_size: int,
    population_size: int,
    alpha: float = 0.05,
) -> tuple[int, int]:
    """Invert the hypergeometric distribution for the finite-population total."""
    minimum = sample_successes
    maximum = population_size - (sample_size - sample_successes)
    candidates = range(minimum, maximum + 1)
    lower = minimum
    for total_successes in candidates:
        if hypergeom.sf(sample_successes - 1, population_size, total_successes, sample_size) >= alpha / 2:
            lower = total_successes
            break
    upper = maximum
    for total_successes in range(maximum, minimum - 1, -1):
        if hypergeom.cdf(sample_successes, population_size, total_successes, sample_size) >= alpha / 2:
            upper = total_successes
            break
    return lower, upper


def binary_metrics(reference: list[bool], candidate: list[bool]) -> dict:
    if len(reference) != len(candidate) or not reference:
        raise ValueError("Binary metric vectors must be paired and non-empty")
    tp = sum(r and c for r, c in zip(reference, candidate))
    tn = sum((not r) and (not c) for r, c in zip(reference, candidate))
    fp = sum((not r) and c for r, c in zip(reference, candidate))
    fn = sum(r and (not c) for r, c in zip(reference, candidate))
    n = tp + tn + fp + fn
    po = (tp + tn) / n
    pa = (tp + fn) / n
    pb = (tp + fp) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return {
        "n": n,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "overall_agreement": po,
        "positive_agreement": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "negative_agreement": 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else None,
        "cohen_kappa": (po - pe) / (1 - pe) if pe != 1 else 1.0,
    }


def weighted_binary_metrics(reference: list[bool], candidate: list[bool], weights: list[float]) -> dict:
    if len(reference) != len(candidate) or len(reference) != len(weights) or not reference:
        raise ValueError("Weighted binary metric vectors must be aligned and non-empty")
    tp = sum(w for r, c, w in zip(reference, candidate, weights) if r and c)
    tn = sum(w for r, c, w in zip(reference, candidate, weights) if not r and not c)
    fp = sum(w for r, c, w in zip(reference, candidate, weights) if not r and c)
    fn = sum(w for r, c, w in zip(reference, candidate, weights) if r and not c)
    n = tp + tn + fp + fn
    po = (tp + tn) / n
    pa = (tp + fn) / n
    pb = (tp + fp) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return {
        "weighted_n": n,
        "weighted_tp": tp,
        "weighted_tn": tn,
        "weighted_fp": fp,
        "weighted_fn": fn,
        "overall_agreement": po,
        "positive_agreement": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "negative_agreement": 2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else None,
        "cohen_kappa": (po - pe) / (1 - pe) if pe != 1 else 1.0,
    }


def event_e_code(event: dict) -> str:
    direct = {
        "decimal_shift": "E01",
        "digit_transposition": "E02",
        "unit": "E03",
        "threshold_precision": "E04",
        "threshold_omission": "E05",
        "qualitative_to_numeric": "E06",
        "derived_numeric": "E06",
        "sign": "E07",
        "comparator": "E08",
        "range": "E09",
        "binding": "E10",
    }
    mechanism = event["mechanism"]
    if mechanism in direct:
        return direct[mechanism]
    return {
        "alteration": "E04",
        "omission": "E05",
        "fabrication": "E06",
        "binding": "E10",
    }[event["direction"]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--study-root",
        type=Path,
        default=DEFAULT_DATA,
        help="Frozen study-data root (default: sibling of the writing directory).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = args.study_root.expanduser().resolve()
    if not data.is_dir():
        raise FileNotFoundError(f"Study root does not exist: {data}")
    OUT.mkdir(parents=True, exist_ok=True)

    corpus_path = data / "02_frozen_corpus/corpus_manifest_2000.jsonl"
    corpus = read_jsonl(corpus_path)
    corpus_pmids = {str(row["pmid"]) for row in corpus}
    if len(corpus) != EXPECTED_TASKS or len(corpus_pmids) != EXPECTED_TASKS:
        raise ValueError("Frozen corpus must contain 2,000 unique PMIDs")

    manifest_paths = [
        corpus_path,
        data / "01_study_design/model_extraction_prompt.txt",
        data / "01_study_design/codex_adjudication_prompt_english_translation.txt",
        data / "01_study_design/numerical_distortion_taxonomy_E01-E10.md",
        data / "01_study_design/codex_adjudication_output_schema.json",
        data / "03_model_outputs/model_run_metadata.json",
        data / "04_codex_adjudications/adjudication_run_metadata.json",
        data / "06_human_review/human_review_operating_manual_v2_20260818_english_translation.md",
        data / "06_human_review/blinded_review_materials.csv",
        data / "06_human_review/reviewer_A_final_ratings.csv",
        data / "06_human_review/reviewer_B_final_ratings.csv",
    ]

    review_by_model: dict[str, list[dict]] = {}
    review_by_key: dict[tuple[str, str], dict] = {}
    candidate_rows = []
    taxonomy_rows = []
    high_counts: dict[str, int] = {}

    for letter, (model, display, output_dir) in RUNS.items():
        output_path = data / f"03_model_outputs/{output_dir}/outputs.jsonl"
        review_path = data / f"04_codex_adjudications/run_{letter}_2000_20260817/reviews.jsonl"
        manifest_paths.extend([output_path, review_path])

        outputs = read_jsonl(output_path)
        reviews = read_jsonl(review_path)
        if len(outputs) != EXPECTED_TASKS or len(reviews) != EXPECTED_TASKS:
            raise ValueError(f"Incomplete model or review run: {letter}")
        output_pmids = {str(row["pmid"]) for row in outputs}
        review_pmids = {str(row["pmid"]) for row in reviews}
        if output_pmids != corpus_pmids or review_pmids != corpus_pmids:
            raise ValueError(f"PMID coverage mismatch: {letter}")
        if any(not row.get("llm_output") or row.get("llm_error") or row.get("truncated") for row in outputs):
            raise ValueError(f"Failed, empty, or truncated output in run {letter}")

        review_by_model[model] = reviews
        strict_tasks: set[str] = set()
        substantive_tasks: set[str] = set()
        high_tasks: set[str] = set()
        task_codes: dict[str, set[str]] = defaultdict(set)
        primary_events = Counter()
        substantive_events = Counter()

        for review in reviews:
            pmid = str(review["pmid"])
            review_by_key[(model, pmid)] = review
            primary = [event for event in review["events"] if event["primary_scope"]]
            substantive = [event for event in primary if event["substantive"]]
            high = [event for event in primary if int(event["severity"]) >= 3]
            if primary:
                strict_tasks.add(pmid)
            if substantive:
                substantive_tasks.add(pmid)
            if high:
                high_tasks.add(pmid)
            for event in primary:
                primary_events[event_e_code(event)] += 1
            for event in substantive:
                code = event_e_code(event)
                substantive_events[code] += 1
                task_codes[pmid].add(code)

        high_counts[model] = len(high_tasks)
        strict_ci = wilson(len(strict_tasks), EXPECTED_TASKS)
        substantive_ci = wilson(len(substantive_tasks), EXPECTED_TASKS)
        high_ci = wilson(len(high_tasks), EXPECTED_TASKS)
        candidate_rows.append(
            {
                "model": display,
                "model_id": model,
                "tasks": EXPECTED_TASKS,
                "primary_candidate_tasks": len(strict_tasks),
                "primary_candidate_rate": len(strict_tasks) / EXPECTED_TASKS,
                "primary_candidate_ci_low": strict_ci[0],
                "primary_candidate_ci_high": strict_ci[1],
                "substantive_candidate_tasks": len(substantive_tasks),
                "substantive_candidate_rate": len(substantive_tasks) / EXPECTED_TASKS,
                "substantive_candidate_ci_low": substantive_ci[0],
                "substantive_candidate_ci_high": substantive_ci[1],
                "codex_flagged_severity_ge3_tasks": len(high_tasks),
                "codex_flagged_severity_ge3_rate": len(high_tasks) / EXPECTED_TASKS,
                "codex_flagged_severity_ge3_ci_low": high_ci[0],
                "codex_flagged_severity_ge3_ci_high": high_ci[1],
                "primary_events_supplementary": sum(primary_events.values()),
                "substantive_events_supplementary": sum(substantive_events.values()),
            }
        )
        for code in E_CODES:
            task_count = sum(code in codes for codes in task_codes.values())
            taxonomy_rows.append(
                {
                    "model": display,
                    "model_id": model,
                    "E_code": code,
                    "tasks_with_substantive_candidate": task_count,
                    "task_rate": task_count / EXPECTED_TASKS,
                    "primary_events_supplementary": primary_events[code],
                    "substantive_events_supplementary": substantive_events[code],
                }
            )

    humans: dict[str, list[dict]] = {}
    for rater in ["A", "B"]:
        rows = read_csv(data / f"06_human_review/reviewer_{rater}_final_ratings.csv")
        if len(rows) != 1_347 or len({row["blind_id"] for row in rows}) != 1_347:
            raise ValueError(f"Rater {rater} must contain 1,347 unique records")
        for row in rows:
            if row["model"] not in MODEL_ORDER:
                raise ValueError(f"Unknown model in human file: {row['model']}")
            if row["verdict"] not in {"no_error", "strict_contract_error"}:
                raise ValueError(f"Invalid verdict: {rater}/{row['blind_id']}")
            if row["substantive"] not in {"yes", "no"}:
                raise ValueError(f"Invalid substantive label: {rater}/{row['blind_id']}")
            if row["max_severity"] not in {"0", "1", "2", "3", "4"}:
                raise ValueError(f"Invalid severity: {rater}/{row['blind_id']}")
            if row["verdict"] == "no_error" and (row["substantive"] != "no" or row["max_severity"] != "0"):
                raise ValueError(f"Inconsistent no-error row: {rater}/{row['blind_id']}")
            if row["substantive"] == "yes" and row["max_severity"] == "0":
                raise ValueError(f"Substantive error cannot have severity 0: {rater}/{row['blind_id']}")

            review = review_by_key[(row["model"], row["pmid"])]
            primary = [event for event in review["events"] if event["primary_scope"]]
            codex_max = max([int(event["severity"]) for event in primary] or [0])
            expected_stratum = "census_sev_ge3" if codex_max >= 3 else "random_10pct"
            if row["stratum"] != expected_stratum:
                raise ValueError(f"Stratum mismatch: {rater}/{row['blind_id']}")
            row["human_strict"] = row["verdict"] == "strict_contract_error"
            row["human_substantive"] = row["substantive"] == "yes"
            row["human_high"] = int(row["max_severity"]) >= 3
            row["codex_strict"] = bool(primary)
            row["codex_substantive"] = any(event["substantive"] for event in primary)
            row["codex_high"] = codex_max >= 3
        humans[rater] = rows

    a_by_id = {row["blind_id"]: row for row in humans["A"]}
    b_by_id = {row["blind_id"]: row for row in humans["B"]}
    if set(a_by_id) != set(b_by_id):
        raise ValueError("Human reviewer blind_id sets differ")
    for blind_id in a_by_id:
        for field in ["pmid", "model", "stratum"]:
            if a_by_id[blind_id][field] != b_by_id[blind_id][field]:
                raise ValueError(f"Human reviewer metadata mismatch: {blind_id}/{field}")

    consensus_fields = ["verdict", "substantive", "max_severity", "E", "direction"]
    high_consensus_by_id = {}
    for blind_id, a_row in a_by_id.items():
        if a_row["stratum"] != "census_sev_ge3":
            continue
        b_row = b_by_id[blind_id]
        if any(a_row[field] != b_row[field] for field in consensus_fields):
            raise ValueError(f"Higher-severity consensus mismatch: {blind_id}")
        high_consensus_by_id[blind_id] = a_row

    human_estimates = []
    for rater in ["A", "B"]:
        for model in MODEL_ORDER:
            model_rows = [row for row in humans[rater] if row["model"] == model]
            low = [row for row in model_rows if row["stratum"] == "random_10pct"]
            high = [row for row in model_rows if row["stratum"] == "census_sev_ge3"]
            if len(low) != 200 or len(high) != high_counts[model]:
                raise ValueError(f"Unexpected stratum sizes: {rater}/{model}")
            n_low_population = EXPECTED_TASKS - len(high)
            for outcome, field in [
                ("strict", "human_strict"),
                ("substantive", "human_substantive"),
                ("severity_ge3", "human_high"),
            ]:
                y_low = sum(row[field] for row in low)
                y_high = sum(row[field] for row in high)
                low_total_ci = finite_population_exact_total_ci(
                    y_low,
                    len(low),
                    n_low_population,
                )
                estimated_count = n_low_population * y_low / len(low) + y_high
                human_estimates.append(
                    {
                        "rater": rater,
                        "model": DISPLAY[model],
                        "model_id": model,
                        "outcome": outcome,
                        "low_population": n_low_population,
                        "low_sample": len(low),
                        "low_positive": y_low,
                        "low_source": f"reviewer_{rater}_independent",
                        "codex_flagged_high_census": len(high),
                        "high_positive": y_high,
                        "high_source": "post_review_consensus",
                        "stratified_estimated_tasks": estimated_count,
                        "stratified_estimated_rate": estimated_count / EXPECTED_TASKS,
                        "stratified_ci_low": (low_total_ci[0] + y_high) / EXPECTED_TASKS,
                        "stratified_ci_high": (low_total_ci[1] + y_high) / EXPECTED_TASKS,
                        "ci_method": "exact hypergeometric inversion for sampled finite low stratum; high stratum fixed census",
                    }
                )

    agreement_rows = []
    validation_rows = []
    random_ids = sorted(
        blind_id for blind_id, row in a_by_id.items() if row["stratum"] == "random_10pct"
    )
    for outcome, field in [("strict", "human_strict"), ("substantive", "human_substantive"), ("severity_ge3", "human_high")]:
        metrics = binary_metrics(
            [a_by_id[blind_id][field] for blind_id in random_ids],
            [b_by_id[blind_id][field] for blind_id in random_ids],
        )
        agreement_rows.append(
            {"comparison": "A_vs_B", "stratum": "random_10pct_independent", "outcome": outcome, **metrics}
        )

    for rater, by_id in [("A", a_by_id), ("B", b_by_id)]:
        for outcome, human_field, codex_field in [
            ("strict", "human_strict", "codex_strict"),
            ("substantive", "human_substantive", "codex_substantive"),
            ("severity_ge3", "human_high", "codex_high"),
        ]:
            metrics = binary_metrics(
                [by_id[blind_id][human_field] for blind_id in random_ids],
                [by_id[blind_id][codex_field] for blind_id in random_ids],
            )
            validation_rows.append(
                {"comparison": f"Codex_vs_{rater}", "stratum": "random_10pct_independent", "outcome": outcome, **metrics}
            )

    high_consensus = list(high_consensus_by_id.values())
    severity_rows = [
        {
            "assessment_source": "post_review_consensus",
            "codex_flagged_high_census_n": len(high_consensus),
            "human_strict_confirmed": sum(row["human_strict"] for row in high_consensus),
            "human_substantive_confirmed": sum(row["human_substantive"] for row in high_consensus),
            "human_severity_ge3_confirmed": sum(row["human_high"] for row in high_consensus),
            "random_lower_severity_sample_n": "",
            "human_severity_ge3_found_in_random_layer": "",
        }
    ]
    for rater in ["A", "B"]:
        low = [row for row in humans[rater] if row["stratum"] == "random_10pct"]
        severity_rows.append(
            {
                "assessment_source": f"reviewer_{rater}_independent",
                "codex_flagged_high_census_n": "",
                "human_strict_confirmed": "",
                "human_substantive_confirmed": "",
                "human_severity_ge3_confirmed": "",
                "random_lower_severity_sample_n": len(low),
                "human_severity_ge3_found_in_random_layer": sum(row["human_high"] for row in low),
            }
        )

    weighted_agreement_rows = []
    weighted_ids = sorted(a_by_id)
    row_weights = []
    for blind_id in weighted_ids:
        row = a_by_id[blind_id]
        if row["stratum"] == "census_sev_ge3":
            row_weights.append(1.0)
        else:
            row_weights.append((EXPECTED_TASKS - high_counts[row["model"]]) / 200)
    for outcome, human_field, codex_field in [
        ("strict", "human_strict", "codex_strict"),
        ("substantive", "human_substantive", "codex_substantive"),
        ("severity_ge3", "human_high", "codex_high"),
    ]:
        for rater, by_id in [("A", a_by_id), ("B", b_by_id)]:
            metrics = weighted_binary_metrics(
                [by_id[blind_id][human_field] for blind_id in weighted_ids],
                [by_id[blind_id][codex_field] for blind_id in weighted_ids],
                row_weights,
            )
            weighted_agreement_rows.append(
                {
                    "comparison": f"Codex_vs_{rater}_random_plus_high_consensus",
                    "outcome": outcome,
                    "reference": rater,
                    "candidate": "Codex_candidate",
                    **metrics,
                }
            )

    manifest_rows = []
    for path in manifest_paths:
        relative_path = path.relative_to(data)
        manifest_rows.append(
            {
                "role": "locked_input",
                "path": f"study_data/{relative_path.as_posix()}",
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    write_csv(OUT / "input_manifest.csv", manifest_rows)
    write_csv(OUT / "candidate_task_outcomes.csv", candidate_rows)
    write_csv(OUT / "candidate_taxonomy_task_prevalence.csv", taxonomy_rows)
    write_csv(OUT / "human_stratified_estimates.csv", human_estimates)
    write_csv(OUT / "interrater_agreement.csv", agreement_rows)
    write_csv(OUT / "adjudicator_validation_random_layer.csv", validation_rows)
    write_csv(OUT / "severity_candidate_validation.csv", severity_rows)
    write_csv(OUT / "design_weighted_agreement_sensitivity.csv", weighted_agreement_rows)

    corpus_characteristics_path = data / "08_derived_corpus_features/corpus_features_summary.json"
    corpus_characteristics = json.loads(corpus_characteristics_path.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "2.0",
        "result_source": "single_authoritative_derived_object",
        "design": {
            "source_abstracts": EXPECTED_TASKS,
            "models": len(MODEL_ORDER),
            "model_document_tasks": EXPECTED_TASKS * len(MODEL_ORDER),
            "human_records_per_reviewer": len(humans["A"]),
            "human_random_lower_severity": sum(row["stratum"] == "random_10pct" for row in humans["A"]),
            "codex_flagged_high_severity_census": sum(row["stratum"] == "census_sev_ge3" for row in humans["A"]),
            "higher_severity_assessment": "post_review_consensus",
            "unique_pmids_in_human_sample": len({row["pmid"] for row in humans["A"]}),
        },
        "corpus_characteristics": corpus_characteristics,
        "candidate_task_outcomes": candidate_rows,
        "candidate_taxonomy_task_prevalence": taxonomy_rows,
        "human_stratified_estimates": human_estimates,
        "interrater_agreement": agreement_rows,
        "adjudicator_validation_random_layer": validation_rows,
        "severity_validation": severity_rows,
        "design_weighted_agreement_sensitivity": weighted_agreement_rows,
        "input_manifest": manifest_rows,
        "interpretation_constraints": [
            "Full-run outcomes are candidate labels from one blinded LLM adjudicator.",
            "The higher-severity census contains all Codex-flagged severity 3-4 tasks, not all true severity 3-4 tasks.",
            "The enriched combined human sample is not analyzed as a simple random sample.",
            "Reviewers A and B are reported separately for the independently rated random layer.",
            "The higher-severity candidate census uses the documented post-review consensus labels and is excluded from A/B inter-rater agreement.",
            "No fact-level numerical fidelity rate is calculated.",
            "No model ranking or patient-harm claim is supported.",
        ],
    }
    write_json(OUT / "locked_results_summary.json", payload)

    checkpoint = "# Stage 1 Derivation Checkpoint\n\n"
    checkpoint += f"- Frozen abstracts: {EXPECTED_TASKS:,}.\n"
    checkpoint += f"- Completed model-document tasks: {EXPECTED_TASKS * len(MODEL_ORDER):,}.\n"
    checkpoint += f"- Final human records: {len(humans['A']):,} per reviewer.\n"
    checkpoint += f"- Random lower-severity layer: {payload['design']['human_random_lower_severity']:,}.\n"
    checkpoint += f"- Codex-flagged higher-severity census: {payload['design']['codex_flagged_high_severity_census']:,}.\n"
    checkpoint += "- Higher-severity assessment: post-review consensus; excluded from A/B inter-rater agreement.\n"
    checkpoint += f"- Rating logic anomalies: 0.\n"
    checkpoint += "- Fact-level numerical fidelity rate: excluded.\n"
    checkpoint += "- Cross-model ranking tests: excluded.\n"
    checkpoint += "- Status: derived successfully; awaiting independent statistical review.\n"
    (OUT / "DERIVATION_CHECKPOINT.md").write_text(checkpoint, encoding="utf-8")

    print(json.dumps({"output_dir": str(OUT), "status": "ok", "manifest_files": len(manifest_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
