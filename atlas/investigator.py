"""Bounded, evidence-driven retrieval agent. Deterministic policy; no LLM planner.

Actions use accessible evidence only. This is an investigation workflow, not a
general-purpose autonomous agent. No writes, credentials, network or execution tools.
"""

import re
import time
from atlas.answer import INJECTION, STOP
from atlas.retrieval import Config, sentences, tokens

MAX_ACTIONS = 6
MAX_SECONDS = 15
MAX_EVIDENCE = 12
IDENTIFIERS = re.compile(r"\b(?:PRJ|INC|CR|DEC|RISK|LL|REQ|SITE)-\d+\b", re.I)


def investigate(
    index, request, projects, *, max_seconds=MAX_SECONDS, max_actions=MAX_ACTIONS
):
    start = time.perf_counter()
    sources = set(request.sources)
    trace, hits, paths, used = [], {}, [], set()
    scope = set(projects)
    gaps = []
    # Resolve explicit project names exclusively from already accessible metadata.
    names = re.findall(r"\bProject\s+([A-Za-z]+)", request.query, re.I)
    accessible = [
        d
        for d in index.docs.values()
        if index.allowed(d.id, scope) and d.current and d.channel in sources
    ]
    if names:
        matched = {
            d.project
            for d in accessible
            if d.title.split(" / ")[0].lower() in {n.lower() for n in names}
        }
        if not matched:
            return finish(
                index,
                request,
                {},
                [],
                [],
                start,
                [
                    "The named project was not found in the selected, accessible sources."
                ],
                "missing_evidence",
            )
        scope &= matched
    query_ids = {x.upper() for x in IDENTIFIERS.findall(request.query)}
    accessible = [
        d
        for d in accessible
        if index.allowed(d.id, scope) and (not names or d.project in scope)
    ]
    if query_ids and not all(
        any(
            x.lower() in d.text.lower() and not INJECTION.search(d.text)
            for d in accessible
        )
        for x in query_ids
    ):
        return finish(
            index,
            request,
            {},
            [],
            [],
            start,
            [
                "The requested identifier was not found in the selected, accessible sources."
            ],
            "missing_evidence",
        )

    def budget():
        return len(trace) < max_actions and time.perf_counter() - start < max_seconds

    def search(query, label, graph=False):
        if not budget() or query in used:
            return
        used.add(query)
        t = time.perf_counter()
        result = index.search(
            query,
            Config("investigator", hybrid=True, rerank=not graph, graph=graph),
            5,
            projects=scope,
            sources=sources,
        )
        found = []
        for h in result["hits"]:
            d = index.docs[h["doc_id"]]
            if (
                h["dense_score"] >= 0.28
                and not INJECTION.search(d.text)
                and (not names or d.project in scope)
            ):
                hits.setdefault(d.id, h)
                found.append(d.id)
        paths.extend(
            p
            for p in result["graph_paths"]
            if not INJECTION.search(index.docs[p["doc_id"]].text)
            and (not names or index.docs[p["doc_id"]].project in scope)
        )
        trace.append(
            {
                "tool": "search_relationships" if graph else "search_sources",
                "label": label,
                "query": query,
                "source_ids": found,
                "duration_ms": round((time.perf_counter() - t) * 1000, 2),
            }
        )

    search(request.query, "Find the initial evidence")
    while budget():
        # Re-plan from the observed evidence on every iteration, never from eval labels.
        observed = [index.docs[did] for did in hits]
        threads = {(d.project, d.channel, d.thread_id) for d in observed if d.thread_id}
        pending = [key for key in sorted(threads) if "thread:" + str(key) not in used]
        if pending:
            key = pending[0]
            used.add("thread:" + str(key))
            t = time.perf_counter()
            siblings = sorted(
                [
                    d
                    for d in accessible
                    if (d.project, d.channel, d.thread_id) == key
                    and not INJECTION.search(d.text)
                ],
                key=lambda d: d.date,
            )[:20]
            for d in siblings:
                # Thread expansion preserves literal message boundaries and offsets.
                hits.setdefault(
                    d.id,
                    dict(
                        doc_id=d.id,
                        title=d.title,
                        text=d.text,
                        start=0,
                        end=len(d.text),
                        source=d.source,
                        synthetic=d.synthetic,
                        dense_score=1.0,
                    ),
                )
            trace.append(
                {
                    "tool": "read_thread",
                    "label": "Read the surrounding " + key[1] + " conversation",
                    "source_ids": [d.id for d in siblings],
                    "duration_ms": round((time.perf_counter() - t) * 1000, 2),
                }
            )
            continue
        evidence = " ".join(d.text for d in observed)
        ids = list(dict.fromkeys(IDENTIFIERS.findall(evidence)))[:8]
        anchor = (
            ("Project " + names[0]) if names else " ".join(ids[:3]) or request.query
        )
        wants_approval = bool(
            re.search(r"approve|approval|decision|trace", request.query, re.I)
        )
        wants_schedule = bool(
            re.search(r"schedule|delay|commission", request.query, re.I)
        )
        actions = []
        if wants_approval and not any(
            d.decision_status == "approved" for d in observed
        ):
            actions.append(
                (
                    anchor + " approved change approval owner",
                    "Check the approval record",
                    False,
                )
            )
        if wants_schedule and not any(
            "schedule register updated" in d.text.lower() for d in observed
        ):
            actions.append(
                (
                    anchor + " schedule register updated baseline",
                    "Verify the schedule update",
                    False,
                )
            )
        if re.search(r"why|cause|delay", request.query, re.I) and not any(
            d.kind == "incident" or "cause" in d.id for d in observed
        ):
            actions.append(
                (
                    anchor + " incident commissioning cause",
                    "Investigate the cause",
                    False,
                )
            )
        if ids and "documents" in sources:
            actions.append(
                (
                    " ".join(ids[:3]) + " linked change impact",
                    "Follow documented relationships",
                    True,
                )
            )
        todo = next((a for a in actions if a[0] not in used), None)
        if not todo:
            break
        search(*todo)
    observed = [index.docs[did] for did in hits]
    if re.search(r"approv|who", request.query, re.I) and not any(
        d.decision_status == "approved" for d in observed
    ):
        gaps.append(
            "No explicit approval message was found in the selected sources. A proposal is not an approval."
        )
    if re.search(r"updated|register", request.query, re.I) and not any(
        "schedule register updated" in d.text.lower() for d in observed
    ):
        gaps.append(
            "A schedule-register update was not verified in the selected evidence."
        )
    stopped = (
        "time_budget"
        if time.perf_counter() - start >= max_seconds
        else "action_budget"
        if len(trace) >= max_actions
        else "evidence_checked"
    )
    if stopped in ("time_budget", "action_budget"):
        gaps.append(
            "The investigation reached its budget. Additional evidence may remain."
        )
    return finish(index, request, hits, paths, trace, start, gaps, stopped)


