"""Bounded public-source acquisition with provenance, retries and raw snapshots."""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from atlas.corpus import DATA, write_jsonl
from atlas.schema import Document, Question

CLIENT = httpx.Client(
    timeout=60, follow_redirects=True, headers={"User-Agent": "TraceLedgerResearch/0.1"}
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def fetch(url, params=None):
    r = CLIENT.get(url, params=params)
    r.raise_for_status()
    if len(r.content) > 15_000_000:
        raise ValueError("Snapshot exceeds 15 MB limit")
    return r


def main():
    raw = DATA / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest = []
    public = []
    urls = [
        (
            "doe-microgrid-checklist",
            "https://www.energy.gov/cmei/femp/articles/microgrid-system-project-development-checklist",
        ),
        (
            "doe-project-process",
            "https://www.energy.gov/cmei/femp/process-planning-and-implementing-federal-distributed-energy-projects",
        ),
        ("doe-microgrid-systems", "https://www.energy.gov/oe/microgrid-systems"),
    ]
    for did, url in urls:
        r = fetch(url)
        (raw / f"{did}.html").write_bytes(r.content)
        soup = BeautifulSoup(r.text, "html.parser")
        for el in soup(["script", "style", "nav", "header", "footer"]):
            el.decompose()
        main = soup.find("main") or soup
        text = main.get_text("\n", strip=True)
        title = soup.title.get_text(strip=True) if soup.title else did
        public.append(Document(id=did, title=title, text=text, source=url))
        manifest.append(
            dict(
                id=did,
                url=url,
                sha256=hashlib.sha256(r.content).hexdigest(),
                bytes=len(r.content),
                license="US DOE public website; retain attribution; third-party material may have separate rights",
            )
        )
    write_jsonl(DATA / "public/documents.jsonl", public)

    dataset = "galileo-ai/ragbench"
    splits = fetch(
        "https://datasets-server.huggingface.co/splits", {"dataset": dataset}
    ).json()
    (raw / "ragbench-splits.json").write_text(json.dumps(splits), encoding="utf-8")
    # Predeclared deterministic bounded sample. Not a leaderboard reproduction.
    response = fetch(
        "https://datasets-server.huggingface.co/rows",
        dict(dataset=dataset, config="techqa", split="test", offset=0, length=40),
    )
    (raw / "ragbench-techqa-test-0-40.json").write_bytes(response.content)
    docs, questions = {}, []
    for item in response.json()["rows"]:
        if item.get("truncated_cells"):
            raise ValueError("Viewer truncated a benchmark row")
        row = item["row"]
        ids = []
        for body in row["documents"]:
            did = "ragbench-" + hashlib.sha256(body.encode()).hexdigest()[:20]
            ids.append(did)
            docs[did] = Document(
                id=did,
                title=f"RAGBench TechQA {did[-8:]}",
                text=body,
                source="https://huggingface.co/datasets/galileo-ai/ragbench",
            )
        indices = set(
            int(re.match(r"\d+", key).group())
            for key in row["all_relevant_sentence_keys"]
            if re.match(r"\d+", key)
        )
        relevant = sorted({ids[i] for i in indices if i < len(ids)})
        questions.append(
            Question(
                id=row["id"],
                query=row["question"],
                relevant=relevant,
                category="external_techqa",
                split="external",
            )
        )
    write_jsonl(DATA / "external/ragbench-documents.jsonl", list(docs.values()))
    write_jsonl(DATA / "external/ragbench-questions.jsonl", questions)
    manifest.append(
        dict(
            id=dataset,
            subset="techqa",
            split="test",
            offset=0,
            count=40,
            license="CC-BY-4.0 (dataset card); upstream IBM TechQA terms also apply",
            url="https://huggingface.co/datasets/galileo-ai/ragbench",
            sha256=hashlib.sha256(response.content).hexdigest(),
            method="pooled context documents, sentence relevance mapped to document IDs; sampled diagnostic, not official retrieval benchmark",
        )
    )
    er = "SJChen02/EnterpriseRAG-Bench"
    response = fetch(
        "https://datasets-server.huggingface.co/rows",
        dict(dataset=er, config="questions", split="test", offset=0, length=10),
    )
    (raw / "enterprise-questions-preview.json").write_bytes(response.content)
    manifest.append(
        dict(
            id=er,
            license="MIT (dataset card)",
            url="https://huggingface.co/datasets/SJChen02/EnterpriseRAG-Bench",
            status="selected for full-scale follow-up; 10 question schemas inspected; full 500k-document benchmark not run",
            sha256=hashlib.sha256(response.content).hexdigest(),
        )
    )
    (DATA / "source-manifest.json").write_text(
        json.dumps(
            {
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "sources": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Fetched {len(public)} DOE references and {len(docs)} pooled TechQA contexts for {len(questions)} questions"
    )


if __name__ == "__main__":
    main()
