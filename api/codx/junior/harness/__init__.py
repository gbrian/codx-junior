"""
codx-junior harness: the native harness runtime of codx-junior.

The ``codx-junior`` profile is the main contact between the user and the rest
of the platform. This package provides the harness infrastructure around the
existing durable orchestration runtime:

* :mod:`.audit` — the append-only audit journal (``.codx/harness/audit.jsonl``)
  where every user request, run, step and completion is registered.
* :mod:`.watchdog` — the harness watchdog that keeps the orchestration worker
  alive: it detects a stalled worker and restarts it (or raises the alarm).
* :mod:`codx.junior.api.harness` — the REST endpoints that expose the audit
  journal and the worker health for the Harness UI.

Everything is best-effort and crash-safe by construction: records are appended
atomically, the journal is JSONL (one line per event), and the watchdog only
relies on the durable worker heartbeat files already written by the
orchestration worker.
"""
