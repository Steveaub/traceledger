from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from starlette.responses import Response
import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from atlas.corpus import ROOT, load_docs
from atlas.retrieval import Encoder, Index
from atlas.schema import QueryRequest
from atlas.service import Service
from atlas.answer import local_generation_status
from atlas.history import list_runs, read_run, compare_runs

log = logging.getLogger("atlas.audit")
logging.basicConfig(level=logging.INFO, format="%(message)s")
auth = HTTPBearer(auto_error=False)


def create_app(service: Service | None = None) -> FastAPI:
    generation_status = local_generation_status()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if app.state.service is None:
            selection_path = ROOT / "reports/selection.json"
            selection = (
                json.loads(selection_path.read_text())
                if selection_path.exists()
                else {}
            )
            documents = load_docs()
            if app.state.demo:
                # Anonymous portfolio mode never indexes private operator imports.
                documents = [
                    d
                    for d in documents
                    if d.synthetic
                    or (d.project == "public" and d.channel == "documents")
                ]
            index = Index(
                documents,
                Encoder(),
                semantic=selection.get("selected", {}).get("chunking") == "semantic",
            )
            app.state.service = Service(index)
        yield

    app = FastAPI(title="TraceLedger", version="0.1.0", lifespan=lifespan)
    app.state.service = service
    # Principal ACL is server-controlled, never accepted from a query body.
    app.state.principals = json.loads(os.environ.get("ATLAS_PRINCIPALS_JSON", "{}"))
    app.state.demo = os.environ.get("ATLAS_DEMO", "0") == "1"
    app.state.requests = defaultdict(deque)
    app.state.hosted_demo = (
        app.state.demo and os.environ.get("ATLAS_HOSTED_DEMO", "0") == "1"
    )

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(auth)):
        if app.state.demo and not credentials:
            return {"id": "demo", "projects": [f"PRJ-{i:03}" for i in range(1, 13)]}
        if credentials:
            for key, info in app.state.principals.items():
                if secrets.compare_digest(key, credentials.credentials):
                    return info
        raise HTTPException(401, "Valid bearer token required")

    def evaluator(user=Depends(principal)):
        if not user.get("evaluation", False) and not (
            app.state.demo and user["id"] == "demo"
        ):
            raise HTTPException(403, "Evaluation access requires an evaluator role")
        return user

    def visible_run(run_id, user):
        try:
            record = read_run(run_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Evaluation run not found")
        if user["id"] == "demo" and record.get("visibility") != "demo":
            raise HTTPException(404, "Evaluation run not found")
        return record

    @app.get("/api/evaluations")
    def evaluations(user=Depends(evaluator)):
        records = list_runs()
        if user["id"] == "demo":
            records = [r for r in records if r.get("visibility") == "demo"]
        return {"runs": records}

    @app.get("/api/evaluations/compare")
    def comparison(before: str, after: str, user=Depends(evaluator)):
        try:
            return compare_runs(visible_run(before, user), visible_run(after, user))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/evaluations/{run_id}")
    def evaluation(run_id: str, user=Depends(evaluator)):
        return visible_run(run_id, user)

    @app.middleware("http")
    async def trace(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        trace_id = uuid.uuid4().hex
        started = time.perf_counter()
        from fastapi.responses import JSONResponse

        try:
            declared = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid content length"}, status_code=400)
        if declared > 16000:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        if request.method in ("POST", "PUT", "PATCH"):
            chunks = []
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 16000:
                    return JSONResponse(
                        {"detail": "Request too large"}, status_code=413
                    )
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors "
            + ("'self' https://huggingface.co" if app.state.hosted_demo else "'none'")
        )
        log.info(
            json.dumps(
                {
                    "event": "http_request",
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
        )
        return response

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ready" if app.state.service else "starting",
            "demo": app.state.demo,
            "hosted_demo": app.state.hosted_demo,
            "local_generation": {
                "available": False,
                "reason": "This demo supports verified source excerpts only.",
            }
            if app.state.hosted_demo
            else generation_status,
        }

    @app.post("/api/query")
    def query(
        body: QueryRequest, user: dict[str, Any] = Depends(principal)
    ) -> dict[str, Any]:
        if app.state.hosted_demo and body.generation != "evidence":
            raise HTTPException(422, "Hosted demo supports evidence mode only")
        if body.generation == "local" and not generation_status["available"]:
            raise HTTPException(
                503, "Local AI unavailable. " + str(generation_status["reason"])
            )
        with app.state.service.lock:
            now = time.monotonic()
            for principal_id in list(app.state.requests):
                old_bucket = app.state.requests[principal_id]
                while old_bucket and now - old_bucket[0] > 60:
                    old_bucket.popleft()
                if not old_bucket:
                    del app.state.requests[principal_id]
            bucket = app.state.requests[user["id"]]
            if len(bucket) >= 30:
                raise HTTPException(
                    429,
                    "Rate limit: 30 requests per minute",
                    headers={"Retry-After": "60"},
                )
            bucket.append(now)
        try:
            result = app.state.service.query(body, user["projects"])
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except (RuntimeError, OSError, ImportError) as exc:
            log.error(
                json.dumps(
                    {"event": "inference_failed", "exception_type": type(exc).__name__}
                )
            )
            if body.generation == "local":
                generation_status.update(
                    available=False,
                    reason="Local AI could not load or run. Use verified source excerpts, or check local AI setup and restart.",
                )
                raise HTTPException(
                    503, "Local AI unavailable. " + generation_status["reason"]
                ) from exc
            raise HTTPException(
                503,
                "Retrieval model unavailable. Run the retrieval model bootstrap and restart the server.",
            ) from exc
        log.info(
            json.dumps(
                {
                    "event": "query_complete",
                    "principal": hashlib.sha256(user["id"].encode()).hexdigest()[:12],
                    "route": result["path"],
                    "cached": result["cached"],
                    "citations": len(result["citations"]),
                    "retrieval_ms": result["retrieval_ms"],
                }
            )
        )
        return result

    @app.get("/api/projects")
    def projects(user: dict[str, Any] = Depends(principal)) -> dict[str, Any]:
        docs = app.state.service.index.docs.values()
        names = {
            d.project: d.title.split(" / ")[0] for d in docs if d.kind == "charter"
        }
        return {
            "projects": sorted(user["projects"]),
            "names": {p: names.get(p, p) for p in user["projects"]},
        }

    @app.get("/api/feeds")
    def feeds(user: dict[str, Any] = Depends(principal)) -> dict[str, Any]:
        index = app.state.service.index
        docs = [
            d
            for d in index.docs.values()
            if d.current and index.allowed(d.id, set(user["projects"]))
        ]
        return {
            "live_connected": False,
            "sources": [
                {
                    "id": channel,
                    "label": label,
                    "records": sum(d.channel == channel for d in docs),
                    "demo_records": sum(
                        d.channel == channel and d.synthetic for d in docs
                    ),
                    "imported_records": sum(
                        d.channel == channel and not d.synthetic for d in docs
                    ),
                    "status": "local index"
                    if channel == "documents"
                    else "demo / reviewed exports",
                }
                for channel, label in [
                    ("documents", "Documents"),
                    ("email", "Email"),
                    ("slack", "Slack"),
                    ("teams", "Teams"),
                ]
            ],
        }

    @app.get("/api/source/{doc_id}")
    def source(
        doc_id: str, user: dict[str, Any] = Depends(principal)
    ) -> dict[str, Any]:
        index = app.state.service.index
        if doc_id not in index.docs or not index.allowed(doc_id, set(user["projects"])):
            raise HTTPException(404, "Source not found")
        return index.docs[doc_id].model_dump()

    app.mount("/static", StaticFiles(directory=ROOT / "atlas/static"), name="static")

    @app.get("/")
    def home() -> FileResponse:
        return FileResponse(ROOT / "atlas/static/index.html")

    return app


app = create_app()
