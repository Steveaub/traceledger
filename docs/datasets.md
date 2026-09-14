# Dataset choices and provenance

Research and acquisition date: 13 September 2026. See `data/source-manifest.json` for raw hashes and fetch timestamps.

| Source | Decision | Why / limits |
|---|---|---|
| [EnterpriseRAG-Bench](https://huggingface.co/datasets/SJChen02/EnterpriseRAG-Bench) | Selected for a future scale run; inspected ten question records | Closest match to internal project knowledge and cross-source questions. MIT according to the card. The full collection is far larger than this local diagnostic; no full-corpus result is claimed. |
| [RAGBench](https://huggingface.co/datasets/galileo-ai/ragbench), TechQA subset | Downloaded and evaluated first 40 test rows | Technical enterprise questions with sentence relevance annotations. CC-BY-4.0 on dataset card; retain upstream source attribution and review upstream terms before redistribution. Pooling supplied contexts makes a convenient bounded retrieval test, not an official score. |
| [DOE microgrid checklist page](https://www.energy.gov/cmei/femp/articles/microgrid-system-project-development-checklist) | Downloaded main-page text | Project development context; this snapshot is the landing page, not the linked PDF checklist. |
| [DOE distributed energy project process](https://www.energy.gov/cmei/femp/process-planning-and-implementing-federal-distributed-energy-projects) | Downloaded main-page text | Real project-management phases and terminology. |
| [DOE Microgrid Systems](https://www.energy.gov/oe/microgrid-systems) | Downloaded main-page text | Real technical definition, operating modes and program context. |

The synthetic corpus is original fictional material: 12 charters plus incident, risk, change, lesson, decision, current/old status, RFI, minutes, vendor, handover and routine records for each project. It intentionally contains recurring equipment, similar vendor names, superseded forecasts, and ordinary records without decisive information. The generator authors a known universe before rendering records and questions. `synthetic/universe.json` is evaluation/design material, not a runtime lookup table.

Public text is acquired through a fixed allowlist with retries, HTML cleaning and size checks. Hugging Face Viewer splits are resolved before downloading rows; truncated cells fail the importer. Raw snapshots stay under ignored `data/raw`, while a manifest records hashes. The exact sampled TechQA contexts stay local under ignored `data/external`; the release archive includes the importer and measured reports. Fetching again may retrieve an upstream revision with different text; compare hashes before claiming reproduction.

## Attribution
RAGBench: *RAGBench: Explainable Benchmark for Retrieval-Augmented Generation Systems*, [paper](https://arxiv.org/abs/2407.11005), dataset published by Galileo. Use the dataset's current recommended author citation for formal publication.

EnterpriseRAG-Bench: Yuhong Sun and coauthors, *EnterpriseRAG-Bench: A RAG Benchmark for Company Internal Knowledge*, [paper](https://arxiv.org/abs/2605.05253).

DOE/FEMP/Office of Electricity: source links above. Federal website content can include separately protected third-party material; TraceLedger retains source attribution and does not grant new rights to it.

Embedding: [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), downloaded via Qdrant's ONNX export. Reranker: [Xenova/ms-marco-MiniLM-L-6-v2](https://huggingface.co/Xenova/ms-marco-MiniLM-L-6-v2). Generator: [google/flan-t5-small](https://huggingface.co/google/flan-t5-small). Immutable revisions are in `config/model-manifest.json`.
