#!/usr/bin/env python3
"""Recompute six-model statistics with one model-independent source ledger."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from datetime import datetime
from pathlib import Path


EXPECTED = 2_000
BOOTSTRAP_ITERATIONS = 20_000
BOOTSTRAP_SEED = 20260816
RUNS = {
    "G": ("aliyun/glm-5.2", "aliyun_glm52_extract_2000_20260817", "GLM-5.2"),
    "H": ("aliyun/deepseek-v4-pro", "aliyun_deepseek_v4_pro_extract_2000_20260817", "DeepSeek V4 Pro"),
    "I": ("aliyun/deepseek-v4-flash", "aliyun_deepseek_v4_flash_extract_2000_20260817", "DeepSeek V4 Flash"),
    "J": ("aliyun/qwen3.7-max", "aliyun_qwen37max_extract_2000_20260817", "Qwen 3.7 Max"),
    "K": ("aliyun/kimi-k2.6", "aliyun_kimi_k2_6_extract_2000_20260817", "Kimi K2.6"),
    "L": ("aliyun/qwen3.8-max", "aliyun_qwen38max_extract_2000_20260817", "Qwen 3.8 Max"),
}
E_CODES = tuple(f"E{i:02d}" for i in range(1, 11))


def portable_path(path: Path, repository_root: Path) -> str:
    """Record repository-relative paths without exposing a contributor's filesystem."""
    try:
        return path.resolve().relative_to(repository_root).as_posix()
    except ValueError:
        return path.name


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def wilson(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return center - half, center + half


def e_code(event: dict) -> str:
    direct = {
        "decimal_shift": "E01", "digit_transposition": "E02", "unit": "E03",
        "threshold_precision": "E04", "threshold_omission": "E05",
        "qualitative_to_numeric": "E06", "derived_numeric": "E06",
        "sign": "E07", "comparator": "E08", "range": "E09", "binding": "E10",
    }
    if event["mechanism"] in direct:
        return direct[event["mechanism"]]
    return {"alteration": "E04", "omission": "E05", "fabrication": "E06", "binding": "E10"}[
        event["direction"]
    ]


def load_ledger(path: Path) -> tuple[dict[str, int], int, int]:
    rows = read_jsonl(path)
    counts = {str(row["pmid"]): int(row["source_count"]) for row in rows}
    mentions = sum(int(row["source_mentions"]) for row in rows)
    return counts, sum(counts.values()), mentions


def analyze_run(
    letter: str,
    runs_root: Path,
    blind_root: Path,
    canonical_facts: dict[str, int],
    canonical_total: int,
    checks: list[str],
) -> dict:
    label, run_dir_name, display_name = RUNS[letter]
    run_dir = runs_root / run_dir_name
    blind_dir = blind_root / f"run_{letter}_2000_20260817"
    outputs = read_jsonl(run_dir / "outputs.jsonl")
    reviews = read_jsonl(blind_dir / "reviews.jsonl")

    def check(condition: bool, message: str) -> None:
        if not condition:
            raise RuntimeError(message)
        checks.append(f"PASS | run_{letter}: {message}")

    check(len(outputs) == EXPECTED, "2,000 model outputs")
    check(len(reviews) == EXPECTED, "2,000 adjudication records")
    output_pmids = {str(row["pmid"]) for row in outputs}
    review_pmids = {str(row["pmid"]) for row in reviews}
    check(len(output_pmids) == EXPECTED, "model output PMIDs unique")
    check(len(review_pmids) == EXPECTED, "adjudication PMIDs unique")
    check(output_pmids == review_pmids == set(canonical_facts), "PMID coverage matches canonical ledger")
    check(all(row.get("llm_output") and not row.get("llm_error") and not row.get("truncated") for row in outputs),
          "no empty, failed, or truncated model output")

    events = [{**event, "pmid": str(review["pmid"])} for review in reviews for event in review["events"]]
    primary = [event for event in events if event["primary_scope"]]
    substantive = [event for event in primary if event["substantive"]]
    failures = [event for event in primary if event["source_fact_failure"]]
    high_risk = [event for event in primary if event["severity"] >= 3]
    error_docs = {event["pmid"] for event in primary}
    substantive_docs = {event["pmid"] for event in substantive}
    high_risk_docs = {event["pmid"] for event in high_risk}
    verdicts = Counter(review["verdict"] for review in reviews)
    category = Counter(e_code(event) for event in primary)
    category_substantive = Counter(e_code(event) for event in substantive)
    category_failure = Counter(e_code(event) for event in failures)
    category_high_risk = Counter(e_code(event) for event in high_risk)
    direction = Counter(event["direction"] for event in primary)
    mechanism = Counter(event["mechanism"] for event in primary)
    severity = Counter(event["severity"] for event in events)
    per_doc_failures = Counter(event["pmid"] for event in failures)

    rng = random.Random(BOOTSTRAP_SEED)
    pmids = sorted(review_pmids)
    bootstrap = []
    for _ in range(BOOTSTRAP_ITERATIONS):
        sampled = [rng.choice(pmids) for _ in pmids]
        numerator = sum(per_doc_failures[pmid] for pmid in sampled)
        denominator = sum(canonical_facts[pmid] for pmid in sampled)
        bootstrap.append(1 - numerator / denominator)
    bootstrap.sort()

    result = {
        "model": label,
        "display_name": display_name,
        "blind_run": letter,
        "documents": EXPECTED,
        "source_fact_groups": canonical_total,
        "documents_with_primary_error": len(error_docs),
        "document_error_rate": len(error_docs) / EXPECTED,
        "document_error_rate_95ci": wilson(len(error_docs), EXPECTED),
        "documents_with_substantive_error": len(substantive_docs),
        "substantive_document_rate": len(substantive_docs) / EXPECTED,
        "substantive_document_rate_95ci": wilson(len(substantive_docs), EXPECTED),
        "documents_with_sev_ge3_event": len(high_risk_docs),
        "sev_ge3_document_rate_95ci": wilson(len(high_risk_docs), EXPECTED),
        "primary_events": len(primary),
        "substantive_events": len(substantive),
        "source_fact_failures": len(failures),
        "numerical_fidelity_rate": 1 - len(failures) / canonical_total,
        "numerical_fidelity_rate_cluster_bootstrap_95ci": (bootstrap[499], bootstrap[19499]),
        "severity_ge_3_events": len(high_risk),
        "e1_e10": {code: category.get(code, 0) for code in E_CODES},
        "e1_e10_substantive": {code: category_substantive.get(code, 0) for code in E_CODES},
        "e1_e10_source_failure": {code: category_failure.get(code, 0) for code in E_CODES},
        "e1_e10_sev_ge3": {code: category_high_risk.get(code, 0) for code in E_CODES},
        "direction": dict(direction),
        "mechanism": dict(mechanism),
        "severity_distribution": {str(key): value for key, value in sorted(severity.items())},
        "verdicts": dict(verdicts),
        "unable_documents": verdicts.get("unable", 0),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parent
    repository_root = default_root.parent
    parser.add_argument("--runs-root", type=Path, default=default_root / "runs")
    parser.add_argument("--blind-root", type=Path, default=default_root / "blind_runs")
    parser.add_argument("--corpus", type=Path, default=default_root / "corpus/subset2000_effective_20260817.jsonl")
    parser.add_argument("--ledger", type=Path, default=default_root / "canonical_source_fact_ledger_16715.jsonl")
    parser.add_argument("--output-dir", type=Path, default=default_root / "paper_analysis_unified_16715")
    args = parser.parse_args()

    corpus = read_jsonl(args.corpus)
    canonical_path = args.ledger
    canonical_facts, canonical_total, source_mentions = load_ledger(canonical_path)
    if canonical_total != 16_715 or len(canonical_facts) != EXPECTED:
        raise RuntimeError("Canonical source ledger must contain 16,715 groups across 2,000 PMIDs")
    corpus_pmids = {str(row["pmid"]) for row in corpus}
    if corpus_pmids != set(canonical_facts):
        raise RuntimeError("Corpus and canonical source ledger PMID sets differ")

    checks: list[str] = []
    per_model = [
        analyze_run(letter, args.runs_root, args.blind_root, canonical_facts, canonical_total, checks)
        for letter in RUNS
    ]
    pooled_primary = Counter()
    pooled_substantive = Counter()
    pooled_direction = Counter()
    pooled_mechanism = Counter()
    pooled_severity = Counter()
    for model in per_model:
        pooled_primary.update(model["e1_e10"])
        pooled_substantive.update(model["e1_e10_substantive"])
        pooled_direction.update(model["direction"])
        pooled_mechanism.update(model["mechanism"])
        pooled_severity.update(model["severity_distribution"])

    consolidated = {
        "models": len(per_model),
        "model_tasks": sum(model["documents"] for model in per_model),
        "documents_unique": EXPECTED,
        "source_fact_groups_per_model": canonical_total,
        "model_fact_exposures": canonical_total * len(per_model),
        "primary_error_tasks": sum(model["documents_with_primary_error"] for model in per_model),
        "substantive_error_tasks": sum(model["documents_with_substantive_error"] for model in per_model),
        "sev_ge3_tasks": sum(model["documents_with_sev_ge3_event"] for model in per_model),
        "primary_events": sum(model["primary_events"] for model in per_model),
        "substantive_events": sum(model["substantive_events"] for model in per_model),
        "source_fact_failures": sum(model["source_fact_failures"] for model in per_model),
        "severity_ge_3_events": sum(model["severity_ge_3_events"] for model in per_model),
        "pooled_e1_e10_primary": dict(pooled_primary),
        "pooled_e1_e10_substantive": dict(pooled_substantive),
        "pooled_direction": dict(pooled_direction),
        "pooled_mechanism": dict(pooled_mechanism),
        "pooled_severity": dict(pooled_severity),
    }
    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "design": {
            "corpus": portable_path(args.corpus, repository_root),
            "canonical_source_ledger": portable_path(canonical_path, repository_root),
            "source_mentions": source_mentions,
            "source_fact_groups": canonical_total,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "ci_methods": "document rates: Wilson; NFR: document-cluster bootstrap",
            "denominator_definition": "One model-independent source ledger is used for all six models.",
        },
        "per_model": per_model,
        "consolidated": consolidated,
        "verification_checks": checks,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "consolidated_stats_unified_16715.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log = args.output_dir / "verification_log_unified_16715.md"
    log.write_text(
        "# Unified-denominator verification\n\n"
        f"- Checks: {len(checks)}; all PASS.\n"
        f"- Canonical source fact groups: {canonical_total}.\n\n"
        + "\n".join(f"- {line}" for line in checks) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "checks": len(checks), "models": len(per_model)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
