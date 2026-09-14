"""Matched-corpus single-pass vs bounded investigation. No label access at runtime."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas.corpus import ROOT, DATA, load_questions
from atlas.schema import Document, QueryRequest
from atlas.retrieval import Encoder, Index
from atlas.service import Service
from atlas.evaluate import retrieval_metrics, answer_metrics, aggregate
from atlas.history import record_run
from atlas.investigator import investigate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare fresh metrics with the saved release before writing this run",
    )
    args = parser.parse_args()
    reference = (
        json.loads(
            (ROOT / f"reports/investigation-{args.split}.json").read_text(
                encoding="utf-8"
            )
        )
        if args.check
        else None
    )
    docs = [
        Document.model_validate_json(line)
        for folder in ("synthetic", "public", "conversations")
        for line in (DATA / folder / "documents.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    index = Index(docs, Encoder(), persist=False)
    service = Service(index)
    projects = sorted({d.project for d in docs})
    qs = [
        q
        for q in load_questions(DATA / "conversations/questions.jsonl")
        if q.split == args.split
    ]
    results = {}
    for mode in ("auto", "investigate"):
        rows = []
        service.query(
            QueryRequest(
                query="warmup project acceptance",
                sources=["documents", "email", "slack", "teams"],
            ),
            projects,
        )
        started_at = datetime.now(timezone.utc).isoformat()
        for q in qs:
            service.cache.clear()
            index.encoder.cache.clear()
            started = time.perf_counter()
            request = QueryRequest(
                query=q.query,
                mode="investigate",
                sources=["documents", "email", "slack", "teams"],
            )
            answer = investigate(
                index, request, projects, max_actions=1 if mode == "auto" else 6
            )
            answer["investigation"]["max_actions"] = 1 if mode == "auto" else 6
            ranked = answer.get(
                "ranked", list(dict.fromkeys(c["doc_id"] for c in answer["citations"]))
            )
            row = dict(
                id=q.id,
                query=q.query,
                category=q.category,
                ranked=ranked,
                relevant=q.relevant,
                path=answer["path"],
                **retrieval_metrics(ranked, q.relevant),
                **answer_metrics(answer, q, index.docs),
                retrieval_ms=answer["retrieval_ms"],
                total_ms=(time.perf_counter() - started) * 1000,
                answer=answer,
            )
            # Full evidence coverage uses all returned citations, separate from @5 metrics.
            row["evidence_recall"] = (
                len(set(ranked) & set(q.relevant)) / len(q.relevant)
                if q.relevant
                else None
            )
            row["actions"] = len(answer.get("investigation", {}).get("steps", []))
            rows.append(row)
        result = {
            "config": {
                "name": "Single-pass matched selector"
                if mode == "auto"
                else "Bounded investigator",
                "mode": mode,
            },
            "summary": aggregate(rows),
            "slices": {
                cat: aggregate([r for r in rows if r["category"] == cat])
                for cat in sorted({r["category"] for r in rows})
            },
            "rows": rows,
        }
        result["summary"]["mean_actions"] = sum(r["actions"] for r in rows) / len(rows)
        result["summary"]["evidence_recall"] = sum(
            r["evidence_recall"] for r in rows if r["evidence_recall"] is not None
        ) / sum(r["evidence_recall"] is not None for r in rows)
        result["run_id"] = record_run(
            result,
            index,
            qs,
            started_at=started_at,
            public_demo=not args.check,
            protocol="atlas-investigation-evidence-v2",
            generation="evidence",
        )
        results[mode] = result
        print(mode, json.dumps(result["summary"]), flush=True)
    if reference:
        for mode in results:
            for metric, tolerance in [
                ("recall", 0.02),
                ("citation_accuracy", 0.02),
                ("citation_integrity", 0),
                ("abstention_correct", 0),
            ]:
                assert (
                    results[mode]["summary"][metric]
                    >= reference[mode]["summary"][metric] - tolerance
                ), (mode, metric)
            assert results[mode]["summary"]["total_p95_ms"] < 5000, (
                "Investigation latency ceiling exceeded"
            )
        print("Investigation regression thresholds passed.", flush=True)
    else:
        (ROOT / f"reports/investigation-{args.split}.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
