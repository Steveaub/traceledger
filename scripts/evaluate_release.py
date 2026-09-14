"""Record comparable, real benchmark runs for the portfolio dashboard.

Only bundled fictional/public records are loaded; uploads are excluded.
No production configuration is automatically promoted by this command.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas.corpus import ROOT, DATA, load_questions
from atlas.schema import Document
from atlas.retrieval import Config, Encoder, Index
from atlas.evaluate import run

docs = [
    Document.model_validate_json(line)
    for folder in ("synthetic", "public")
    for line in (DATA / folder / "documents.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]
qs = load_questions()
selection = json.loads((ROOT / "reports/selection.json").read_text())
encoder = Encoder()
baseline = Index(docs, encoder, persist=False)
config = Config(**selection["selected"])
selected = (
    baseline
    if config.chunking == "fixed"
    else Index(docs, encoder, semantic=True, persist=False)
)
for split in ("dev", "test"):
    questions = [q for q in qs if q.split == split]
    for label, index, cfg, routing in [
        ("Vector baseline", baseline, Config(), False),
        ("Selected router", selected, config, selection["router_enabled"]),
    ]:
        report = run(
            index,
            questions,
            cfg,
            routing=routing,
            graph_enabled=selection["graph_enabled"] if routing else False,
            public_demo=True,
        )
        print(split, label, report["run_id"], json.dumps(report["summary"]), flush=True)
