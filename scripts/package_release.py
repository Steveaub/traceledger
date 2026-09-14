import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
skip = {
    ".venv",
    ".git",
    ".cache",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "models",
}
paths = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT)
    if any(
        x in skip or x.startswith(".test-tmp") or x.endswith(".egg-info")
        for x in rel.parts
    ):
        continue
    if rel.parts[:2] in [
        ("data", "raw"),
        ("data", "external"),
        ("data", "index"),
        ("data", "ingested"),
    ]:
        continue
    if (
        p.name in (".env", "release-manifest.json", "CODEX-BRIEF.md")
        or (p.name.startswith(".env.") and p.name != ".env.example")
        or p.suffix.lower() in {".log", ".pem", ".key", ".token"}
        or p.name.lower().startswith(("credentials", "secrets"))
    ):
        continue
    if rel.parts[:2] == ("reports", "runs"):
        if (
            p.suffix != ".json"
            or json.loads(p.read_text(encoding="utf-8")).get("visibility") != "demo"
        ):
            continue
    paths.append(p)
manifest = {
    str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
        p.read_bytes()
    ).hexdigest()
    for p in sorted(paths)
}
mp = ROOT / "reports/release-manifest.json"
mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
archive = ROOT.parent / "trace-ledger-source.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for p in paths + [mp]:
        z.write(p, Path("trace-ledger") / p.relative_to(ROOT))
print(
    json.dumps(
        {
            "archive": str(archive),
            "files": len(paths) + 1,
            "bytes": archive.stat().st_size,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        }
    )
)
