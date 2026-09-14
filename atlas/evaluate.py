"""Executable ablations. Development-only promotion, then frozen held-out run."""

import argparse
import hashlib
import json
import math
import platform
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
import numpy as np
from atlas.corpus import ROOT, DATA, load_docs, load_questions
from atlas.schema import Document
from atlas.retrieval import Encoder, Index, Config, route
from atlas.answer import evidence_answer, LocalGenerator


def retrieval_metrics(ranked, relevant, k=5):
    ranked = list(dict.fromkeys(ranked))[:k]
    gold = set(relevant)
    if not gold:
        return {"recall": None, "mrr": None, "ndcg": None}
    gains = [int(x in gold) for x in ranked]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(gold))))
    return {
        "recall": sum(gains) / len(gold),
        "mrr": next((1 / (i + 1) for i, g in enumerate(gains) if g), 0),
        "ndcg": dcg / ideal,
    }


def answer_metrics(answer, q, docs):
    citations = answer["citations"]
    integrity = [
        c["doc_id"] in docs
        and docs[c["doc_id"]].text[c["start"] : c["end"]] == c["quote"]
        for c in citations
    ]
    relevant = [c["doc_id"] in q.relevant for c in citations]
    terms = q.answer_terms
    return {
        "citation_integrity": sum(integrity) / len(citations) if citations else None,
        "citation_accuracy": sum(relevant) / len(citations) if citations else None,
        "faithfulness_exact_quote": sum(integrity) / len(citations)
        if citations
        else None,
        "relevance_gold_term_coverage": sum(
            t.lower() in answer["answer"].lower() for t in terms
        )
        / len(terms)
        if terms
        else None,
        "abstention_correct": int(answer["abstained"] == (not q.relevant)),
        "api_cost_usd": answer["api_cost_usd"],
    }


def aggregate(rows):
    keys = [
        "recall",
        "mrr",
        "ndcg",
        "citation_integrity",
        "citation_accuracy",
        "faithfulness_exact_quote",
        "relevance_gold_term_coverage",
        "abstention_correct",
        "api_cost_usd",
    ]
    result = {
        k: float(np.mean([r[k] for r in rows if r.get(k) is not None]))
        if any(r.get(k) is not None for r in rows)
        else None
        for k in keys
    }
    result.update(
        queries=len(rows),
        answerable=sum(r["recall"] is not None for r in rows),
        retrieval_p50_ms=float(np.median([r["retrieval_ms"] for r in rows])),
        retrieval_p95_ms=float(np.percentile([r["retrieval_ms"] for r in rows], 95)),
        total_p95_ms=float(np.percentile([r["total_ms"] for r in rows], 95)),
        compute_cost_usd=None,
    )
    vals = [r["recall"] for r in rows if r["recall"] is not None]
    if vals:
        rng = np.random.default_rng(42)
        boots = np.mean(rng.choice(vals, size=(1000, len(vals)), replace=True), axis=1)
        result["recall_bootstrap_95ci"] = np.percentile(boots, [2.5, 97.5]).tolist()
    return result


def run(
    index,
    qs,
    config,
    generator=None,
    routing=False,
    graph_enabled=False,
    history_dir=None,
    public_demo=False,
):
    from atlas.history import record_run

    started_at = datetime.now(timezone.utc).isoformat()
    if not qs:
        raise ValueError("Evaluation requires at least one question")
    rows = []
    # Warm model sessions and code paths, then remove query embedding cache.
    index.search("warmup project acceptance", config)
    for q in qs:
        index.encoder.cache.pop(q.query, None)
        started = time.perf_counter()
        actual = route(q.query, config, graph_enabled) if routing else config
        retrieval = index.search(q.query, actual, projects=q.projects or None)
        answer = (
            generator.answer(q.query, retrieval)
            if generator
            else evidence_answer(q.query, retrieval)
        )
        row = {
            "id": q.id,
            "query": q.query,
            "category": q.category,
            "ranked": [h["doc_id"] for h in retrieval["hits"]],
            "relevant": q.relevant,
            "path": retrieval["path"],
            **retrieval_metrics([h["doc_id"] for h in retrieval["hits"]], q.relevant),
            **answer_metrics(answer, q, index.docs),
            "retrieval_ms": retrieval["retrieval_ms"],
            "total_ms": (time.perf_counter() - started) * 1000,
            "answer": answer,
        }
        rows.append(row)
    result = {
        "config": asdict(config),
        "summary": aggregate(rows),
        "slices": {
            cat: aggregate([r for r in rows if r["category"] == cat])
            for cat in sorted({r["category"] for r in rows})
        },
        "rows": rows,
    }
    result["run_id"] = record_run(
        result,
        index,
        qs,
        started_at=started_at,
        routing=routing,
        graph_enabled=graph_enabled,
        generation="local" if generator else "evidence",
        directory=history_dir,
        public_demo=public_demo,
    )
    return result


def promote(old, new):
    a, b = old["summary"], new["summary"]
    return b["retrieval_p95_ms"] <= 2000 and (
        (b["recall"] >= a["recall"] + 0.02 and b["ndcg"] >= a["ndcg"] - 0.02)
        or (b["ndcg"] >= a["ndcg"] + 0.02 and b["recall"] >= a["recall"] - 0.02)
    )


