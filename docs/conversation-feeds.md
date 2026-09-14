# Conversation sources

The workspace offers independent Documents, Email, Slack and Teams toggles. These select sources already in the local index; they do not sign in to services. **72 bundled messages are fictional demo fixtures. No accounts are connected.** The source inventory reports accessible records without revealing other projects.

Reviewed exports can be imported through the command below. Stop the server before replacing an import, run with `ATLAS_DEMO=0` and configure project tokens for private imports. Anonymous demo mode intentionally excludes private imports.

```powershell
.venv\Scripts\python.exe -m atlas.conversations messages.json --provider teams --project CLIENT-ALPHA --reviewed-project-access
```

Restart the server to refresh the index. The explicit review flag records the operator's acknowledgement that **every member of the TraceLedger project may read every message in this export**. This does not import or synchronize native mailbox/channel permissions. Choose a project scope accordingly; do not import mixed-access threads into a broadly shared project.

Supported formats:

- Email: a plain-text `.eml` message, or normalized JSON. Attachments and HTML-only email are not imported.
- Slack: one channel's JSON message export (`type`, `ts`, `thread_ts`, `text`, `user`), or normalized JSON. Bot/system/subtype events are skipped. User IDs are preserved if names are unavailable.
- Teams: normalized JSON exported/transformed by the operator. This is not a native Microsoft Graph connector.

Normalized JSON uses this shape; timestamps require an explicit timezone:

```json
[
  {
    "id": "message-001",
    "thread_id": "schedule-review-001",
    "author": "Project engineer",
    "timestamp": "2026-05-14T14:00:00Z",
    "text": "The revised schedule is ready for review."
  }
]
```

An optional `source` must be an HTTPS or supported local source identifier. Message IDs and thread IDs are namespaced by project, provider and export filename; keep a unique, stable filename per account/channel. Reimporting that filename replaces its snapshot. Renaming it creates a different namespace. Normalized email should supply a consistent thread ID: `.eml` parent headers alone cannot reconstruct arbitrarily deep threads.

Imports cap at 10 MB and 1,000 messages, reject duplicate IDs and quarantine the entire export on recognized instruction-injection patterns. Approval statuses default to unspecified and are not inferred from a message claiming to be authoritative. Read full records and verify approvals independently. Private imports are excluded from the source ZIP and published benchmark reports.

Live connection work remains: provider authentication, least-privilege scopes, incremental cursors, retry/backoff, permission synchronization, deletions, retention and explicit sync-health reporting. A source toggle must never imply these are already connected.
