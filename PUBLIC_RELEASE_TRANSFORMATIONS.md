# Public Release Transformations

This English-only public package was derived from the frozen internal study package without changing task identifiers, model outputs, structured adjudication labels, human verdicts, severity ratings, or statistical outcomes.

The following release-only transformations were applied:

1. Full PubMed abstract text was omitted and linked by PMID and SHA-256.
2. Duplicate source abstracts were removed from model-output records.
3. Local filesystem paths were redacted.
4. Chinese free-text rationales in Codex adjudications were omitted. Structured event fields were retained.
5. Chinese human-review notes were omitted. Reviewer verdicts, substantive labels, severity, normalized declared E codes, and English direction labels were retained.
6. Chinese study-type and clinical-field labels were translated to fixed English labels.
7. The original Chinese adjudication prompt, human-review rubric, and operating manual were replaced by faithful English translations. Translation files are explicitly labeled and were not the literal runtime documents.

These transformations reduce redistribution and language barriers but prevent byte-for-byte reconstruction of omitted source text and narrative notes. They do not affect the released analysis denominators or reported results.
