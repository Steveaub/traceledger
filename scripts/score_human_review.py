"""Score completed human labels; refuses empty sheets or a changed source report."""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report_digest(content: bytes) -> str:
    """Hash source text consistently across Git checkout line endings."""
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()


def score(folder: Path) -> dict:
    manifest = json.loads((folder / "sample.json").read_text(encoding="utf-8"))
    source = ROOT / "reports/heldout.json"
    if report_digest(source.read_bytes()) != manifest["source_sha256_lf"]:
        raise ValueError("Source report changed; labels cannot be compared")
    rows = {
        r["id"]: r
        for r in json.loads(source.read_text(encoding="utf-8"))["selected"]["rows"]
    }
    agreements = {}
    counts = {}
    for name, field in [
        ("answers", "answer_relevant"),
        ("citations", "citation_relevant"),
    ]:
        with (folder / f"{name}.csv").open(encoding="utf-8-sig", newline="") as file:
            labels = list(csv.DictReader(file))
        if not labels or any(
            r[field] not in ("yes", "no") or not r["reviewer_id"].strip()
            for r in labels
        ):
            raise ValueError(
                f"{name}: every row needs a human yes/no label and reviewer ID"
            )
        observed = []
        keys = set()
        for label in labels:
            qid = label["question_id"]
            if qid not in manifest["question_ids"]:
                raise ValueError("Unexpected question ID")
            row = rows[qid]
            if name == "answers":
                key = qid
                proxy = (
                    row["answer"]["abstained"]
                    if not row["relevant"]
                    else (row["relevance_gold_term_coverage"] or 0) >= 0.8
                )
            else:
                key = (qid, int(label["citation_id"]))
                citation = next(
                    c for c in row["answer"]["citations"] if c["id"] == key[1]
                )
                proxy = citation["doc_id"] in row["relevant"]
            if key in keys:
                raise ValueError("Duplicate label row")
            keys.add(key)
            observed.append((label[field] == "yes") == proxy)
        expected = (
            set(manifest["question_ids"])
            if name == "answers"
            else {
                (qid, c["id"])
                for qid in manifest["question_ids"]
                for c in rows[qid]["answer"]["citations"]
            }
        )
        if keys != expected:
            raise ValueError(f"{name}: incomplete review")
        agreements[name] = sum(observed) / len(observed)
        counts[name] = len(observed)
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": manifest["source_sha256"],
        "sample_size": 30,
        "counts": counts,
        "agreement": agreements,
        "answer_proxy": "gold-term coverage >= 0.8, or correct abstention on unsupported questions",
        "citation_proxy": "document ID belongs to gold relevance set",
        "limitations": "Agreement is not accuracy or inter-rater reliability; human labels are supplied by the operator.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, default=ROOT / "evaluation/human-review")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(args.folder)
    # Never replace an earlier review result.
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
