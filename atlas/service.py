from __future__ import annotations
from collections.abc import Iterable
from typing import Any
from atlas.schema import QueryRequest
import copy
import hashlib
import json
import threading
import time
from collections import OrderedDict
from atlas.corpus import ROOT
from atlas.retrieval import Config, Index, route
from atlas.answer import evidence_answer, LocalGenerator


class Service:
    def __init__(self, index: Index, cache_size: int = 128, ttl: float = 120) -> None:
        self.index = index
        self.document_index = index
        if any(d.channel != "documents" for d in index.docs.values()):
            from atlas.retrieval import Index

            document_docs = [d for d in index.docs.values() if d.channel == "documents"]
            if document_docs:
                self.document_index = Index(document_docs, index.encoder, persist=False)
        self.cache = OrderedDict()
        self.cache_size, self.ttl = cache_size, ttl
        self.lock = threading.RLock()
        self.generator = None
        selection_path = ROOT / "reports/selection.json"
        self.selection = (
            json.loads(selection_path.read_text())
            if selection_path.exists()
            else {
                "selected": Config().__dict__,
                "graph_enabled": False,
                "router_enabled": False,
            }
        )

    def query(self, request: QueryRequest, projects: Iterable[str]) -> dict[str, Any]:
        # Serialize local CPU inference and mutate cache only under this lock.
        with self.lock:
            allowed = set(projects)
            if request.project is not None:
                if request.project not in allowed and request.project != "public":
                    raise PermissionError("Project not authorized")
                allowed = {request.project}
            config = Config(**self.selection["selected"])
            if request.mode == "auto" and self.selection["router_enabled"]:
                config = route(request.query, config, self.selection["graph_enabled"])
            elif request.mode != "auto":
                config = Config(
                    request.mode,
                    config.chunking,
                    hybrid=request.mode in ("hybrid", "graph"),
                    graph=request.mode == "graph",
                )
            key = hashlib.sha256(
                json.dumps(
                    [
                        request.model_dump(),
                        sorted(allowed),
                        self.index.fingerprint,
                        config.__dict__,
                    ],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            now = time.monotonic()
            if key in self.cache and now - self.cache[key][0] < self.ttl:
                self.cache.move_to_end(key)
                answer = copy.deepcopy(self.cache[key][1])
                answer["cached"] = True
                return answer
            if request.mode == "investigate":
                from atlas.investigator import investigate

                return investigate(self.index, request, allowed)
            search_index = (
                self.document_index
                if set(request.sources) == {"documents"}
                else self.index
            )
            retrieved = search_index.search(
                request.query,
                config,
                request.k,
                projects=allowed,
                sources=set(request.sources),
            )
            if request.generation == "local":
                if self.generator is None:
                    self.generator = LocalGenerator()
                answer = self.generator.answer(request.query, retrieved)
                answer.pop("draft", None)
            else:
                answer = evidence_answer(request.query, retrieved)
            result = {
                **answer,
                "path": retrieved["path"],
                "retrieval_ms": retrieved["retrieval_ms"],
                "graph_paths": retrieved["graph_paths"],
                "rewritten_query": retrieved["rewritten_query"],
                "cached": False,
                "corpus_version": self.index.fingerprint[:12],
            }
            self.cache[key] = (now, copy.deepcopy(result))
            self.cache.move_to_end(key)
            while len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)
            return result
