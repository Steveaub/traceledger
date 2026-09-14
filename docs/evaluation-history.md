# Evaluation history and dashboard

Every call to `atlas.evaluate.run` now creates a uniquely named JSON artifact under `reports/runs`. Existing run files are never overwritten by the application. The older top-level reports remain compatibility summaries for the README; the dashboard reads the new run history. These are local files, not tamper-proof audit storage—an owner can still edit or delete them manually.

Each run preserves actual start/end timestamps, code fingerprint, model revisions, corpus and question hashes, retrieval configuration, routing flags, answer mode, aggregate/slice metrics, and individual questions/answers/rankings. An exclusive temporary file is atomically published only when the full result is ready.

## Add measured runs

From the repository root, with the Python environment active:

```text
python scripts/evaluate_release.py
```

This runs the vector baseline and selected system on development and held-out questions. It uses only bundled fictional/public documents, excludes ingested uploads, and explicitly marks these runs as visible in demo mode. Each invocation adds four new runs. No fabricated dates or interpolated historical measurements are added. Use Refresh runs in Evaluation lab to load new results. This command records results; it does not tune or promote a new configuration against held-out questions.

Other benchmark commands also preserve run history, but default to restricted visibility. Private deployments require `"evaluation": true` on a server-configured principal to read these reports, because raw evaluation questions and answers may be sensitive. Ordinary project readers cannot access the evaluation endpoints. The source release packager excludes restricted run histories. Apply your own retention and backup policy before using private data.

## Compare carefully

A comparison cohort requires the same corpus hash, question hash, metric protocol, K and answer mode. Development and held-out results are separate. Code and retrieval/model configurations may differ—those are the experimental changes being compared. The API rejects comparisons across cohorts. The dashboard shows deltas and marks quality drops exceeding 0.02; this is a regression heuristic, not statistical significance. Latency deltas are reported separately and remain sensitive to hardware and load.

The trend plot uses sequential run order with timestamps available in the table, not evenly spaced calendar dates. A single point remains a single point. Missing metrics appear as unavailable. Run details include question search, a needs-review filter, pagination and JSON export. The API exposes no endpoint to launch expensive benchmark jobs or choose arbitrary filesystem paths.

## Scope of the metrics

MRR, Recall and nDCG evaluate retrieved documents. Citation relevance uses labelled document membership. Exact-quote faithfulness and term coverage are limited proxies. The benchmark is not continuously judging every live user query. Live request duration is shown beside each answer; evaluation latency is a separate warmed benchmark measurement.
