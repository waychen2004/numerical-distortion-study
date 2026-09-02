# Medical Numerical Distortion Taxonomy (E01-E10)

This document defines the ten numerical-distortion categories used in the study. Categories apply to error events, not models or documents.

| Code | Name | Definition |
|---|---|---|
| E01 | Decimal shift | A changed decimal position alters the order of magnitude. |
| E02 | Digit transposition | The order of digits is exchanged. |
| E03 | Unit error | A unit is replaced, omitted, or added, changing dimension or dose meaning. |
| E04 | Value alteration | A source value is replaced by a different value, or an approximation is made inappropriately precise. |
| E05 | Numerical omission | A value, threshold, or range explicitly stated in the source is not retained anywhere in the output. |
| E06 | Number not explicit in source | The output contains a number not explicitly stated in the source. Distinguish equivalent quantification, uniquely determined arithmetic derivation, and assumption-dependent addition. |
| E07 | Sign reversal | The positive or negative direction of a value changes. |
| E08 | Comparator error | `>`, `<`, `>=`, `<=`, or an equivalent natural-language comparison is changed or omitted. |
| E09 | Range corruption | A range endpoint, interval structure, or boundary relation is changed, truncated, or omitted. |
| E10 | Contextual misbinding | The value is retained but attached to the wrong object, group, endpoint, time point, or field. |

## Error direction

- `alteration`: a source value is changed.
- `omission`: an explicit source value is not retained.
- `fabrication`: the output adds a number not explicit in the source.
- `binding`: the relation between a value and its object, group, endpoint, time point, or field is wrong.

Direction and E01-E10 are separate dimensions. A unit error can involve alteration or omission; contextual misbinding uses the `binding` direction.

## Substantive status

- `substantive=true`: the output changes the medical meaning of the fact.
- `substantive=false`: the output violates the strict transformation contract without changing medical meaning.

## Severity

- 0: cosmetic or formatting difference with no effect on understanding.
- 1: minor deviation with little effect on medical understanding.
- 2: may mislead a marginal judgment but usually does not change the main clinical conclusion.
- 3: may change testing, medication, dose, or follow-up decisions if accepted.
- 4: may cause serious harm or become life-threatening if used without verification.

Severity depends on the value's role in its medical context and is not mechanically determined by the error code.

## Source-fact failure

Set `source_fact_failure=true` only when a numerical fact in primary scope is not correctly retained anywhere in the output. A purely added number is not a source-fact failure. If the same fact is correctly retained elsewhere, do not deduct it again from fact-level fidelity.
