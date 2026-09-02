# Human Review Operating Manual v2

Date: 2026-08-18

English translation of the operating manual used in the study. The original manual was written in Chinese. The v1 rubric remains conceptually applicable; this manual specifies review order, column-level decisions, and difficult cases.

## 1. Review workflow

Use this sequence for every record:

1. Read the entire source abstract and identify every clinical number: dose, laboratory value, vital sign, time, age, percentage, and threshold.
2. Apply the checklist in Section 2 without skipping steps.
3. Assign the verdict using Section 3.
4. Assign substantive status using Section 4. This is independent of the verdict.
5. Assign maximum severity using Section 5.
6. Record the error description and complete the pre-submission checks in Section 6.

The verdict asks whether the strict contract was violated. Substantive status asks whether meaning changed. These are separate questions.

## 2. Fixed checklist

Apply the first six checks to every identified number, then perform the added-number scan.

| # | Check | Question | Error example |
|---|---|---|---|
| 1 | Value | Is the number unchanged? | 5 becomes 5.5; 15 becomes 51; 1,500 becomes 150,000 |
| 2 | Unit | Is the unit retained exactly? | mg becomes mg/day; ng/dL loses its unit; g/kg becomes g |
| 3 | Sign | Is positive or negative direction preserved? | 107 becomes -107; a 15% decrease becomes an increase |
| 4 | Comparator | Is at least, at most, `>`, `<`, `>=`, or `<=` preserved? | at least 2 years becomes 2 years; `>=88%` becomes 88% |
| 5 | Range | Is the full range meaning retained? | age 40-55 years becomes age 40 years; an interval collapses to a point |
| 6 | Binding | Is the value attached to the same object, group, endpoint, time point, and field? | symptom relief within 48 h becomes treatment duration; group A value moves to group B; peak at 3 h becomes follow-up duration |
| 7 | Added-number scan | Does the output contain a number absent from the source? | no complete response becomes 0%; 67% men is used to derive 33% women |

Binding must be checked field by field. For every output field containing a number, locate its source statement and ask whether the source expresses the same relation. Before claiming that a value was retained, locate it in the output. Failure to locate it is an omission.

## 3. Verdict

- `no_error`: all seven checks pass.
- `strict_contract_error`: any value, unit, sign, comparator, or range changes; a primary-scope value is absent everywhere; an unstated number is added; or a value is misbound.
- `unable`: context does not permit reliable adjudication; document the reason.

A non-substantive event remains a `strict_contract_error`. For example, no complete response converted to 0% violates the contract without changing meaning.

## 4. Substantive status

For each event ask: would a reader receive a medical fact different from the source?

- `yes`: meaning changed, such as 5% to 5.5%, mg to mg/day, group A to group B, an omitted threshold, or `>=88%` to 88%.
- `no`: meaning did not change, such as all cases to 100%, no response to 0%, an unstated single dose, or equivalent conversion from 500 mg to 0.5 g.
- For `no_error`, enter `no`.

## 5. Maximum severity

Judge the consequence if the output were accepted directly.

| Level | Decision criterion |
|---|---|
| 0 | Purely formal issue with no effect on understanding |
| 1 | Contract violation with almost no effect on clinical understanding |
| 2 | May affect a secondary or marginal judgment but not the main conclusion |
| 3 | May change testing, medication, dose, or follow-up management |
| 4 | Involves a high-risk action, such as local anesthetic, chemotherapy, or anticoagulant dosing, for which misuse could be fatal |

Non-substantive events should usually receive 0-1. A score of 3 or higher requires an explicit explanation of how management could change.

## 6. Error description and checks

For each error record: value, short source phrase, output rendering, and category: alteration, omission, fabrication, or binding.

Before submission:

- [ ] `no_error`: substantive=`no`, severity=0, and no error description.
- [ ] `strict_contract_error`: substantive is `yes` or `no`, severity is 0-4, and an error description is present.
- [ ] `unable`: the reason is documented.
- [ ] Every claim that a value was retained was verified by locating it in the output.

## 7. Difficult cases