def save(name, value):
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", choices=["baseline", "all", "generation", "external"], default="all"
    )
    args = parser.parse_args()
    encoder = Encoder()
    docs = load_docs()
    qs = load_questions()
    dev = [q for q in qs if q.split == "dev"]
    test = [q for q in qs if q.split == "test"]
    fixed = Index(docs, encoder)
    meta = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor(),
        "threads": 2,
        "corpus_sha256": fixed.fingerprint,
        "questions_sha256": hashlib.sha256(
            (DATA / "synthetic/questions.jsonl").read_bytes()
        ).hexdigest(),
        "documents": len(docs),
        "models": json.loads((ROOT / "models/manifest.json").read_text()),
        "cache": "warmed sessions; query embeddings evicted; no answer cache; single sequential pass",
        "index_build_ms": fixed.build_ms,
    }
    if args.stage in ("baseline", "all"):
        best_config = Config()
        best = run(fixed, dev, best_config)
        save("baseline-development", {"metadata": meta, **best})
        print("BASELINE", json.dumps(best["summary"]), flush=True)
        if args.stage == "baseline":
            return
        experiments = [best]
        decisions = []
        semantic = Index(docs, encoder, semantic=True)
        for name, updates in [
            ("semantic", {"chunking": "semantic"}),
            ("hybrid", {"hybrid": True}),
            ("expansion", {"expansion": True}),
            ("reranker", {"rerank": True}),
        ]:
            candidate = replace(best_config, name=name, **updates)
            result = run(
                semantic if candidate.chunking == "semantic" else fixed, dev, candidate
            )
            accepted = promote(best, result)
            decisions.append(
                {
                    "candidate": asdict(candidate),
                    "promoted": accepted,
                    "compared_to": best_config.name,
                }
            )
            experiments.append(result)
            print(name, "promoted", accepted, json.dumps(result["summary"]), flush=True)
            if accepted:
                best, best_config = result, candidate
        index = semantic if best_config.chunking == "semantic" else fixed
        graph_config = Config("graph", best_config.chunking, hybrid=True, graph=True)
        graph = run(index, dev, graph_config)
        multi = graph["slices"]["multi_hop"]
        graph_enabled = (
            multi["recall"] >= best["slices"]["multi_hop"]["recall"] + 0.05
            and multi["retrieval_p95_ms"] <= 2000
        )
        experiments.append(graph)
        decisions.append(
            {
                "candidate": asdict(graph_config),
                "promoted": graph_enabled,
                "scope": "relationship route only",
            }
        )
        # Route itself is a candidate; compare before freezing.
        routed = run(index, dev, best_config, routing=True, graph_enabled=graph_enabled)
        router_enabled = promote(best, routed)
        experiments.append({**routed, "experiment": "router"})
        selection = {
            "selected": asdict(best_config),
            "graph_enabled": graph_enabled,
            "router_enabled": router_enabled,
            "decisions": decisions,
            "frozen_before_test": datetime.now(timezone.utc).isoformat(),
        }
        save("selection", selection)
        save(
            "development",
            {"metadata": meta, "experiments": experiments, "selection": selection},
        )
        final = run(
            index,
            test,
            best_config,
            routing=router_enabled,
            graph_enabled=graph_enabled,
        )
        baseline_test = run(fixed, test, Config())
        save(
            "heldout",
            {
                "metadata": meta,
                "selection": selection,
                "baseline": baseline_test,
                "selected": final,
            },
        )
        print("HELDOUT", json.dumps(final["summary"]), flush=True)
    if args.stage in ("all", "external"):
        selection = json.loads((ROOT / "reports/selection.json").read_text())
        config = Config(**selection["selected"])
        edocs = [
            Document.model_validate_json(x)
            for x in (DATA / "external/ragbench-documents.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        eqs = load_questions(DATA / "external/ragbench-questions.jsonl")
        ei = Index(edocs, encoder, persist=False)
        base = run(ei, eqs, Config())
        if config.chunking == "semantic":
            ei = Index(edocs, encoder, semantic=True, persist=False)
        selected = run(ei, eqs, config)
        save(
            "external",
            {
                "metadata": meta,
                "scope": "40 TechQA rows; pooled 200 documents; not official leaderboard",
                "external_corpus_sha256": ei.fingerprint,
                "baseline": base,
                "selected": selected,
            },
        )
        print("EXTERNAL", json.dumps(selected["summary"]), flush=True)
    if args.stage in ("all", "generation"):
        selection = json.loads((ROOT / "reports/selection.json").read_text())
        config = Config(**selection["selected"])
        index = Index(docs, encoder, semantic=config.chunking == "semantic")
        generator = LocalGenerator()
        # Entire test set; local generation distinct from evidence-only evaluation.
        generated = run(
            index,
            test,
            config,
            generator,
            routing=selection["router_enabled"],
            graph_enabled=selection["graph_enabled"],
        )
        save("generation", {"metadata": meta, **generated})
        print("GENERATION", json.dumps(generated["summary"]), flush=True)


if __name__ == "__main__":
    main()
