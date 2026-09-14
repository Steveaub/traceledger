"""Append-only, versioned evaluation artifacts; no invented historical runs."""
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from atlas.corpus import ROOT

PROTOCOL = "atlas-document-eval-v2"
HISTORY = ROOT / "reports/runs"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def code_version():
    return digest({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted((ROOT / "atlas").glob("*.py"))})


def record_run(result, index, questions, *, started_at, routing=False,
               graph_enabled=False, generation="evidence", directory=None, public_demo=False, protocol=PROTOCOL):
    folder = Path(directory) if directory is not None else HISTORY
    folder.mkdir(parents=True, exist_ok=True)
    qhash = digest([q.model_dump() for q in questions])
    finished = datetime.now(timezone.utc).isoformat()
    model_path = ROOT / "config/model-manifest.json"
    models = json.loads(model_path.read_text()) if model_path.exists() else {}
    cohort = {"corpus": index.fingerprint, "questions": qhash,
              "protocol": protocol, "k": 5, "generation": generation}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:12]
    record = {"id": run_id, "started_at": started_at, "finished_at": finished,
              "protocol": protocol, "cohort_id": digest(cohort),
              "corpus_sha256": index.fingerprint, "questions_sha256": qhash,
              "code_sha256": code_version(), "models": models,
              "split": ", ".join(sorted({q.split for q in questions})),
              "generation": generation, "routing": routing, "graph_enabled": graph_enabled,
              "cache_policy": "warm sessions; answer cache disabled; query embeddings evicted",
              "visibility": "demo" if public_demo else "restricted", **result}
    # Exclusive create plus atomic publication prevents overwriting or partial reads.
    temporary = folder / (run_id + ".tmp")
    target = folder / (run_id + ".json")
    with temporary.open("x", encoding="utf-8") as file:
        json.dump(record, file, indent=2, allow_nan=False)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, target)
    return run_id


def read_run(run_id, directory=None):
    if not re.fullmatch(r"\d{8}T\d{6}-[a-f0-9]{12}", run_id):
        raise ValueError("Invalid run identifier")
    folder = Path(directory) if directory is not None else HISTORY
    return json.loads((folder / f"{run_id}.json").read_text(encoding="utf-8"))


def list_runs(directory=None):
    folder = Path(directory) if directory is not None else HISTORY
    records = []
    for path in sorted(folder.glob("*.json"), reverse=True):
        try:
            record = read_run(path.stem, folder)
            records.append({k: v for k, v in record.items() if k != "rows"})
        except (ValueError, OSError):
            continue
    return records


def compare_runs(before, after):
    if before["cohort_id"] != after["cohort_id"]:
        raise ValueError("Choose runs with the same corpus, questions, protocol and answer mode")
    deltas = {}
    for metric in ("recall", "mrr", "ndcg", "citation_accuracy", "citation_integrity",
                   "relevance_gold_term_coverage", "abstention_correct", "retrieval_p95_ms"):
        a, b = before["summary"].get(metric), after["summary"].get(metric)
        if a is not None and b is not None:
            deltas[metric] = b - a
    older = {row["id"]: row for row in before["rows"]}
    changes = []
    for row in after["rows"]:
        old = older.get(row["id"])
        if old and row.get("mrr") is not None and old.get("mrr") is not None:
            changes.append({"id": row["id"], "query": row["query"],
                            "before_mrr": old["mrr"], "after_mrr": row["mrr"],
                            "delta": row["mrr"] - old["mrr"]})
    return {"before": before["id"], "after": after["id"], "deltas": deltas,
            "regressions": [k for k, v in deltas.items() if k != "retrieval_p95_ms" and v < -0.02],
            "questions": sorted(changes, key=lambda r: r["delta"])}
