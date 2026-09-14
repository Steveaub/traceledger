"""Assemble an allowlisted evidence-only Space without publishing anything."""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for folder in [
        "atlas",
        "config",
        "data/synthetic",
        "data/public",
        "data/conversations",
    ]:
        for source in (ROOT / folder).rglob("*"):
            if not source.is_file() or "__pycache__" in source.parts:
                continue
            if source.suffix not in (
                ".py",
                ".js",
                ".css",
                ".html",
                ".svg",
                ".json",
                ".jsonl",
            ):
                continue
            target = destination / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for name in [
        "pyproject.toml",
        "LICENSE",
        "scripts/bootstrap_models.py",
        "reports/selection.json",
    ]:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for source in (ROOT / "reports/runs").glob("*.json"):
        if json.loads(source.read_text(encoding="utf-8")).get("visibility") == "demo":
            target = destination / "reports/runs" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for name in ["README.md", "Dockerfile"]:
        shutil.copyfile(ROOT / "deploy/huggingface" / name, destination / name)
    print(f"Prepared {destination}; no upload performed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    prepare(parser.parse_args().destination)