def finish(index, request, hits, paths, trace, start, gaps, stopped):
    # Prioritize the requested facets, then show proposals as context after approved records.
    priority = {
        "approved": 0,
        "recorded": 2,
        "unspecified": 4,
        "proposed": 5,
        "disputed": 1,
    }
    ordered = sorted(
        hits.values(),
        key=lambda h: (
            priority[index.docs[h["doc_id"]].decision_status],
            0
            if "schedule" in h["doc_id"]
            else 1
            if index.docs[h["doc_id"]].kind == "incident"
            else 2,
        ),
    )
    terms = set(tokens(request.query)) - STOP
    citations = []
    for h in ordered:
        d = index.docs[h["doc_id"]]
        # Conversation context informs follow-up actions but is not automatically
        # answer evidence. Select explicit statements for the requested facets.
        if re.search(r"approv|schedule|why|delay", request.query, re.I):
            patterns = []
            if re.search(r"approv|who", request.query, re.I):
                patterns.append(r"\bapproved\b|approval owner|board accepted")
            if re.search(r"schedule|updated|delay|commission", request.query, re.I):
                patterns.append(
                    r"schedule register updated|commissioning.*(?:delayed|slipped)|technical cause|moved .+ by \d+ weeks"
                )
            if re.search(r"why|cause", request.query, re.I):
                patterns.append(r"\bincident\b.*:|\bbecause\b")
            if patterns and (
                d.decision_status == "proposed"
                or not re.search("|".join(patterns), h["text"], re.I)
            ):
                continue
            if d.channel != "documents" and d.decision_status == "unspecified":
                # Unverified questions and requests must not become approvals.
                continue
        ranked = sorted(
            sentences(h["text"]),
            key=lambda s: len(terms & set(tokens(s[2]))),
            reverse=True,
        )
        if not ranked:
            continue
        a, b, _ = ranked[0]
        quote = h["text"][a:b]
        if not terms.intersection(tokens(quote)):
            continue
        citations.append(
            dict(
                id=len(citations) + 1,
                doc_id=d.id,
                title=d.title,
                quote=quote,
                start=h["start"] + a,
                end=h["start"] + b,
                source=d.source,
                synthetic=d.synthetic,
                channel=d.channel,
                author=d.author,
                date=d.date,
                thread_id=d.thread_id,
                decision_status=d.decision_status,
            )
        )
        if len(citations) >= MAX_EVIDENCE:
            break
    caveats = []
    if any(
        index.docs[h["doc_id"]].decision_status == "proposed" for h in hits.values()
    ):
        caveats.append(
            "A proposal was found in the conversation context. It was not treated as an approval."
        )
    if re.search(r"compensation|settlement|contract value", request.query, re.I):
        gaps.append(
            "This workflow does not verify a final signed financial amount. Review the signed contract or settlement."
        )
    answer = (
        "\n".join(f"{c['quote'].strip()} [{c['id']}]" for c in citations)
        or "I could not find sufficient evidence in the selected, accessible sources."
    )
    return dict(
        answer=answer,
        citations=citations,
        abstained=not citations,
        generation_mode="bounded_investigation",
        api_cost_usd=0.0,
        compute_cost_usd=None,
        generation_ms=0.0,
        cached=False,
        path="investigator",
        retrieval_ms=sum(t["duration_ms"] for t in trace),
        total_ms=(time.perf_counter() - start) * 1000,
        graph_paths=paths,
        rewritten_query=request.query,
        corpus_version=index.fingerprint[:12],
        ranked=[c["doc_id"] for c in citations],
        limitations=["Exact excerpts establish provenance, not independent truth."]
        + caveats,
        investigation={
            "policy": "Evidence-driven deterministic controller; no LLM planner",
            "steps": trace,
            "stop_reason": stopped,
            "gaps": gaps,
            "caveats": caveats,
            "max_actions": MAX_ACTIONS,
            "max_seconds": MAX_SECONDS,
            "status": "needs_review" if gaps else "evidence_found",
            "sources": sorted(set(request.sources)),
        },
    )
