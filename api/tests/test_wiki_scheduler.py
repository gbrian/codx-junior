"""Tests for the debounced wiki update scheduler."""

import os
import tempfile
import time
import unittest
from codx.junior.wiki.scheduler import WikiUpdateScheduler


class FakeSettings:
    def __init__(self, root, enabled=True):
        self.project_name = "demo"
        self.project_id = "demo-id"
        self.abs_project_path = root
        self.codx_path = os.path.join(root, ".codx")
        self.project_wiki = enabled
        self.wiki_auto_update = True
        self.wiki_update_debounce_seconds = 0
        self.wiki_update_max_delay_seconds = 5

    def get_project_wiki_path(self):
        return os.path.join(self.codx_path, "wiki")


class WikiUpdateSchedulerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, ".codx", "wiki"), exist_ok=True)
        self.settings = FakeSettings(self.root)
        self.processed = []
        self.processor = lambda settings, files, reason: self.processed.append(
            (settings.project_name, files, reason)
        )
        self.scheduler = WikiUpdateScheduler(
            processor=self.processor,
            notify_parent=False,
        )

    def tearDown(self):
        self.scheduler.stop()
        self.tmp.cleanup()

    def wait_processed(self, count=1, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline and len(self.processed) < count:
            time.sleep(0.02)

    def test_batches_changes_for_the_same_project(self):
        self.scheduler.schedule(self.settings, files=["a.py"], reason="change", debounce_seconds=1)
        self.scheduler.schedule(self.settings, files=["b.py"], reason="change", debounce_seconds=1)
        self.wait_processed()
        self.assertEqual(len(self.processed), 1)
        _, files, reason = self.processed[0]
        self.assertEqual(files, ["a.py", "b.py"])
        self.assertEqual(reason, "change")

    def test_disabled_project_is_not_scheduled(self):
        disabled = FakeSettings(self.root, enabled=False)
        self.assertFalse(self.scheduler.schedule(disabled, files=["a.py"]))
        self.assertEqual(self.scheduler.pending_count(), 0)

    def test_status_reports_pending_then_completed(self):
        self.scheduler.schedule(
            self.settings,
            files=["a.py"],
            debounce_seconds=1,
        )
        status = self.scheduler.status(self.settings)
        self.assertTrue(status["pending"])
        self.wait_processed()
        status = self.scheduler.status(self.settings)
        self.assertFalse(status["pending"])
        self.assertTrue(status["last_success_at"])

    def test_site_only_refresh_uses_the_refresher(self):
        refreshed = []
        scheduler = WikiUpdateScheduler(
            processor=self.processor,
            site_refresher=lambda settings: refreshed.append(settings.project_name),
            notify_parent=False,
        )
        try:
            self.assertTrue(
                scheduler.schedule(self.settings, files=[], reason="child-update", site_only=True)
            )
            deadline = time.time() + 3
            while time.time() < deadline and not refreshed:
                time.sleep(0.02)
            self.assertEqual(refreshed, ["demo"])
        finally:
            scheduler.stop()


if __name__ == "__main__":
    unittest.main()
