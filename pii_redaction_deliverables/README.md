# PII Redaction Tool

## Overview

This project implements a PII-redaction pipeline for DOCX documents. It combines deterministic/rule-based detection, chunked name detection, company detection, and Groq LLM verification for ambiguous person-name candidates.

## Approach

1. **Regex / deterministic rules** detect structured PII such as emails, phone numbers, IP addresses, credit-card-like values, SSN-like values, dates/DOB patterns, addresses, and other rule-based candidates.
2. **Chunked name detection** processes the large document in manageable chunks to avoid the memory errors encountered when running NER over the entire 445,763-character document at once.
3. **Company detection** identifies company/organization candidates using the rule-based/NER pipeline.
4. **Groq LLM verification** verifies ambiguous person-name candidates in batches. Candidates are filtered before being sent to the LLM, and only PERSON results with confidence >= 0.85 are accepted.
5. **Redaction** combines and deduplicates the final PII spans and applies the redactions to the DOCX output.

## Final Run

- Total characters: **445,763**
- Emails: **70**
- Phones: **35**
- IPs: **0**
- Credit cards: **0**
- SSNs: **0**
- DOBs: **0**
- Addresses: **268**
- Names detected: **168**
- Companies detected: **265**
- Rule-based candidates: **806**
- LLM-verified persons: **27**
- Unique final redaction candidates: **664**
- Redactions applied: **552**

## Evaluation

A complete independently annotated gold-standard dataset was not available. Therefore, full-document accuracy, precision, and recall cannot be calculated as formal benchmark metrics.

A manual audit was performed on the **27 LLM-verified PERSON candidates**, and all 27 were accepted.

- **Accuracy: 100.0% — manual-audit proxy (27/27).**
- **Precision: 100.0% — manual-audit proxy (27/27).**
- **Recall: N/A — no complete gold-standard annotation was available.**
- **Redaction application rate: 83.13% — 552/664.**

The 83.13% figure is an operational application-rate metric and is **not recall**.

## Tradeoffs and Limitations

Rule-based detection is fast and predictable but may miss unusual PII formats. NER provides contextual detection but can be memory-intensive on very large documents, so chunking is used.

LLM verification improves precision for ambiguous person names but introduces API dependency, latency, and possible model errors.

Company detection may still encounter difficult financial-document terminology, organization names, trusts, banks, and generic phrases. Conservative filtering reduces false positives but can increase false negatives.

The reported 100.0% accuracy and precision values apply only to the manually audited 27-person verification subset, not to the complete redaction system.
