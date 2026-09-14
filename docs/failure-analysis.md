# Failure analysis from the measured held-out run

This file is generated from reports; examples are actual outputs. Empty relevance sets are excluded from retrieval metrics.

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
