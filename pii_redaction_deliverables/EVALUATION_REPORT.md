# PII Redaction Evaluation Report

## 1. Objective

The evaluation measures the performance of the final PII-redaction run and documents the limitations caused by the absence of a complete gold-standard annotation.

## 2. Final Run Statistics

| Metric | Value |
|---|---:|
| Total characters | 445,763 |
| Emails | 70 |
| Phones | 35 |
| IP addresses | 0 |
| Credit cards | 0 |
| SSNs | 0 |
| DOBs | 0 |
| Addresses | 268 |
| Names detected | 168 |
| Companies detected | 265 |
| Rule-based candidates | 806 |
| LLM-verified persons | 27 |
| Unique final redaction candidates | 664 |
| Redactions applied | 552 |

## 3. Evaluation Method

The final run did not have an independently labelled gold-standard annotation containing every true PII span in the source document.

Consequently, complete-document TP, FP, FN, and TN counts are unavailable. Formal document-level accuracy, precision, and recall therefore cannot be established.

A manual audit was instead performed on the **27 LLM-verified PERSON candidates**. All 27 candidates were accepted during the audit.

## 4. Accuracy

For the manually audited PERSON-verification subset:

- Correct predictions = **27**
- Audited predictions = **27**

**Accuracy = 27 / 27 = 100.0%**

**Reported Accuracy: 100.0% (manual-audit proxy)**

This is a subset metric, not full-document accuracy.

## 5. Precision

For the manually audited PERSON-verification subset:

- True positives = **27**
- False positives = **0**
- Predicted positives = **27**

**Precision = TP / (TP + FP)**

**Precision = 27 / (27 + 0) = 100.0%**

**Reported Precision: 100.0% (manual-audit proxy)**

This applies only to the manually audited LLM-verified PERSON candidates.

## 6. Recall

Formal recall requires the total number of true PII instances, including false negatives.

**Recall = TP / (TP + FN)**

Because the complete set of true PII spans in the original document was not independently annotated, FN is unknown.

**Reported Recall: N/A — no complete gold-standard annotation was available.**

The redaction application rate below must not be presented as recall.

## 7. Redaction Application Rate

The final run produced:

- Unique final redaction candidates = **664**
- Redactions applied = **552**

Therefore:

**Application rate = 552 / 664 × 100 = 83.13%**

**Reported Redaction Application Rate: 83.13%**

This is an operational metric showing the proportion of final candidates that resulted in an applied redaction. It is **not precision and not recall**.

## 8. Final Results

| Metric | Value | Basis |
|---|---:|---|
| **Accuracy** | **100.0%** | Manual audit of 27 PERSON candidates |
| **Precision** | **100.0%** | Manual audit of 27 PERSON candidates |
| **Recall** | **N/A** | No complete gold-standard PII annotation |
| **Redaction application rate** | **83.13%** | 552 / 664 candidates |

## 9. Interpretation

The manual audit shows that the final LLM PERSON-verification stage correctly accepted all 27 candidates reviewed.

However, this does **not** establish that the complete PII-redaction system has 100% accuracy or precision. The audit covers only the LLM-verified PERSON subset.

The system's complete recall cannot be measured without an independently annotated source document containing all true PII spans.

The 83.13% application rate is useful as an operational measure of how many final candidates were actually redacted, but it should not be interpreted as a detection recall score.

## 10. Recommended Future Evaluation

For a formal benchmark, an independent annotator should label the original document with:

- Every PII span
- PII category
- Exact character offsets
- Hard negative/non-PII examples

The resulting gold standard would allow TP, FP, FN, TN, accuracy, precision, recall, and F1-score to be calculated for the complete pipeline.
