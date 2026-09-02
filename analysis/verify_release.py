#!/usr/bin/env python3
"""Verify public-release counts and scan for local paths or credential literals."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "study_data"
RUNS = {
    "G": "aliyun_glm52_extract_2000_20260817",
    "H": "aliyun_deepseek_v4_pro_extract_2000_20260817",
    "I": "aliyun_deepseek_v4_flash_extract_2000_20260817",
    "J": "aliyun_qwen37max_extract_2000_20260817",
    "K": "aliyun_kimi_k2_6_extract_2000_20260817",
    "L": "aliyun_qwen38max_extract_2000_20260817",
}
LOCAL_PATH = re.compile(
    r"(?:file://)?(?:/(?:Users|home|Volumes|private/var|var/folders|tmp)/[^\s\"<>]+|[A-Za-z]:\\\\[^\s\"<>]+)"
)
EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
HAN = re.compile(r"[\u3400-\u9fff]")
SECRET_PATTERNS = {
    "private_key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "openai_style_key": re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    "aliyun_access_key": re.compile(r"(?:LTAI|AKID)[A-Za-z0-9]{12,}"),
    "embedded_ncbi_key": re.compile(r'NCBI_API_KEY\s*=\s*os\.environ\.get\([^,]+,\s*"[^\"]{8,}"'),
    "credential_url": re.compile(r"https?://[^\s\"]*[?&](?:key|token|access_token|api_key|sig|signature)=", re.I),
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)
    print(f"PASS: {message}")


def scan_text() -> None:
    findings = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.txt", "FILE_MANIFEST.csv"}:
            continue
        if HAN.search(path.relative_to(ROOT).as_posix()):
            findings.append(f"chinese_path:{path.relative_to(ROOT)}")
        check(path.stat().st_size < 100_000_000, f"GitHub file-size limit: {path.relative_to(ROOT)}")
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        if LOCAL_PATH.search(text):
            findings.append(f"local_path:{path.relative_to(ROOT)}")
        if HAN.search(text):
            findings.append(f"chinese_text:{path.relative_to(ROOT)}")
        emails = {match.group(0) for match in EMAIL.finditer(text)} - {"YOUR_EMAIL@example.org"}
        if emails:
            findings.append(f"email:{path.relative_to(ROOT)}")
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{name}:{path.relative_to(ROOT)}")
    check(not findings, f"no language, privacy, path, or credential findings ({findings})")


def main() -> None:
    corpus = read_jsonl(DATA / "02_frozen_corpus/corpus_manifest_2000.jsonl")
    corpus_pmids = {str(row["pmid"]) for row in corpus}
    check(len(corpus) == len(corpus_pmids) == 2_000, "2,000 unique corpus PMIDs")
    check(all("abstract" not in row and len(row["abstract_sha256"]) == 64 for row in corpus), "full abstracts omitted and hashes retained")

    ledger = read_jsonl(DATA / "02_frozen_corpus/canonical_source_fact_ledger_16715.jsonl")
    check(len(ledger) == 2_000 and sum(int(row["source_count"]) for row in ledger) == 16_715, "2,000 ledger rows and 16,715 source groups")
    check(all("source_numbers" not in row for row in ledger), "source contexts omitted from public ledger")

    for letter, run_dir in RUNS.items():
        outputs = read_jsonl(DATA / f"03_model_outputs/{run_dir}/outputs.jsonl")
        reviews = read_jsonl(DATA / f"04_codex_adjudications/run_{letter}_2000_20260817/reviews.jsonl")
        output_pmids = {str(row["pmid"]) for row in outputs}
        review_pmids = {str(row["pmid"]) for row in reviews}
        check(len(outputs) == len(reviews) == 2_000, f"run {letter}: 2,000 outputs and reviews")
        check(output_pmids == review_pmids == corpus_pmids, f"run {letter}: PMID coverage")
        check(all("source_abstract" not in row and len(row["source_abstract_sha256"]) == 64 for row in outputs), f"run {letter}: source text omitted")

    for reviewer in ["A", "B"]:
        path = DATA / f"06_human_review/reviewer_{reviewer}_final_ratings.csv"
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        check(len(rows) == 1_347 and len({row["blind_id"] for row in rows}) == 1_347, f"Reviewer {reviewer}: 1,347 unique ratings")
        check(all(row["verdict"] for row in rows), f"Reviewer {reviewer}: verdict complete")

    scan_text()
    print("PUBLIC RELEASE VERIFICATION PASSED")


if __name__ == "__main__":
    main()
