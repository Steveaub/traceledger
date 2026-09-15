import time
from collections import deque

import pytest
from fastapi.testclient import TestClient

from atlas.api import create_app
from test_system import FakeEncoder
from atlas.schema import Document
from atlas.retrieval import Index
from atlas.service import Service


@pytest.fixture
def service():
    record = Document(
        id="public",
        title="Public",
        text="Public planning information is available.",
        source="https://example.org/reference",
    )
    return Service(Index([record], FakeEncoder(), persist=False))


def test_expired_principals_are_evicted(service, monkeypatch):
    monkeypatch.setenv("ATLAS_DEMO", "1")
    app = create_app(service)
    app.state.requests["expired"] = deque([time.monotonic() - 120])
    app.state.requests["empty"] = deque()
    with TestClient(app) as client:
        result = client.post(
            "/api/query", json={"query": "public information", "mode": "vector"}
        )
        assert result.status_code == 200
        assert set(app.state.requests) == {"demo"}


def test_hosted_demo_is_evidence_only_and_allows_space_frame(service, monkeypatch):
    monkeypatch.setenv("ATLAS_DEMO", "1")
    monkeypatch.setenv("ATLAS_HOSTED_DEMO", "1")
    with TestClient(create_app(service)) as client:
        result = client.get("/health")
        assert result.json()["hosted_demo"]
        csp = result.headers["Content-Security-Policy"]
        assert "frame-ancestors 'self' https://huggingface.co" in csp
        assert "script-src 'self'" in csp
        result = client.post(
            "/api/query", json={"query": "public information", "generation": "local"}
        )
        assert result.status_code == 422
        assert service.generator is None


def test_forwarded_addresses_cannot_bypass_shared_demo_limit(service, monkeypatch):
    monkeypatch.setenv("ATLAS_DEMO", "1")
    with TestClient(create_app(service)) as client:
        for i in range(30):
            result = client.post(
                "/api/query",
                headers={"X-Forwarded-For": f"192.0.2.{i}"},
                json={"query": "public information", "mode": "vector"},
            )
            assert result.status_code == 200
        result = client.post(
            "/api/query",
            headers={"X-Forwarded-For": "198.51.100.1"},
            json={"query": "public information", "mode": "vector"},
        )
        assert result.status_code == 429 and result.headers["Retry-After"] == "60"


def test_human_review_refuses_unlabelled_sample():
    from pathlib import Path
    from scripts.score_human_review import score

    with pytest.raises(ValueError, match="human yes/no"):
        score(Path(__file__).resolve().parents[1] / "evaluation/human-review")


def test_review_digest_ignores_checkout_newlines_but_detects_edits():
    from scripts.score_human_review import report_digest

    assert report_digest(b"a\r\nb\r\n") == report_digest(b"a\nb\n")
    assert report_digest(b"a\nb\n") != report_digest(b"a\nc\n")


def test_synthetic_generator_matches_committed_artifacts(tmp_path, monkeypatch):
    from atlas import corpus

    committed = corpus.DATA / "synthetic"
    monkeypatch.setattr(corpus, "DATA", tmp_path)
    corpus.generate()
    for name in ("documents.jsonl", "questions.jsonl", "universe.json"):
        assert (tmp_path / "synthetic" / name).read_text(encoding="utf-8") == (
            committed / name
        ).read_text(encoding="utf-8")


def test_schema_audit_matches_current_and_legacy_fingerprints():
    import hashlib
    import json
    from atlas.corpus import DATA, ROOT
    from atlas.schema import Document

    def digest(rows):
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()

    rows = [
        Document.model_validate_json(line).model_dump()
        for folder in ("synthetic", "public", "conversations")
        for line in (DATA / folder / "documents.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    audit = json.loads(
        (ROOT / "reports/corpus-schema-audit.json").read_text(encoding="utf-8")
    )
    assert digest(rows) == audit["investigation_corpus"]["current_after_sha256"]
    assert (
        digest(rows[:183]) == audit["document_corpus"]["current_14_field_after_sha256"]
    )
    legacy = [
        {k: v for k, v in row.items() if k not in audit["added_default_fields"]}
        for row in rows[:183]
    ]
    assert digest(legacy) == audit["document_corpus"]["legacy_10_field_sha256"]


def test_optional_generation_missing_dependencies(monkeypatch, tmp_path):
    import importlib.util
    from atlas import answer

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(answer, "ROOT", tmp_path)
    assert answer.local_generation_status()["available"] is False


def test_optional_generation_missing_files(monkeypatch, tmp_path):
    import importlib.util
    from atlas import answer

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(answer, "ROOT", tmp_path)
    assert answer.local_generation_status()["available"] is False
    model = tmp_path / "models/generator"
    model.mkdir(parents=True)
    for name in (
        "config.json",
        "tokenizer_config.json",
        "spiece.model",
        "model.safetensors",
    ):
        (model / name).write_text("fixture")
    assert answer.local_generation_status()["available"] is True


def test_optional_generation_disabled_but_evidence_works(service, monkeypatch):
    from atlas import api

    monkeypatch.setenv("ATLAS_DEMO", "1")
    monkeypatch.delenv("ATLAS_HOSTED_DEMO", raising=False)
    monkeypatch.setattr(
        api,
        "local_generation_status",
        lambda: {"available": False, "reason": "Optional AI is not installed."},
    )
    with TestClient(create_app(service)) as client:
        assert client.get("/health").json()["local_generation"]["available"] is False
        body = {"query": "public planning", "mode": "vector", "generation": "local"}
        assert client.post("/api/query", json=body).status_code == 503
        body["generation"] = "evidence"
        assert client.post("/api/query", json=body).status_code == 200


def test_optional_generation_runtime_failure_offers_recovery(service, monkeypatch):
    from atlas import api

    monkeypatch.setenv("ATLAS_DEMO", "1")
    monkeypatch.delenv("ATLAS_HOSTED_DEMO", raising=False)
    monkeypatch.setattr(
        api, "local_generation_status", lambda: {"available": True, "reason": ""}
    )
    original = service.query

    def fail_local(request, projects):
        if request.generation == "local":
            raise OSError("Broken optional model")
        return original(request, projects)

    monkeypatch.setattr(service, "query", fail_local)
    with TestClient(create_app(service)) as client:
        body = {"query": "public planning", "mode": "vector", "generation": "local"}
        response = client.post("/api/query", json=body)
        assert response.status_code == 503
        assert response.json()["detail"].startswith("Local AI unavailable.")
        assert client.get("/health").json()["local_generation"]["available"] is False
        body["generation"] = "evidence"
        assert client.post("/api/query", json=body).status_code == 200
