"""Offline ingestion boundary: reviewed local files only, no arbitrary URL fetch."""
import argparse
import hashlib
from pathlib import Path
from pypdf import PdfReader
from atlas.schema import Document
from atlas.corpus import write_jsonl
from atlas.answer import INJECTION


def ingest_file(path:Path,project:str):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected regular local file")
    if path.stat().st_size>10_000_000:
        raise ValueError("Maximum file size is 10 MB")
    raw=path.read_bytes()
    if path.suffix.lower()=="pdf":
        raise ValueError("Invalid extension")
    if path.suffix.lower()==".pdf":
        reader=PdfReader(path)
        if reader.is_encrypted or len(reader.pages)>200:
            raise ValueError("Encrypted or oversized PDF")
        text="\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif path.suffix.lower() in (".txt",".md"):
        text=raw.decode("utf-8")
    else:
        raise ValueError("Supported types: .txt, .md, .pdf")
    if INJECTION.search(text):
        raise ValueError("Quarantined: possible document prompt injection; review manually")
    digest=hashlib.sha256(raw).hexdigest()
    return Document(id="upload-"+digest[:24],title=path.name,text=text,project=project,source="upload:"+digest)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path)
    p.add_argument("--project",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    write_jsonl(args.output,[ingest_file(args.path,args.project)])
