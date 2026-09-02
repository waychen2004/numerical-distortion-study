#!/usr/bin/env python3
"""Derive major-revision analyses from the authoritative locked result object."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path

import numpy as np
from scipy.stats import hypergeom


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
DEFAULT_STUDY = PACKAGE_ROOT / "study_data"
DERIVED = ROOT / "derived"
LOCKED_RESULTS = DERIVED / "locked_results_summary.json"
BOOTSTRAP_SEED = 20260827
BOOTSTRAP_REPLICATES = 20_000
MODEL_ORDER = [
    "GLM-5.2",
    "DeepSeek V4 Pro",
    "DeepSeek V4 Flash",
    "Qwen 3.7 Max",
    "Kimi K2.6",
    "Qwen 3.8 Max",
]
E_CODES = [f"E{i:02d}" for i in range(1, 11)]


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty output: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=DEFAULT_STUDY)
    return parser.parse_args()


def kappa_from_counts(tp: float, tn: float, fp: float, fn: float) -> float:
    n = tp + tn + fp + fn
    observed = (tp + tn) / n
    reference_positive = (tp + fn) / n
    candidate_positive = (tp + fp) / n
    expected = (
        reference_positive * candidate_positive
        + (1 - reference_positive) * (1 - candidate_positive)
    )
    return (observed - expected) / (1 - expected) if expected != 1 else 1.0


def wilson(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return center - half, center + half


def bootstrap_agreement(rows: list[dict]) -> list[dict]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    outputs = []
    for row in rows:
        if row["outcome"] not in {"strict", "substantive"}:
            continue
        counts = np.array([row["tp"], row["tn"], row["fp"], row["fn"]], dtype=int)
        n = int(counts.sum())
        draws = rng.multinomial(n, counts / n, size=BOOTSTRAP_REPLICATES)
        kappas = []
        positive_agreements = []
        negative_agreements = []
        for tp, tn, fp, fn in draws:
            kappas.append(kappa_from_counts(tp, tn, fp, fn))
            positive_agreements.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0)
            negative_agreements.append(2 * tn / (2 * tn + fp + fn) if 2 * tn + fp + fn else 1.0)
        overall_low, overall_high = wilson(int(row["tp"] + row["tn"]), n)
        outputs.append({
            "comparison": row["comparison"],
            "stratum": row["stratum"],
            "outcome": row["outcome"],
            "n": n,
            "overall_agreement": row["overall_agreement"],
            "overall_agreement_ci_low": overall_low,
            "overall_agreement_ci_high": overall_high,
            "cohen_kappa": row["cohen_kappa"],
            "cohen_kappa_ci_low": float(np.quantile(kappas, 0.025)),
            "cohen_kappa_ci_high": float(np.quantile(kappas, 0.975)),
            "positive_agreement": row["positive_agreement"],
            "positive_agreement_ci_low": float(np.quantile(positive_agreements, 0.025)),
            "positive_agreement_ci_high": float(np.quantile(positive_agreements, 0.975)),
            "negative_agreement": row["negative_agreement"],
            "negative_agreement_ci_low": float(np.quantile(negative_agreements, 0.025)),
            "negative_agreement_ci_high": float(np.quantile(negative_agreements, 0.975)),
            "ci_method": f"paired multinomial bootstrap ({BOOTSTRAP_REPLICATES} replicates; seed {BOOTSTRAP_SEED}); Wilson CI for overall agreement",
        })
    return outputs


def higher_severity_audit(estimates: list[dict]) -> list[dict]:
    rows_a = [
        row for row in estimates
        if row["rater"] == "A" and row["outcome"] == "severity_ge3"
    ]
    rows_b = [
        row for row in estimates
        if row["rater"] == "B" and row["outcome"] == "severity_ge3"
    ]
    by_model_b = {row["model"]: row for row in rows_b}
    outputs = []
    for row in sorted(rows_a, key=lambda value: MODEL_ORDER.index(value["model"])):
        peer = by_model_b[row["model"]]
        for field in ["low_positive", "high_positive", "low_population", "low_sample"]:
            if row[field] != peer[field]:
                raise ValueError(f"A/B higher-severity labels differ for {row['model']}: {field}")
        missed = row["low_population"] * row["low_positive"] / row["low_sample"]
        confirmed = row["high_positive"]
        total = missed + confirmed
        missed_low = max(0.0, row["stratified_ci_low"] * 2000 - confirmed)
        missed_high = max(0.0, row["stratified_ci_high"] * 2000 - confirmed)
        outputs.append({
            "model": row["model"],
            "model_id": row["model_id"],
            "codex_low_population": row["low_population"],
            "human_random_sample": row["low_sample"],
            "human_severity_ge3_in_codex_low_sample": row["low_positive"],
            "design_weighted_missed_tasks": missed,
            "missed_tasks_bound_low": missed_low,
            "missed_tasks_bound_high": missed_high,
            "codex_high_census": row["codex_flagged_high_census"],
            "human_confirmed_severity_ge3_in_codex_high": confirmed,
            "design_weighted_total_severity_ge3_tasks": total,
            "descriptive_capture_fraction": confirmed / total if total else None,
            "bound_note": "missed-task bounds transform the model-specific exact finite-population interval; capture fraction is descriptive, not validated screening sensitivity",
        })

    missed = sum(row["design_weighted_missed_tasks"] for row in outputs)
    confirmed = sum(row["human_confirmed_severity_ge3_in_codex_high"] for row in outputs)
    total = missed + confirmed
    outputs.append({
        "model": "All six runs (descriptive aggregate)",
        "model_id": "aggregate_not_pooled_prevalence",
        "codex_low_population": sum(row["codex_low_population"] for row in outputs),
        "human_random_sample": sum(row["human_random_sample"] for row in outputs),
        "human_severity_ge3_in_codex_low_sample": sum(row["human_severity_ge3_in_codex_low_sample"] for row in outputs),
        "design_weighted_missed_tasks": missed,
        "missed_tasks_bound_low": "",
        "missed_tasks_bound_high": "",
        "codex_high_census": sum(row["codex_high_census"] for row in outputs),
        "human_confirmed_severity_ge3_in_codex_high": confirmed,
        "design_weighted_total_severity_ge3_tasks": total,
        "descriptive_capture_fraction": confirmed / total if total else None,
        "bound_note": "descriptive sum across six finite runs; no joint confidence interval and no clinical screening-sensitivity claim",
    })
    return outputs


def reviewer_path_sensitivity(estimates: list[dict]) -> list[dict]:
    selected = [row for row in estimates if row["outcome"] in {"strict", "substantive"}]
    by_key = {(row["model"], row["outcome"], row["rater"]): row for row in selected}
    outputs = []
    for model in MODEL_ORDER:
        for outcome in ["strict", "substantive"]:
            a = by_key[(model, outcome, "A")]["stratified_estimated_rate"]
            b = by_key[(model, outcome, "B")]["stratified_estimated_rate"]
            outputs.append({
                "model": model,
                "outcome": outcome,
                "A_consensus_rate": a,
                "B_consensus_rate": b,
                "observed_reviewer_path_low": min(a, b),
                "observed_reviewer_path_high": max(a, b),
                "absolute_path_difference": abs(a - b),
                "interpretation": "observed reviewer-path sensitivity; not a corrected truth interval",
            })
    return outputs


def exact_total_ci(y: int, n: int, population: int, alpha: float = 0.05) -> tuple[int, int]:
    minimum = y
    maximum = population - (n - y)
    lower = minimum
    for total in range(minimum, maximum + 1):
        if hypergeom.sf(y - 1, population, total, n) >= alpha / 2:
            lower = total
            break
    upper = maximum
    for total in range(maximum, minimum - 1, -1):
        if hypergeom.cdf(y, population, total, n) >= alpha / 2:
            upper = total
            break
    return lower, upper


def validation_precision() -> list[dict]:
    population = 2000
    sample = 200
    outputs = []
    for expected_rate in [0.01, 0.05, 0.10, 0.20, 0.30, 0.50]:
        positives = round(sample * expected_rate)
        low, high = exact_total_ci(positives, sample, population)
        outputs.append({
            "finite_population": population,
            "sample_size": sample,
            "illustrative_sample_positive": positives,
            "illustrative_sample_rate": positives / sample,
            "exact_ci_low": low / population,
            "exact_ci_high": high / population,
            "interval_width": (high - low) / population,
            "purpose": "post hoc precision description, not prospective power calculation",
        })
    return outputs


def normalize_human_e_codes(study_root: Path) -> tuple[list[dict], list[dict]]:
    normalized = []
    by_rater: dict[str, dict[str, set[str]]] = {}
    for rater in ["A", "B"]:
        rows = read_csv(study_root / f"06_human_review/reviewer_{rater}_final_ratings.csv")
        by_rater[rater] = {}
        for row in rows:
            raw = row["E"].strip()
            codes = sorted(set(re.findall(r"E(?:0[1-9]|10)", raw)), key=E_CODES.index)
            if codes:
                status = "parsed_declared_codes"
            elif raw.lower() in {"", "none", "e0", "e00"}:
                status = "explicit_no_code"
            else:
                status = "unparsed_nonempty"
            by_rater[rater][row["blind_id"]] = set(codes)
            normalized.append({
                "rater": rater,
                "blind_id": row["blind_id"],
                "pmid": row["pmid"],
                "model": row["model"],
                "stratum": row["stratum"],
                "original_E": raw,
                "normalized_declared_codes": "|".join(codes),
                "normalization_status": status,
                "normalization_boundary": "syntax-only extraction; no semantic correction of reviewer labels",
            })

    a_rows = {row["blind_id"]: row for row in normalized if row["rater"] == "A"}
    random_ids = sorted(
        blind_id for blind_id, row in a_rows.items() if row["stratum"] == "random_10pct"
    )
    agreement = []
    for code in E_CODES:
        a_values = [code in by_rater["A"][blind_id] for blind_id in random_ids]
        b_values = [code in by_rater["B"][blind_id] for blind_id in random_ids]
        tp = sum(a and b for a, b in zip(a_values, b_values))
        tn = sum(not a and not b for a, b in zip(a_values, b_values))
        fp = sum(not a and b for a, b in zip(a_values, b_values))
        fn = sum(a and not b for a, b in zip(a_values, b_values))
        n = tp + tn + fp + fn
        agreement.append({
            "E_code": code,
            "stratum": "random_10pct_independent",
            "n": n,
            "reviewer_A_positive": tp + fn,
            "reviewer_B_positive": tp + fp,
            "both_positive": tp,
            "both_negative": tn,
            "A_negative_B_positive": fp,
            "A_positive_B_negative": fn,
            "overall_agreement": (tp + tn) / n,
            "positive_agreement": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
            "cohen_kappa": kappa_from_counts(tp, tn, fp, fn),
            "interpretation_boundary": "agreement of syntax-normalized reviewer-declared codes; not ontology validation",
        })
    return normalized, agreement


def main() -> None:
    args = parse_args()
    study_root = args.study_root.expanduser().resolve()
    locked = json.loads(LOCKED_RESULTS.read_text(encoding="utf-8"))
    agreement_rows = bootstrap_agreement(
        locked["interrater_agreement"] + locked["adjudicator_validation_random_layer"]
    )
    severity_rows = higher_severity_audit(locked["human_stratified_estimates"])
    reviewer_rows = reviewer_path_sensitivity(locked["human_stratified_estimates"])
    precision_rows = validation_precision()
    normalized_e_rows, e_agreement_rows = normalize_human_e_codes(study_root)

    outputs = {
        "agreement_confidence_intervals": agreement_rows,
        "higher_severity_screening_audit": severity_rows,
        "reviewer_path_sensitivity": reviewer_rows,
        "validation_sample_precision": precision_rows,
        "human_e_code_normalization_audit": normalized_e_rows,
        "human_e_code_agreement_random_layer": e_agreement_rows,
    }
    for key, rows in outputs.items():
        write_csv(DERIVED / f"{key}.csv", rows)
        locked[key] = rows
    locked["revision_analysis_metadata"] = {
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "higher_severity_boundary": "descriptive candidate-screen audit; not validated clinical sensitivity",
        "reviewer_path_boundary": "A/consensus and B/consensus remain separate; no corrected ground truth was imputed",
    }
    LOCKED_RESULTS.write_text(json.dumps(locked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "outputs": list(outputs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
