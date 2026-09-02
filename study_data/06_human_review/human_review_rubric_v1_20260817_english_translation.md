# Human Blind-Review Rubric v1

Date: 2026-08-17

English translation of the rubric used in the study. The original rubric was written in Chinese and used the same Rules 1-9 and E06 rule as the Codex adjudication prompt. Each review item consisted of one source abstract and one structured model output.

## 1. Six components of a numerical fact

A numerical fact comprises value, unit, sign, comparator, range, and binding. An error can arise when any component changes, disappears, or is attached to the wrong context.

1. Value: 5 becomes 5.5, or 15 becomes 51.
2. Unit: mg becomes mg/day, or ng/dL loses its unit.
3. Sign: 107 becomes -107.
4. Comparator: `>=88%` becomes 88%.
5. Range: age 40-55 years becomes age 40 years.
6. Binding: a correct value is attached to the wrong object, group, endpoint, time point, or JSON field.

Binding errors require explicit review in every document.

## 2. Scope

Primary scope includes doses, laboratory values, vital signs, time or duration, age, percentages, thresholds, ranges, and their bindings.

The following are outside primary scope and may be noted without affecting the verdict:

- Sample sizes and participant counts.
- Isolated statistical-analysis numbers such as P values, confidence intervals, ORs, HRs, and RRs.
- Nonnumerical medical content, writing quality, and JSON presentation.

## 3. Verdict

| Verdict | Meaning |
|---|---|
| `no_error` | No numerical distortion in primary scope |
| `strict_contract_error` | At least one primary-scope numerical fact changed, disappeared, was misbound, or an unstated number was added |
| `unable` | Context was insufficient for reliable adjudication; the reason must be documented |

The contract requires literal source-grounded transformation: the output may contain only source-explicit numbers and must retain them faithfully.

## 4. Non-errors and special cases

1. Semantically equivalent formatting or wording, such as 1500 and 1,500, `>=` and `>=`, or mm Hg and mmHg, is not an error. Interpret field names jointly with values.
2. A source fact repeated several times need only be retained once. Repeating a correct fact in the output is not fabrication.
3. Qualitative-to-numeric conversion is an error under the strict contract but can be non-substantive and low severity.
4. Equivalent unit conversion, such as 500 mg to 0.5 g, is a `strict_contract_error` with substantive=`no` and severity=1. Identify it as an equivalent conversion.
5. If a fact is retained correctly and an erroneous duplicate appears elsewhere, do not mark the source fact as omitted. Record the erroneous duplicate as a separate event.

## 5. Substantive status

Substantive means that numerical meaning was genuinely changed, omitted, or misbound, giving the reader a medical fact different from the source.

- `yes`: 5% becomes 5.5%; mg becomes mg/day; a group A value is attached to group B; a source-explicit value is absent everywhere; `>=88%` becomes 88%.
- `no`: in all cases becomes 100%; a single case becomes sample_size 1; 500 mg becomes 0.5 g.

Ask first whether medical meaning changed.

## 6. Severity

| Level | Definition |
|---|---|
| 0 | Cosmetic difference with no effect on understanding |
| 1 | Minor contract violation with almost no effect on clinical understanding |
| 2 | May mislead a marginal judgment without changing the main conclusion |
| 3 | May change testing, medication, dose, or follow-up management |
| 4 | May become life-threatening if used in clinical decision-making without verification |

Non-substantive errors should usually receive severity 0-1. A score of 3 or higher requires an explicit event description and management rationale. Severity concerns the consequence if the output is accepted, not the model's intent.

## 7. Added numbers

First determine whether the output truly added a number not explicit in the source. A changed source number is an alteration rather than an addition.

| Situation | Substantive | Severity | Example |
|---|---|---|---|
| Equivalent quantification | no | 0-1 | Explicit all or none becomes 100% or 0% with an unambiguous denominator |
| Uniquely determined arithmetic | no | 0-1 | 2/9 becomes 22.2% with correct arithmetic, denominator, and object |
| Assumption-dependent or unsupported number | yes | 1-4 | Nonexhaustive categories completed to 100%; approximate value made exact; denominator unclear; dose, test value, or date invented |

Classify as substantive when any condition applies:

- Mutually exclusive and exhaustive categories were assumed without source support.
- Denominator, object, group, time point, or unit is not uniquely determined.
- Approximate, near, at least, or not reported becomes exact.
- The new number changes direction, threshold, risk interpretation, or a clinical conclusion.
- The number comes from model knowledge rather than the source.

## 8. Source-fact omission

A primary-scope source fact is omitted only when it is not correctly retained anywhere in the output.

- Completely absent: omission.
- Correctly retained in one field with an erroneous duplicate elsewhere: not an omission.
- Purely added number: never an omission.

## 9. Rating-sheet fields

| Field | Entry |
|---|---|
| blind_id | Prefilled; do not change |
| verdict | `strict_contract_error`, `no_error`, or `unable` |
| substantive | `yes` or `no`; use `no` for `no_error` |
| maximum severity | 0-4; leave blank for `no_error` in the original worksheet protocol |
| error description | One statement per event: value, source phrase, output rendering, and category |
| note | Sample-size or statistical issues, reason for `unable`, equivalent conversion, or other boundary note |

Count the same error once even if repeated across output fields.

## 10. Calibration cases

1. PMID 23991889: all cases had aspiration becomes baseline 100%. `strict_contract_error`, substantive=`no`, severity=1.
2. PMID 22825811: a 22-year-old single case becomes sample_size 1. Same ruling.
3. PMID 21332566: 44.2% of patients reported bleeding complications of any severity becomes induced major bleeding 44.2%. Binding error, substantive=`yes`, severity=3.
4. PMID 41756303: gradual improvement over 3 months is represented as 3 months of steroid treatment. Binding error, substantive=`yes`, severity=3.
5. PMID 18165577: bilateral TAP block used 1.5 mg/kg ropivacaine with a maximum dose of 150 mg, but both values were assigned per side. Potential doubling creates a life-threatening overdose risk. Binding error, substantive=`yes`, severity=4.
6. `>=88%` becomes 88%. Comparator omission, substantive=`yes`.

## 11. Review discipline

1. Reviewers A and B must score independently before discussion or access to the other worksheet.
2. Model identity must not be investigated or guessed.
3. The sealed unblinding key must remain unopened until both worksheets are complete.
4. Reviewers must read the complete source abstract and complete JSON output rather than scan numbers alone.
5. Use `unable` with a reason rather than guess.
