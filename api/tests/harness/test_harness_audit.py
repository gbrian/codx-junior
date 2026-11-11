"""
Tests for the harness audit journal (``codx/junior/harness/audit.py``).

The journal must be append-only, ordered, crash-safe (concurrent appends never
corrupt a line) and it must never raise: auditing cannot break the work it
records.

Run with::

    cd api && pytest tests/harness/test_harness_audit.py -q
"""

import json
import os
import threading

from codx.junior.harness.audit import (
    HarnessAuditLog,
    audit_path,
    harness_dir,
    record_audit,
)


def test_path_layout(tmp_path):
    """The journal lives in <codx_path>/harness/audit.jsonl (codx_path = .codx)."""
    assert harness_dir(str(tmp_path)) == str(tmp_path / "harness")
    assert audit_path(str(tmp_path)) == str(tmp_path / "harness" / "audit.jsonl")


def test_record_creates_folder_and_writes_line(tmp_path):
    log = HarnessAuditLog(str(tmp_path))
    entry = log.record("task_requested", chat_id="c1", user="alice")
    assert entry["event"] == "task_requested"
    assert entry["chat_id"] == "c1"
    assert "ts" in entry
    path = audit_path(str(tmp_path))
    assert os.path.isfile(path)
    lines = open(path, encoding="utf-8").read().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event"] == "task_requested"


def test_read_returns_newest_first(tmp_path):
    log = HarnessAuditLog(str(tmp_path))
    for i in range(5):
        log.record("run_event", index=i)
    entries = log.read(limit=10)
    assert [e["index"] for e in entries] == [4, 3, 2, 1, 0]


def test_read_filter_and_pagination(tmp_path):
    log = HarnessAuditLog(str(tmp_path))
    for i in range(6):
        log.record("run_event" if i % 2 == 0 else "worker_event", index=i)
    run_events = log.read(event="run_event", limit=10)
    assert all(e["event"] == "run_event" for e in run_events)
    assert [e["index"] for e in run_events] == [4, 2, 0]
    page = log.read(limit=2, offset=1)
    assert len(page) == 2
    assert page[0]["index"] == 4


def test_read_filters_by_run_and_chat(tmp_path):
    """The diagnostic view scopes the journal to one run/task."""
    log = HarnessAuditLog(str(tmp_path))
    log.record("run_event", run_id="r1", main_chat_id="main1", step_id="s1")
    log.record("run_event", run_id="r2", main_chat_id="main2", step_id="s2")
    log.record("task_requested", chat_id="main1", user="alice")

    assert [e["run_id"] for e in log.read(run_id="r1")] == ["r1"]
    # A task filter matches both the entry chat_id and the run main_chat_id.
    entries = log.read(chat_id="main1")
    assert len(entries) == 2
    assert {e["event"] for e in entries} == {"run_event", "task_requested"}
    assert log.read(run_id="nope") == []


def test_concurrent_appends_stay_line_clean(tmp_path):
    """Many threads appending at once must produce one valid JSON per line."""
    log = HarnessAuditLog(str(tmp_path))
    threads = [
        threading.Thread(target=log.record, args=("step_finished",), kwargs={"i": i})
        for i in range(50)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    lines = open(audit_path(str(tmp_path)), encoding="utf-8").read().strip().splitlines()
    assert len(lines) == 50
    for line in lines:
        assert json.loads(line)["event"] == "step_finished"


def test_record_never_raises_with_bad_values(tmp_path):
    """Unserialisable values are coerced, never raised."""
    log = HarnessAuditLog(str(tmp_path))
    class Weird:
        def __str__(self):
            return "weird"
    entry = log.record("error", payload={"x": Weird()}, big="a" * 10000)
    assert entry is not None
    assert len(entry["big"]) < 10000


def test_record_audit_helper(tmp_path):
    entry = record_audit(str(tmp_path), "worker_recovered", pid=123)
    assert entry["event"] == "worker_recovered"
    assert entry["pid"] == 123


def test_read_missing_journal_returns_empty(tmp_path):
    assert HarnessAuditLog(str(tmp_path)).read() == []
    assert HarnessAuditLog(str(tmp_path)).exists() is False
