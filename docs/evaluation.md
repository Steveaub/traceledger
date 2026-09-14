# Evaluation protocol

## What the reported numbers mean
- Recall@5: relevant unique documents retrieved / all labelled relevant documents. Unanswerable queries are excluded, not scored as perfect recall.
- MRR: reciprocal rank of the first relevant document within the returned five; zero when absent.
- nDCG@5: binary document relevance with log2 discount, divided by ideal DCG.
- Citation accuracy: fraction of emitted citations whose documents are in the question's relevance labels. This tests relevance of the cited document, not entailment of an arbitrary claim.
- Citation integrity: fraction of citations whose exact character span equals the original document. Empty citation sets are null, not one.
- Faithfulness (exact-quote proxy): verified source-span fraction. This is useful for this extractive system; it is **not** an independent semantic faithfulness score or a claim that misleading evidence is impossible.
- Answer relevance (gold-term coverage proxy): fraction of predeclared answer terms present in the displayed answer. It is sensitive to wording and can reward verbose excerpts. It is null for external rows without independent answer terms.
- Abstention correctness: predicted missing-answer state versus empty relevance labels. Reported across all queries; inspect the unanswerable slice separately because most questions are answerable.
- Latency: actual wall-clock retrieval and total answer time, p50/p95, warmed sessions, answer cache disabled. Local model startup, network model downloads and concurrent load are excluded. Single sequential pass; timings are measurements, not a service SLA.
- Cost: local calls incur zero external API spend. Hardware, power and amortization are unmeasured/null. Tokens are counted for FLAN, without pretending local tokens have an API price.

## Data and split discipline
180 deterministic fictional documents across 12 projects. Six projects provide development question templates and six provide held-out questions; three missing-answer questions appear in each split. The retrieval corpus includes all projects, as a deployed corpus would. Shared templates, equipment and mitigations make this a controlled engineering regression set rather than proof of broad generalization. Graph labels derive from the same authored project universe; edges are source-validated but not automatically extracted. This advantage must be disclosed.

The 40-row RAGBench TechQA diagnostic pools 200 supplied context documents into a small retrieval collection. Document relevance is mapped from supplied relevant sentence keys. Ten sampled rows have no labelled relevant context. These are partial diagnostic measurements, **not** the RAGBench leaderboard or full TechQA retrieval corpus. EnterpriseRAG-Bench was inspected and selected as the scaling benchmark; its 500k-document run is not claimed.

Six public-reference questions are a post-selection diagnostic and do not influence configuration selection. JSON reports preserve every query, ranking, answer, citation and latency. Source manifests preserve downloaded snapshot hashes; model manifests pin immutable revisions.

## Stage gates
The product brief predates baseline execution. `reports/development.json` records experiments, promotion decisions and per-category results. Candidates add one feature to the current accepted configuration, so this is sequential selection, not a full factorial study. Graph is evaluated on multi-hop development questions. The router is separately measured before freezing. `selection.json` records the freeze timestamp; `heldout.json` contains the resulting final comparison. Do not keep tuning against these test questions: author an independent next release test set.

Bootstrap intervals resample queries 1,000 times with seed 42. Correlated templates violate independent-query assumptions; these intervals are descriptive and may be optimistic. No significance claim is made. Security tests are separate from retrieval promotion, so high recall cannot override an access-control failure.

## What remains unmeasured
Independent human relevance/faithfulness ratings, inter-rater agreement, answer usefulness in real PM workflows, large enterprise retrieval, adversarial prompt-injection coverage beyond the included suite, concurrent throughput, Docker runtime and hosted CI execution. No external LLM judge was called and no paid inference was used.

## Corpus schema and historical fingerprints

The corpus fingerprint covers the ordered, parsed document models serialized with sorted keys. It includes metadata and default values; it is neither a text-only hash nor the hash of the raw JSONL file.

The original 183-document benchmark used a ten-field document schema and fingerprint `0d0ed2e1611e303c148716295f2cb801e4b931c8da0a3df50c61ef4ada52ab75`. Conversation support added four defaults to the document model. Current parsing therefore produces `ef1ee84c6485502137c282f5de998d7ba3b01eb931048cd1d0f07729ca12114d` for that same document set, even when those defaults are absent from JSONL. The legacy fingerprint does **not** reproduce under the current full-schema hash; it reproduces exactly under the original ten-field projection. Historical reports and run identifiers remain unchanged.

Regenerating the 180 synthetic records materializes those defaults without changing any existing field, document text, questions, or universe entries. Parsed before/after fingerprints are identical. The 255-document investigation corpus remains `76226b6b650bae985d59cebc056cc1b43573236e6ddca96113ed6d8e934d489c`. See the [schema audit](../reports/corpus-schema-audit.json). This migration adds no performance result and does not merge historical and current evaluation cohorts.
