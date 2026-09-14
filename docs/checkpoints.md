# Checkpoint ledger

## 1 — Product and data
Recovered the source conversation's architecture, portfolio intent and staged evaluation approach. Wrote the product brief before the first run. Built 180 fictional records, 114 questions, three fetched DOE references and a bounded 40-row RAGBench TechQA diagnostic. Resolved model revisions and saved source hashes. Existing mirrored project files were left untouched.

## 2 — Baseline
Ran fixed-chunk MiniLM dense retrieval and exact evidence answers. Development Recall@5 was 0.667. Source-span integrity was perfect by construction, while citation relevance was low. This distinction is retained throughout the documentation.

## 3 — Measured retrieval improvements
Semantic chunking failed the development promotion gate. Hybrid retrieval passed. Rewriting/expansion failed. Cross-encoder reranking passed. Source-grounded graph expansion improved the development multi-hop slice from 0.250 (reranked retrieval) to 0.500. The combined router passed an independent development comparison. The selected retrieval configuration was frozen before held-out queries were run.

## 4 — Held-out and external diagnostics
Ran the 57-question held-out synthetic set, 40-question external sample and local FLAN generation. Added a separate six-question public-source diagnostic. Reports include per-query rankings, citation spans, timings and measured local token counts. Full EnterpriseRAG-Bench execution was not performed and is explicitly excluded from claims.

## 5 — Browser-driven correctness fix
The Alpha delay workflow displayed a Beta status excerpt alongside Alpha's evidence. Alpha belongs to the development partition. Added an explicit named-project filter to evidence presentation and a regression test; reran development answer evaluation before held-out answers. Kept retrieval configuration fixed and preserved the original held-out report. Citation relevance improved without changing retrieval recall. Generation was rerun after this answer-layer correction.

## 6 — Runtime, security and packaging
Implemented API/UI, local ingestion, ACL-scoped retrieval/graph/cache, source lookup, rate limits, bounded bodies, structured request traces, conservative output validation, model bootstrap, Docker definitions and a CI inference regression script. Ran 21 tests, fresh model-backed regression and browser interaction. Exact local model inference ran successfully. Docker and hosted GitHub Actions were not executed because the necessary runtime/remote repository was not available.

## Remaining limits
This is a completed local portfolio implementation with bounded evaluations, not production certification. Human semantic evaluation, full enterprise benchmarking, broader graph extraction, large-scale storage, concurrent load and independent security review remain future validation work. The product brief's synthetic retrieval targets were met; answer relevance remains an openly reported weakness.
