"""Render documentation from saved measurements, never handwritten scores."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT/f"reports/{name}.json").read_text())
def row(label,s):
    return f"| {label} | {s['recall']:.3f} | {s['mrr']:.3f} | {s['ndcg']:.3f} | {s['retrieval_p95_ms']:.1f} |"
dev=read("development")
held=read("heldout")
ext=read("external")
public=read("public")
gen=read("generation")
table="| Configuration | Recall@5 | MRR@5 | nDCG@5 | Retrieval p95 ms |\n|---|---:|---:|---:|---:|\n"
dev_table=table+"\n".join(row(x.get("experiment",x['config']['name']),x['summary']) for x in dev['experiments'])
final_table=table+"\n".join([row("Synthetic held-out / vector baseline",held['baseline']['summary']),row("Synthetic held-out / selected router",held['selected']['summary']),row("TechQA sample / vector baseline",ext['baseline']['summary']),row("TechQA sample / selected hybrid + reranker",ext['selected']['summary']),row("DOE reference diagnostic / selected",public['summary'])])
s=held['selected']['summary']
g=gen['summary']
accepted=sum(r['answer'].get('draft_accepted',False) for r in gen['rows'])
readme=f'''# TraceLedger
### Grounded project intelligence for complex technical programs

Project teams accumulate decisions, risk registers, incident reports and lessons faster than they can reuse them. **TraceLedger retrieves the evidence, connects documented relationships and shows the source behind an answer.** Microgrid projects provide the first demonstration domain; every operational project record is clearly fictional.

This repository is a working local portfolio system with measured retrieval experiments, a FastAPI service, browser UI, source-grounded graph, local inference, security tests and reproducible benchmark reports. It is not an enterprise deployment or a claim of independently validated answer quality.

## Demo first

Start the app and open **http://127.0.0.1:8000**. Use the workflow cards:

- “What caused Project Alpha to fall behind its commissioning schedule?”
- “Trace the requirement and incident linked to CR-001.”
- “Which active projects use the equipment affected by INC-001, and what lesson follows that incident?”
- “What should we learn from Project Alpha before releasing a purchase order?”
- “What triggers RISK-001 and what response is planned?”

The interface displays exact source excerpts, fictional/public labels and graph evidence. Local AI mode runs FLAN-T5-small, checks its draft against source spans, and falls back to excerpts when validation fails. **Source excerpts remain the default because the small model was less complete.** See the [usage examples](docs/usage-examples.md).

## Real measured results

Executed locally on Windows, Python 3.12, CPU inference with two model threads. Five unique documents per query; model sessions warmed, answer caching disabled. Full per-query data, corpus hashes and model revisions are in [reports](reports/). Hardware/electricity costs are unmeasured; measured external API spend was $0.

{final_table}

Synthetic final test: 57 questions, 54 answerable. Development: a separate 57 questions. The TechQA test is only 40 sampled RAGBench rows pooled into 200 context documents, **not an official benchmark score**. DOE diagnostic: six questions, too small for a generalization claim.

Held-out citation span integrity: **{s['citation_integrity']:.1%}**. Citation relevance accuracy: **{s['citation_accuracy']:.1%}**. Gold-term answer coverage: **{s['relevance_gold_term_coverage']:.1%}**. These differ: a verbatim quote can still be irrelevant. Exact-quote faithfulness is a mechanical proxy, not a human or independent LLM judgment.

Local FLAN evaluation: {accepted}/{len(gen['rows'])} queries produced a fully accepted literal draft. Displayed answer coverage was {g['relevance_gold_term_coverage']:.1%}; total p95 was {g['total_p95_ms']:.1f} ms. Rejected drafts fall back to evidence; see [raw generation results](reports/generation.json). Do not claim a zero hallucination rate from this validation rule.

### What earned its place

{dev_table}

Semantic chunking and rule-based rewriting/expansion were implemented, measured and rejected for the default. Hybrid search and reranking passed development gates. Graph traversal improved the multi-hop slice, and the router separately passed its promotion gate. See [selection decisions](reports/selection.json). The named-project evidence filter was added after an Alpha development UI check exposed mixed-project excerpts; original held-out outputs are retained in [the pre-fix report](reports/heldout-before-answer-fix.json).

## Architecture

```mermaid
flowchart LR
  D[Validated documents + provenance] --> C[Chunking]
  C --> V[MiniLM dense index]
  C --> B[BM25]
  D --> G[Evidence-backed graph]
  Q[Question + server ACL] --> R[Measured router]
  R --> V
  R --> B
  R --> G
  V --> F[Fusion / cross-encoder]
  B --> F
  G --> F
  F --> A[Evidence or local AI draft]
  A --> S[Span validation]
  S --> UI[Answer + citations]
```

The graph includes projects, vendors, sites, equipment, risks, incidents, changes, lessons, decisions, requirements and milestones. Each relationship carries a document and exact supporting text. ACL checks apply during expansion, not just after it. See [architecture and entity diagrams](docs/architecture.md).

## Voice controls

Use **Speak question** to dictate and review before submitting. **Listen** speaks the displayed answer using a local English voice and changes to **Stop** during playback. Browser dictation may use an online service. See [voice support and privacy](docs/voice.md).

## Evaluation lab and polished workspace

The workspace now separates questions, concise evidence excerpts, and expandable source cards. Citation buttons open the exact source; project scoping, keyboard submission, loading/error states, and one Listen/Stop control support the demo flow. Layouts adapt to desktop and mobile.

**Evaluation lab** shows append-only measured run history, MRR/Recall/nDCG/citation trends, compatible-run comparisons, latency tradeoffs, code/data/model versions, and question-level failures with search and pagination. No simulated history is used. Run `python scripts/evaluate_release.py` to add four fresh bundled-data runs, then Refresh runs in the dashboard. Private evaluation results require a server-configured evaluator role.

[Evaluation history guide](docs/evaluation-history.md)

## How it works

1. A deterministic universe produces 180 fictional records across 12 projects, including old forecasts and distractors. Three DOE pages are fetched with provenance; an external TechQA sample is kept separate.
2. Validated documents become fixed chunks and 384-dimensional MiniLM vectors. BM25 preserves exact IDs; optional semantic chunks split on adjacent sentence meaning.
3. The router sends identifier queries to hybrid retrieval and relationship queries to source-backed graph expansion. General questions use hybrid retrieval plus a cross-encoder over 20 candidates.
4. Answers quote exact source spans. Local generation is optional and conservatively validated. Unanswerable handling is imperfect and measured.
5. The API enforces server-owned project scopes, input limits, rate limits, scoped TTL caching and structured traces. Offline ingestion supports TXT, Markdown and PDF. No document can invoke tools.

## Evaluation and tradeoffs

Start with [the product brief and declared success criteria](docs/product-brief.md), [evaluation definitions](docs/evaluation.md), and [dataset selection/provenance](docs/datasets.md). Recall, MRR and nDCG are document-level; citation accuracy measures relevance-label membership; relevance and faithfulness have explicitly named proxy definitions. External answer terms are unavailable and reported null.

The exact NumPy vector index and NetworkX graph keep the local system auditable and easy to run. They are not replacements for pgvector/Neo4j at scale. Graph edges are authored source assertions, not an evaluated general-purpose entity extraction model. Current/superseded flags are explicit metadata, not automatic conflict resolution. The development and held-out synthetic templates are related, so impressive scores here do not prove real-world generalization.

## Failure modes worth showing

- Broad graph expansion misses parts of active-project multi-hop questions and includes related but unnecessary incidents.
- Citations can be exact yet irrelevant; the citation-accuracy result exposes this.
- Missing-answer detection can answer a question that the corpus does not resolve.
- Small-model answers can omit important evidence or fail validation; excerpt fallback is intentional.
- Source metadata can be wrong; literal validation cannot establish whether a document is true or current.
- Tokenization may truncate dense model inputs; fixed word counts do not guarantee a token budget.
- The synthetic vocabulary/templates and curated graph make this easier than messy enterprise ingestion.

## Setup

Requires Python 3.12 and outbound access only for dependency/model/data downloads. No paid API key is needed. From this repository directory:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[test]"
python scripts/bootstrap_models.py --retrieval-only
python -m atlas.corpus
python scripts/fetch_data.py
```

The downloaded public records and synthetic corpus are already included in the source release; fetching is required to reproduce external TechQA evaluation. Model downloads use the committed immutable revision manifest. Never commit access tokens or private project documents.

Run the local demo:

```powershell
$env:ATLAS_DEMO="1"
python -m uvicorn atlas.api:app --host 127.0.0.1 --port 8000
```

On macOS/Linux, use `ATLAS_DEMO=1 python -m uvicorn atlas.api:app --host 127.0.0.1 --port 8000`. Without demo mode, configure `ATLAS_PRINCIPALS_JSON` following [.env.example](.env.example); load it via your shell or deployment environment. The application does not automatically read `.env`.

Optional real local generation:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install "transformers==4.57.6" "sentencepiece==0.2.2"
python scripts/bootstrap_models.py
```

Tests and benchmarks:

```bash
python -m pytest -q
python -m atlas.evaluate --stage baseline
python -m atlas.evaluate --stage all
python scripts/public_eval.py
python scripts/regression.py
python scripts/render_report.py
```

`--stage all` includes local generation and requires the optional dependencies. `--stage external` and `--stage generation` run those diagnostics separately after selection exists. `scripts/regression.py` runs fresh inference against committed quality thresholds; GitHub Actions includes this gate. The CI workflow has been authored, and its commands were exercised locally; hosted CI has not run.

Ingest a reviewed local file, then restart to rebuild:

```bash
python -m atlas.ingest reviewed-note.md --project PRJ-001 --output data/ingested/reviewed-note.jsonl
```

Docker evidence-only demo: `docker compose up --build` after downloading retrieval models. The container is non-root and mounts models read-only; its port is loopback-bound. Docker is not installed on the build machine, so container execution remains unverified. To enable local generation inside Docker, add its optional dependencies explicitly.

## Security and operations

Read [the threat model](docs/security.md). Demo mode exposes only fictional project data and public references. Private deployment defaults to bearer authentication and per-project authorization. Logs omit source text, queries and tokens. A request ID provides local tracing; distributed telemetry, identity federation, parser sandboxing and durable audit storage remain future work. Heuristic injection filtering is not a complete security boundary; no-tool execution and conservative evidence validation are the stronger controls.

## Future work

Independent human annotations; a larger disjoint real-document benchmark; the full EnterpriseRAG-Bench corpus; typed graph predicates for active status and complete paths; learned entity extraction with edge precision evaluation; a stronger independently evaluated generator; token-aware chunking; durable vector/graph storage; concurrent load testing; external identity and distributed tracing. Promote each addition only after a new development test justifies it.

## Portfolio materials

[Usage examples](docs/usage-examples.md) · [architecture diagrams](docs/architecture.md) · [failure analysis](docs/failure-analysis.md) · [checkpoint ledger](docs/checkpoints.md).

Code and original synthetic records are MIT licensed. Third-party models and datasets retain their own licenses and attribution; see [dataset notes](docs/datasets.md). Built with AI assistance; review and reproduce the system before presenting it as your own engineering work.
'''
(ROOT/"README.md").write_text(readme,encoding="utf-8")
fail="""# Failure analysis from the measured held-out run\n\nThis file is generated from reports; examples are actual outputs. Empty relevance sets are excluded from retrieval metrics.\n\n| Category | Recall@5 | MRR | nDCG@5 |\n|---|---:|---:|---:|\n"""
for category,summary in held['selected']['slices'].items():
    if summary['recall'] is not None:
        fail+=f"| {category} | {summary['recall']:.3f} | {summary['mrr']:.3f} | {summary['ndcg']:.3f} |\n"
fail+="\n## Lowest-recall examples\n"
for r in sorted([r for r in held['selected']['rows'] if r['recall'] is not None],key=lambda r:r['recall'])[:6]:
    fail+=f"\n### {r['id']}\n\n{r['query']}\n\nRecall: {r['recall']:.3f}. Relevant: {', '.join(r['relevant'])}. Returned: {', '.join(r['ranked'])}.\n"
fail+="\n## Missing-answer errors\n"
for r in held['selected']['rows']:
    if not r['relevant'] and not r['answer']['abstained']:
        fail+=f"\n- {r['query']} → returned evidence instead of abstaining.\n"
(ROOT/"docs/failure-analysis.md").write_text(fail,encoding="utf-8")
print("Rendered README and failure analysis from saved measurements")
