# TraceLedger: product brief and acceptance criteria

## Problem and users
Project managers, technical program managers and engineers need timely, verifiable answers across fragmented charters, risk registers, changes, incidents and lessons. TraceLedger retrieves evidence and follows documented relationships across fictional microgrid projects. It supports decisions; it does not approve engineering changes or operate equipment.

## First release
Local, reproducible Python application with an API and browser UI. Three clearly separated datasets: a deterministic synthetic project universe, fetched public technical references, and a bounded external Hugging Face benchmark. No confidential project records. No claims of enterprise-scale validation from a small sample.

## Acceptance criteria (declared before benchmarking)
- Synthetic held-out project retrieval: Recall@5 >= 0.80, MRR >= 0.75, nDCG@5 >= 0.70; report failures even if targets are missed.
- Citation integrity: every displayed citation resolves to an indexed source span; unsupported generated claims are rejected by the conservative quote validator.
- Quality: report citation precision against relevance labels, evidence coverage, extractive faithfulness and answer relevance proxies separately from any semantic/human judge scores. Never present a proxy as human evaluation.
- Retrieval p95 <= 2 seconds on this machine after model warmup; report generation time separately, plus cold indexing time and cache state.
- No invented spending: report actual API charges only when returned/known; local API spend is $0, electricity and hardware cost are unmeasured.
- No cross-project disclosure when an API principal lacks access. Exercise retrieval, graph expansion, citations and caching under access restrictions.
- Ingestion rejects invalid/oversized documents; sources are data, never tools or privileged instructions. Red-team tests cover injected instructions, HTML payloads and unauthorized access.
- Reproducibility: fixed seeds, corpus/query hashes, pinned model revisions, per-query outputs, metrics definitions, tests and CI regression gates.

## Stage gates
1. Freeze corpus, question splits and baseline configuration; run fixed-chunk dense retrieval.
2. Compare semantic chunking, hybrid retrieval, expansion and reranking on development queries. Promote only if Recall@5 increases >= 0.02 without nDCG dropping > 0.02, or nDCG improves >= 0.02 without recall dropping > 0.02; p95 must remain <= 2 seconds.
3. Evaluate graph paths separately on relationship questions. Keep graph optional unless that slice improves by >= 0.05 Recall@5 with no unauthorized evidence.
4. Freeze the selection before final held-out evaluation. Never tune against final-test outputs. Retain rejected variants as experiments, disabled by default.
5. Verify API/UI, security, packaging, docs and demo. Record unmet criteria as limitations, not successes.

## Scope and tradeoffs
Use a local exact dense-vector index and a provenance-carrying graph first. Move to pgvector/Neo4j only when corpus size or operations require them. An extractive evidence mode runs without paid credentials; a local generative model is evaluated separately where available. Public technical references describe real systems; synthetic operational recommendations are fictional and labelled.
