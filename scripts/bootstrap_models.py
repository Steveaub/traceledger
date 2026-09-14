"""Download allowlisted model files at immutable Hub revisions; no remote code."""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
specs = {
    "embedding": (
        "qdrant/all-MiniLM-L6-v2-onnx",
        ["*.json", "model.onnx", "vocab.txt", "special_tokens_map.json"],
    ),
    "reranker": (
        "Xenova/ms-marco-MiniLM-L-6-v2",
        ["*.json", "onnx/model.onnx", "vocab.txt"],
    ),
    "generator": (
        "google/flan-t5-small",
        ["*.json", "model.safetensors", "spiece.model", "tokenizer.json"],
    ),
}
manifest_path = ROOT / "models/manifest.json"
lock_path = ROOT / "config/model-manifest.json"
manifest = (
    json.loads(lock_path.read_text())
    if lock_path.exists()
    else (json.loads(manifest_path.read_text()) if manifest_path.exists() else {})
)
for name, (repo, patterns) in specs.items():
    if name == "generator" and "--retrieval-only" in sys.argv:
        continue
    revision = manifest.get(name, {}).get("revision") or HfApi().model_info(repo).sha
    snapshot_download(
        repo,
        revision=revision,
        allow_patterns=patterns,
        local_dir=ROOT / "models" / name,
    )
    manifest[name] = {"repo": repo, "revision": revision, "license": "apache-2.0"}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(name, revision, flush=True)
