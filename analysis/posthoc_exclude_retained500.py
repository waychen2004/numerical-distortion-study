#!/usr/bin/env python3
"""Post hoc sensitivity analysis excluding the previously retained 500 abstracts."""

from pathlib import Path
import argparse
import csv
import hashlib
import json

from scipy.stats import hypergeom


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
DEFAULT_DATA = PACKAGE_ROOT / "study_data"
DEFAULT_MANIFEST = DEFAULT_DATA / "02_frozen_corpus/corpus_construction_manifest.json"
OUTPUT = ROOT / "derived" / "posthoc_exclude_retained500_sensitivity.csv"
LOCKED_RESULTS = ROOT / "derived" / "locked_results_summary.json"

MODELS = {
    "aliyun/glm-5.2": "GLM-5.2",
    "aliyun/deepseek-v4-pro": "DeepSeek V4 Pro",
    "aliyun/deepseek-v4-flash": "DeepSeek V4 Flash",
    "aliyun/qwen3.7-max": "Qwen 3.7 Max",
    "aliyun/kimi-k2.6": "Kimi K2.6",
    "aliyun/qwen3.8-max": "Qwen 3.8 Max",
}


def read_rows(data, name):
    with (data / "06_human_review" / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def exact_total_ci(y, n, population, alpha=0.05):
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


def positive(row, outcome):
    if outcome == "strict":
        return row["verdict"] == "strict_contract_error"
    if outcome == "substantive":
        return row["substantive"].strip().lower() == "yes"
    if outcome == "severity_ge3":
        return int(row["max_severity"] or 0) >= 3
    raise ValueError(outcome)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--construction-manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main():
    args = parse_args()
    data = args.study_root.expanduser().resolve()
    manifest_path = args.construction_manifest.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    retained = {str(value) for value in manifest["retained_pmids"]}
    if len(retained) != 500:
        raise RuntimeError("Retained PMID set must contain 500 records")

    reviewers = {
        "A": read_rows(data, "reviewer_A_final_ratings.csv"),
        "B": read_rows(data, "reviewer_B_final_ratings.csv"),
    }
    rows_out = []
    for reviewer, rows in reviewers.items():
        for model_id, display in MODELS.items():
            model_rows = [row for row in rows if row["model"] == model_id and row["pmid"] not in retained]
            random_rows = [row for row in model_rows if row["stratum"] == "random_10pct"]
            high_rows = [row for row in model_rows if row["stratum"] == "census_sev_ge3"]
            n_high = len(high_rows)
            n_low = 1500 - n_high
            n_sample = len(random_rows)
            if not n_sample:
                raise RuntimeError(f"No retained sensitivity sample for {reviewer} {model_id}")
            for outcome in ["strict", "substantive", "severity_ge3"]:
                y_low = sum(positive(row, outcome) for row in random_rows)
                y_high = sum(positive(row, outcome) for row in high_rows)
                estimated_total = n_low * y_low / n_sample + y_high
                ci_low_total, ci_high_total = exact_total_ci(y_low, n_sample, n_low)
                rows_out.append({
                    "reviewer_path": f"{reviewer}/consensus",
                    "model": display,
                    "model_id": model_id,
                    "outcome": outcome,
                    "analysis_corpus": "new_1500_excluding_retained_500",
                    "target_tasks": 1500,
                    "low_population": n_low,
                    "random_sample_n": n_sample,
                    "random_positive": y_low,
                    "high_census_n": n_high,
                    "high_positive": y_high,
                    "estimated_tasks": estimated_total,
                    "estimated_rate": estimated_total / 1500,
                    "ci_low": (ci_low_total + y_high) / 1500,
                    "ci_high": (ci_high_total + y_high) / 1500,
                })

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows_out[0]))
        writer.writeheader()
        writer.writerows(rows_out)

    locked = json.loads(LOCKED_RESULTS.read_text(encoding="utf-8"))
    locked["posthoc_exclude_retained500_sensitivity"] = rows_out
    locked["posthoc_construction_manifest"] = {
        "path": "supplementary_sources/Supplementary_File_8_corpus_construction_manifest.json",
        "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    LOCKED_RESULTS.write_text(json.dumps(locked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    for row in rows_out:
        if row["outcome"] == "substantive":
            print(row["reviewer_path"], row["model"], f"{100*row['estimated_rate']:.1f}%",
                  f"({100*row['ci_low']:.1f}-{100*row['ci_high']:.1f})",
                  "n_random", row["random_sample_n"])


if __name__ == "__main__":
    main()
