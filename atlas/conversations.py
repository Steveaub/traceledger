"""Reviewed local exports only. Does not connect accounts or inherit native ACLs."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from atlas.answer import INJECTION
from atlas.corpus import DATA, write_jsonl
from atlas.schema import Document


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=200)
    thread_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=200000)
    author: str = Field(min_length=1, max_length=200)
    timestamp: str
    source: str | None = None


def parse_export(path, provider, project):
    path = Path(path)
    if provider not in ("email", "slack", "teams"):
        raise ValueError("Choose email, slack or teams")
    if not project or project == "public":
        raise ValueError("Conversation imports require a private project scope")
    if path.stat().st_size > 10_000_000:
        raise ValueError("Export exceeds 10 MB")
    raw = path.read_bytes()
    if path.suffix.lower() == ".eml" and provider == "email":
        msg = BytesParser(policy=policy.default).parsebytes(raw)
        part = msg.get_body(preferencelist=("plain",))
        if part is None:
            raise ValueError(
                "Email requires a plain-text body; attachments are not imported"
            )
        from email.utils import parsedate_to_datetime

        rows = [
            dict(
                id=str(msg.get("Message-ID") or hashlib.sha256(raw).hexdigest()),
                thread_id=str(
                    msg.get("In-Reply-To") or msg.get("Message-ID") or path.name
                ),
                author=str(msg.get("From", "Unknown sender")),
                timestamp=parsedate_to_datetime(msg["Date"]).isoformat(),
                text=part.get_content(),
            )
        ]
    elif path.suffix.lower() == ".json":
        rows = json.loads(raw.decode("utf-8"))
        if not isinstance(rows, list) or len(rows) > 1000:
            raise ValueError("Expected a JSON list of at most 1000 messages")
        if provider == "slack" and rows and "ts" in rows[0]:
            # One reviewed Slack channel file. Never import deleted/bot/system events.
            rows = [
                dict(
                    id=r["ts"],
                    thread_id=r.get("thread_ts", r["ts"]),
                    author=r.get("user", "Unknown sender"),
                    timestamp=datetime.fromtimestamp(
                        float(r["ts"]), timezone.utc
                    ).isoformat(),
                    text=r["text"],
                )
                for r in rows
                if r.get("type") == "message" and not r.get("subtype") and r.get("text")
            ]
    else:
        raise ValueError("Use .eml for email or the documented normalized JSON format")
    docs = []
    for row in rows:
        m = Message.model_validate(row)
        when = datetime.fromisoformat(m.timestamp.replace("Z", "+00:00"))
        if when.tzinfo is None:
            raise ValueError("Message timestamps require a timezone")
        if INJECTION.search(m.text):
            raise ValueError(
                "Quarantined export: suspected instruction injection; no messages imported"
            )
        # Account/channel namespace comes from the operator-provided export filename.
        namespace = hashlib.sha256(
            (project + provider + path.name).encode()
        ).hexdigest()[:16]
        did = "message-" + hashlib.sha256((namespace + m.id).encode()).hexdigest()[:32]
        docs.append(
            Document(
                id=did,
                title=f"{project} / {provider} / {m.author}"[:300],
                text=m.text,
                project=project,
                kind="conversation",
                source=m.source or "upload:" + did,
                channel=provider,
                author=m.author,
                date=when.isoformat(),
                thread_id=namespace
                + ":"
                + hashlib.sha256(m.thread_id.encode()).hexdigest()[:32],
            )
        )
    if len({d.id for d in docs}) != len(docs):
        raise ValueError("Duplicate message IDs in export")
    return docs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--provider", choices=["email", "slack", "teams"], required=True
    )
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--reviewed-project-access",
        action="store_true",
        required=True,
        help="Confirm all imported messages may be read by every member of this TraceLedger project",
    )
    args = parser.parse_args()
    docs = parse_export(args.path, args.provider, args.project)
    if not docs:
        raise ValueError("No supported messages found")
    key = hashlib.sha256(
        (args.project + args.provider + args.path.name).encode()
    ).hexdigest()[:24]
    target = DATA / "ingested" / ("feed-" + key + ".jsonl")
    write_jsonl(target, docs)
    print(
        f"Imported {len(docs)} messages. Restart TraceLedger to refresh its index. Native workspace permissions are not synchronized."
    )


if __name__ == "__main__":
    main()
