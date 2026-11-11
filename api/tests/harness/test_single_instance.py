"""
Tests for the cross-process single-instance guard.

Background supervisors (chat-turn recovery, harness watchdog) start from the
FastAPI startup hook, which uvicorn runs once per worker process. The guard must
elect exactly one owner and free the lock when the owner exits.

Run with::

    cd api && pytest tests/harness/test_single_instance.py -q
"""

from codx.junior.utils.single_instance import (
    acquire_single_instance,
    release_single_instance,
)


def test_single_instance_elects_one_owner():
    first = acquire_single_instance("test-guard-elect")
    assert first is not None
    try:
        second = acquire_single_instance("test-guard-elect")
        assert second is None
    finally:
        release_single_instance(first)

    # Releasing hands the lock over to the next process/worker.
    second = acquire_single_instance("test-guard-elect")
    assert second is not None
    release_single_instance(second)


def test_release_is_idempotent():
    release_single_instance(None)
    handle = acquire_single_instance("test-guard-idempotent")
    release_single_instance(handle)
    release_single_instance(handle)  # double release must not raise
