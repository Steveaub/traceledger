# Human review: pending

These sheets contain 30 frozen held-out answers, stratified across ten categories with seed 42. Labels are deliberately blank. **No human judgment or human/proxy agreement result has been collected yet.**

Work from `answers.csv` and `citations.csv`. Use `yes` or `no` and a pseudonymous `reviewer_id`; add notes for uncertainty. Do not inspect automated relevance labels before judging. Consult the full source documents in `data/synthetic/documents.jsonl` or `data/public/documents.jsonl` when a quote lacks context.

- **Answer relevance:** yes if the answer directly addresses the question without unrelated or contradictory content. For an unsupported question, appropriate abstention is relevant; merely topical prose is not. Judge usefulness and relevance, not prose style.
- **Citation relevance:** yes if the quoted passage supports the requested fact for the correct project, identifier and time. Topic overlap or presence in a relevant document is insufficient.

If a case is ambiguous, record a provisional yes/no label and explain the ambiguity. Ideally have a second person adjudicate disagreements. The script computes agreement with proxies, not inter-rater reliability or objective truth.

The answer proxy is frozen as gold-term coverage >= 0.8, or correct abstention for an unsupported question. Citation proxy labels are document-level membership. These are operational comparison rules, not definitions of correctness. The sample includes passing and failing proxy cases; no successful cases were cherry-picked.

After completing every label, run:

```bash
python scripts/score_human_review.py --output reports/human-review-001.json
```

The scorer refuses incomplete labels, duplicate rows, an altered source report, or an existing output file. It cannot verify that the operator-supplied labels were actually written by a human; reviewer provenance must be documented honestly. Preserve the original blank sheets and previous completed reviews.
