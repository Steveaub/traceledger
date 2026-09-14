"""Run fresh inference, compare to committed measured quality (not timing noise)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas.corpus import ROOT, DATA, load_questions
from atlas.schema import Document
from atlas.retrieval import Config, Encoder, Index
from atlas.evaluate import run

selection = json.loads((ROOT / "reports/selection.json").read_text())
config = Config(**selection["selected"])
# Preserve the original benchmark corpus; conversations use their own cohort.
# Never mix private operator imports into CI or portfolio measurements.
docs = [
    Document.model_validate_json(line)
    for folder in ("synthetic", "public")
    for line in (DATA / folder / "documents.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]
index = Index(docs, Encoder(), semantic=config.chunking == "semantic", persist=False)
result = run(
    index,
    [q for q in load_questions() if q.split == "test"],
    config,
    routing=selection["router_enabled"],
    graph_enabled=selection["graph_enabled"],
)
baseline = json.loads((ROOT / "reports/heldout.json").read_text())["selected"][
    "summary"
]
for metric, tolerance in [
    ("recall", 0.02),
    ("mrr", 0.02),
    ("ndcg", 0.02),
    ("citation_integrity", 0),
    ("abstention_correct", 0.02),
]:
    assert result["summary"][metric] >= baseline[metric] - tolerance, (
        metric,
        result["summary"][metric],
        baseline[metric],
    )
assert result["summary"]["retrieval_p95_ms"] < 5000, "CI CPU latency ceiling exceeded"
print(json.dumps(result["summary"], indent=2))
