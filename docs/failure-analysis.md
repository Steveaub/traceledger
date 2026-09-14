# Failure analysis from the measured held-out run

The metrics below come from committed reports; examples are actual outputs. The citation review is a separately labeled AI-assisted analysis. Empty relevance sets are excluded from retrieval metrics.

| Category | Recall@5 | MRR | nDCG@5 |
|---|---:|---:|---:|
| change_impact | 1.000 | 1.000 | 1.000 |
| conflict | 1.000 | 1.000 | 1.000 |
| decision | 0.583 | 0.917 | 0.627 |
| direct | 1.000 | 0.250 | 0.431 |
| exact | 1.000 | 1.000 | 1.000 |
| lesson | 1.000 | 1.000 | 1.000 |
| multi_hop | 0.500 | 1.000 | 0.637 |
| risk | 1.000 | 0.806 | 0.855 |
| semantic | 0.667 | 1.000 | 0.765 |

## Lowest-recall examples

### PRJ-007-decision

Why did DEC-007 move the milestone?

Recall: 0.500. Relevant: PRJ-007-decision, PRJ-007-incident. Returned: PRJ-007-decision, PRJ-002-incident, PRJ-006-incident, PRJ-010-incident, PRJ-010-decision.

### PRJ-007-multi_hop

Which active projects use the equipment affected by INC-007, and what lesson follows that incident?

Recall: 0.500. Relevant: PRJ-007-incident, PRJ-007-lesson, PRJ-007-charter, PRJ-011-charter. Returned: PRJ-007-incident, PRJ-007-lesson, PRJ-007-decision, PRJ-007-change, PRJ-003-charter.

### PRJ-008-decision

Why did DEC-008 move the milestone?

Recall: 0.500. Relevant: PRJ-008-decision, PRJ-008-incident. Returned: PRJ-008-decision, PRJ-002-incident, PRJ-006-incident, PRJ-010-incident, PRJ-010-decision.

### PRJ-008-multi_hop

Which active projects use the equipment affected by INC-008, and what lesson follows that incident?

Recall: 0.500. Relevant: PRJ-008-incident, PRJ-008-lesson, PRJ-008-charter, PRJ-012-charter. Returned: PRJ-008-incident, PRJ-008-lesson, PRJ-008-decision, PRJ-008-change, PRJ-004-charter.

### PRJ-009-decision

Why did DEC-009 move the milestone?

Recall: 0.500. Relevant: PRJ-009-decision, PRJ-009-incident. Returned: PRJ-009-decision, PRJ-002-incident, PRJ-006-incident, PRJ-010-incident, PRJ-010-decision.

### PRJ-009-multi_hop

Which active projects use the equipment affected by INC-009, and what lesson follows that incident?

Recall: 0.500. Relevant: PRJ-009-incident, PRJ-009-lesson, PRJ-005-charter, PRJ-009-charter. Returned: PRJ-009-incident, PRJ-009-lesson, PRJ-009-decision, PRJ-009-change, PRJ-001-charter.

## Missing-answer errors

- What is the secret access token for the grid controller? → returned evidence instead of abstaining.

- What is the final approved contract value of Project Alpha? → returned evidence instead of abstaining.


## Citation relevance: review of the saved held-out run

The 56.3% citation relevance figure is a mean of per-answer relevance fractions. The counts below count individual rejected citation occurrences, so they have a different denominator. Every rejected passage was inspected in an AI-assisted review; these are **not human-validated labels**. The source report was not regenerated or changed. Full passages, labels, rationales and its SHA-256 are in [the review artifact](../reports/citation-error-review.json).

| Bucket | Rejected citation occurrences |
|---|---:|
| Wrong project | 61 |
| Right project, wrong artifact | 55 |
| Superseded or stale record | 0 |
| Other: unsupported question answered | 6 |

Correct document but off-question: **not measurable from this rejected-document subset**. A citation from a gold document always passes the current proxy, regardless of which sentence it quotes. The separate human-review sample includes those passing citations too.

Examples: CR-007 pulls requirement passages from Alpha/Falcon rather than Granite; Granite equipment/vendor questions cite routine meeting attendance instead of the charter; a grid-controller secret question receives public microgrid prose instead of abstaining. No superseded records were observed in this flagged subset, consistent with current-record filtering. Repeated similar project templates make cross-project fillers particularly hard to distinguish.

Future work, not silently applied: enforce entity/project consistency for identifier questions, gate final excerpts by question facet, and improve abstention for unsupported questions. Evaluate these on new development cases and an independently authored holdout before replacing any reported result. Human adjudication may identify incomplete gold relevance labels; preserve disagreements rather than rewriting the benchmark to match output.
