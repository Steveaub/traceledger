import json
from types import SimpleNamespace
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from atlas import history
from atlas.api import create_app
from atlas.schema import Question


def record(folder, value=.5, public=False, corpus="corpus"):
    result={"config":{"name":"test"},"summary":{"mrr":value,"recall":value},
            "slices":{},"rows":[{"id":"q","query":"Test question","mrr":value}]}
    qs=[Question(id="q",query="Test question",relevant=["d"],category="unit",split="test")]
    return history.record_run(result,SimpleNamespace(fingerprint=corpus),qs,
                              started_at="2026-09-13T00:00:00+00:00",directory=folder,public_demo=public)


def test_runs_are_unique_and_keep_original_bytes(tmp_path):
    first=record(tmp_path)
    original=(tmp_path/f"{first}.json").read_bytes()
    second=record(tmp_path,.8)
    assert first!=second
    assert (tmp_path/f"{first}.json").read_bytes()==original
    assert len(history.list_runs(tmp_path))==2
    assert all("rows" not in r for r in history.list_runs(tmp_path))
    assert not list(tmp_path.glob("*.tmp"))


def test_compare_rejects_dataset_changes_and_flags_regression(tmp_path):
    a=history.read_run(record(tmp_path,.8),tmp_path)
    b=history.read_run(record(tmp_path,.5),tmp_path)
    comparison=history.compare_runs(a,b)
    assert "mrr" in comparison["regressions"]
    assert comparison["questions"][0]["delta"]==pytest.approx(-.3)
    c=history.read_run(record(tmp_path,.9,corpus="different"),tmp_path)
    with pytest.raises(ValueError,match="same corpus"):
        history.compare_runs(a,c)


@pytest.mark.parametrize("run_id",["../secret", "..%2fsecret", "arbitrary", "/etc/passwd"])
def test_run_ids_reject_path_traversal(tmp_path,run_id):
    with pytest.raises(ValueError):history.read_run(run_id,tmp_path)


def test_evaluation_role_and_demo_visibility(tmp_path,monkeypatch):
    monkeypatch.setattr(history,"HISTORY",tmp_path)
    private=record(tmp_path)
    public=record(tmp_path,.7,public=True)
    monkeypatch.setenv("ATLAS_DEMO","1")
    monkeypatch.setenv("ATLAS_PRINCIPALS_JSON",json.dumps({
        "reader":{"id":"reader","projects":["A"]},
        "evaluator":{"id":"evaluator","projects":[],"evaluation":True}}))
    with TestClient(create_app(SimpleNamespace())) as client:
        headers={"Authorization":"Bearer reader"}
        assert client.get("/api/evaluations",headers=headers).status_code==403
        assert client.get(f"/api/evaluations/{private}").status_code==404
        assert [r["id"] for r in client.get("/api/evaluations").json()["runs"]]==[public]
        assert client.get(f"/api/evaluations/{public}").status_code==200
        assert client.get(f"/api/evaluations/{private}",headers={"Authorization":"Bearer evaluator"}).status_code==200
        assert client.get("/api/evaluations/compare",params={"before":private,"after":public}).status_code==404


def test_corrupt_and_partial_runs_do_not_break_listing(tmp_path):
    record(tmp_path)
    (tmp_path/"20260913T000000-aaaaaaaaaaaa.json").write_text("{")
    (tmp_path/"incomplete.tmp").write_text("{")
    assert len(history.list_runs(tmp_path))==1
