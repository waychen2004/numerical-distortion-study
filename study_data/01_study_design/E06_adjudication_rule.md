# E06 Adjudication Rule for Added Numbers

E06 denotes a number not explicitly stated in the source. It remains a violation of the strict source contract, but absence of an identical numeric string in the source is not enough to classify it as a substantive hallucination.

## Adjudication sequence

1. Confirm that the output introduced a number not explicitly stated in the source. If a source number was changed, use E04 or the corresponding category rather than E06.
2. Determine whether the new number is uniquely determined by the source and whether it introduces an additional assumption, an incorrect denominator, or a wrong temporal or object binding.
3. Judge `substantive` and `severity` separately. Do not infer severity from the E06 label.

## Three situations

| Situation | mechanism | substantive | Typical severity | Example |
|---|---|---:|---:|---|
| Semantically equivalent quantification | `qualitative_to_numeric` | false | 0-1 | Explicit all or none converted to 100% or 0% when the population and denominator are unambiguous |
| Uniquely determined arithmetic derivation | `derived_numeric` | false | 0-1 | Source states 2/9 and output adds 22.2%, with correct arithmetic, denominator, and object |
| Assumption-dependent or unsupported number | `derived_numeric` or `other` | true | 1-4 | Nonexhaustive categories completed to 100%; approximate value made exact; denominator unclear; dose, test value, or date fabricated |

## Conditions requiring substantive classification

- The derivation assumes mutually exclusive and exhaustive categories without source support.
- The denominator, object, group, time point, or unit is not uniquely determined by the source.
- Approximate, near, at least, or not reported is converted into an exact value.
- The new number changes direction, threshold, risk interpretation, or a clinical conclusion.
- The number comes from model prior knowledge rather than verifiable source text.

## Responsibilities of code and LLM

- Code only detects potentially added numbers and checks output consistency. A purely added event must not have `source_fact_failure=true`. A non-substantive E06 event must not receive severity 2-4. A source fact fails only when it is not correctly retained anywhere; an erroneous duplicate after correct retention must not reduce the numerical fidelity rate again.
- The LLM must read the complete source and output to judge unique derivability, assumptions, and clinical impact.
- Reports must provide both total E06 events and substantive E06 events. They must not describe every E06 event as a clinical hallucination or silently exclude all E06 events from primary error reporting.