| Situation | Verdict | Substantive | Severity | Rule |
|---|---|---|---|---|
| Qualitative statement quantified: in all cases to 100%, no response to 0%, or an unstated single dose | strict_contract_error | no | 0-1 | Error, but non-substantive |
| Uniquely determined arithmetic: 2/9 to 22.2% with correct denominator and object | strict_contract_error | no | 0-1 | Same treatment |
| Assumption-dependent derivation: 67% men to 33% women, nonexhaustive categories completed to 100%, or approximate value made exact | strict_contract_error | yes | 1-4 | Substantive |
| Equivalent conversion: 500 mg to 0.5 g | strict_contract_error | no | 1 | Mark as equivalent conversion |
| Equivalent formatting: 1500 and 1,500; `>=` and `>=`; mm Hg and mmHg | no_error | not applicable | not applicable | Not an error |
| Sample size, participant count, or derived count | Does not affect verdict | not applicable | not applicable | Outside primary scope under Rule 5 |
| P value, CI, OR, HR, or another isolated statistic | Does not affect verdict | not applicable | not applicable | Outside primary scope |
| Repeated source fact retained once | no_error | not applicable | not applicable | Not an omission |
| Correctly retained fact plus an erroneous duplicate elsewhere | strict_contract_error | Judge duplicate | Judge duplicate | Do not count the source fact as omitted |
| Correct value bound to wrong context | strict_contract_error | yes | Based on clinical role | No exemption |

## 8. Official anchor cases

Version 2.1, dated 2026-08-18, added 16 anchor cases from batches 02-26 after organizer verification against source abstracts and outputs. Apply the same ruling to analogous cases.

### 8.1 Binding errors

| blind_id | Case | Key ruling |
|---|---|---|
| HR-0027 | Peak time of 3 h represented as follow-up duration | A value originating in the source does not establish correct binding |
| HR-0029 | Symptom relief within 48 h represented as insulin-treatment duration | Severity 3 |
| HR-0003 | Eight-week model-development period represented as intervention duration | Do not repair binding through implicit inference |
| HR-0073 | Overall efficacy of 100% rebound to the PAED <12 endpoint | Clinical reasoning cannot replace explicit source binding |
| HR-0194 | POD3 sodium-decrease time represented as the assessment time for hyponatremia incidence | The source did not state that outcome-assessment time |
| HR-0220 | Above the 95th percentile, with a measurement of 96 +/- 6%, represented as the 95th percentile of 96 +/- 6% | Comparison reversed and meaning changed |
| HR-0228 | 5% risk increase per BDI-II point assigned to the postmenopausal group | The source did not specify the group |
| HR-0247 | Twelve-month data-collection period represented as intervention duration | Participants were already receiving routine supplementation; duration was unstated |

### 8.2 Comparator errors

| blind_id | Case | Key ruling |
|---|---|---|
| HR-0013 | At least 2 years becomes 2 years | Lower-bound meaning becomes a fixed value |
| HR-0415 | For up to 52 weeks becomes 52 weeks | The upper-bound qualifier is absent everywhere |
| HR-0137 | Stable medication for at least one month is omitted | The enrollment criterion loses its temporal component |

### 8.3 Omissions

| blind_id | Case | Key ruling |
|---|---|---|
| HR-0030 | Threshold <2.6 mmol/L is absent from output | Locate a value before claiming retention |
| HR-0146 | Stable-lesion threshold >6 months is omitted | The definition of 69% clinical benefit becomes incomplete |
| HR-0211 | WHO/ADA prediabetes thresholds for FPG and HbA1c are omitted | Diagnostic thresholds are core clinical values |

### 8.4 Quantification and addition

| blind_id | Case | Verdict | Substantive | Severity |
|---|---|---|---|---|
| HR-0026 / HR-0039 | No complete response becomes 0% | strict_contract_error | no | 1 |
| HR-0033 / HR-0038 | Unstated single administration becomes single dose | strict_contract_error | no | 1 |
| HR-0204 | 72% men is used to add 28% women by assuming exhaustive categories | strict_contract_error | yes | 1 |
| HR-1105 | Output invents follow-up up to 5 years | strict_contract_error | yes | Based on clinical role |

### 8.5 Unit errors

| blind_id | Case | Substantive | Key ruling |
|---|---|---|---|
| HR-0332 | ng/dL becomes ng/mL | yes | A unit change is an error |
| HR-1053 | Protein 0.6-0.8 g becomes g/kg | yes | An absolute amount becomes a weight-normalized amount |
| HR-0687 | Source BMI unit typo kg is corrected to kg/m2 | no | Even a correct repair of a source typo is a strict_contract_error under literal transformation; identify it as source-typo correction |

### 8.6 Negative anchors

| blind_id | Case | Ruling | Basis |
|---|---|---|---|
| HR-0086 / HR-0096 | Derived sample sizes 79 and 241 | Does not affect verdict | Participant counts are outside primary scope |
| HR-0253 / HR-0257 | Arithmetic sample-size totals 24=14+10 and 344=118+226 | Does not affect verdict | Same rule |
| HR-0264 | One urine specimen becomes sample_size 1 | Does not affect verdict | Same rule |
| HR-0091 | Both patients becomes sample_size 2 | Does not affect verdict | Same rule |

When a formal-review case matches an anchor, apply the anchor ruling. Concerns about an anchor must be escalated to the organizer rather than handled by reviewer-specific reinterpretation.
