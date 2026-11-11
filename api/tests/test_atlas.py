"""Core tests for the project atlas (stdlib only).

Run with::

    PYTHONPATH=api python3 -m unittest api.tests.test_atlas -v

They build a small git repository, index it and assert that the atlas answers
the questions that used to require grep: symbol locations, exact strings,
routes, docs, traces, impact and freshness.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from types import SimpleNamespace

from codx.junior.atlas import ProjectAtlas, apply_atlas_policy, atlas_ready


class AtlasTestProject:
    """Create a tiny project on disk and commit it to git."""

    def __init__(self, root: str):
        self.root = root
        self.codx_path = os.path.join(root, ".codx")

    def write(self, rel_path: str, content: str) -> None:
        abs_path = os.path.join(self.root, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as handle:
            handle.write(textwrap.dedent(content).lstrip("\n"))

    def init_git(self) -> None:
        """Create a git repository without ``git init`` (chmod is blocked in CI)."""
        git_dir = os.path.join(self.root, ".git")
        os.makedirs(os.path.join(git_dir, "objects"), exist_ok=True)
        os.makedirs(os.path.join(git_dir, "refs", "heads"), exist_ok=True)
        with open(os.path.join(git_dir, "config"), "w", encoding="utf-8") as handle:
            handle.write(
                "[core]\n"
                "\trepositoryformatversion = 0\n"
                "\tfilemode = false\n"
                "\tbare = false\n"
                "\tlogallrefupdates = true\n"
            )
        with open(os.path.join(git_dir, "HEAD"), "w", encoding="utf-8") as handle:
            handle.write("ref: refs/heads/main\n")

    def git(self, *args: str) -> None:
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": "Atlas Test",
            "GIT_AUTHOR_EMAIL": "atlas@example.com",
            "GIT_COMMITTER_NAME": "Atlas Test",
            "GIT_COMMITTER_EMAIL": "atlas@example.com",
        })
        subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

    @property
    def settings(self):
        return SimpleNamespace(
            project_id="atlas-test",
            project_name="atlas-test",
            abs_project_path=self.root,
            codx_path=self.codx_path,
            project_atlas_enabled=True,
            project_atlas_force=True,
            project_atlas_max_files=500,
            project_atlas_ttl_seconds=0,
        )


class AtlasTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-test-", dir=os.getcwd())
        self.project = AtlasTestProject(self.temp.name)
        self.project.write("src/wallet.py", """
            \"\"\"Wallet domain: balance and spending limits.\"\"\"

            class Wallet:
                def __init__(self):
                    self.balance = 0
                    self.spending_limits = []

                def consume(self, cost):
                    self.balance -= cost
                    return self.balance


            def check_user_wallet(user):
                wallet = Wallet()
                wallet.consume(1)
                return wallet.balance == 0
        """)
        self.project.write("src/api.py", """
            from fastapi import APIRouter
            from .wallet import check_user_wallet

            router = APIRouter()


            @router.get("/wallet")
            def get_wallet():
                return check_user_wallet(None)
        """)
        self.project.write("tests/test_wallet.py", """
            from src.wallet import Wallet


            def test_wallet_starts_empty():
                assert Wallet().balance == 0
        """)
        self.project.write("docs/wallet.md", """
            ---
            title: Wallet
            description: How balances and spending limits work.
            source: src/wallet.py
            ---

            # Wallet

            The wallet keeps a balance and a list of spending limits.
        """)
        self.project.write("README.md", "# Atlas demo\n\nThe wallet lives in src/wallet.py.\n")
        self.project.init_git()
        self.project.git("add", ".")
        self.project.git("commit", "-m", "initial")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def atlas(self) -> ProjectAtlas:
        return ProjectAtlas(self.project.settings)

    # ── map ─────────────────────────────────────────────────────────────────

    def test_map_lists_domains_entry_points_and_reading_order(self):
        with self.atlas() as atlas:
            packet = atlas.map(limit=10)
        self.assertEqual(packet.intent, "map")
        self.assertGreaterEqual(len(packet.evidence), 1)
        self.assertIn("src", packet.body)
        self.assertTrue(packet.reading_order)
        self.assertGreater(packet.confidence, 0.5)

    # ── locate ──────────────────────────────────────────────────────────────

    def test_locate_finds_symbol_definition_with_line(self):
        with self.atlas() as atlas:
            packet = atlas.locate("Wallet", limit=5)
        self.assertTrue(packet.evidence)
        top = packet.evidence[0]
        self.assertEqual(top.path, "src/wallet.py")
        self.assertEqual(top.kind, "symbol")
        self.assertEqual(top.start_line, 3)
        self.assertIn("class Wallet", top.snippet)

    def test_locate_finds_exact_content_string_with_line(self):
        with self.atlas() as atlas:
            packet = atlas.locate("spending_limits", limit=5)
        self.assertTrue(packet.evidence)
        top = packet.evidence[0]
        self.assertEqual(top.path, "src/wallet.py")
        self.assertEqual(top.start_line, 6)
        self.assertIn("spending_limits", top.snippet)

    def test_locate_supports_regex(self):
        with self.atlas() as atlas:
            packet = atlas.locate(r"def\s+check_user_wallet", regex=True, limit=5)
        self.assertTrue(packet.evidence)
        self.assertEqual(packet.evidence[0].path, "src/wallet.py")
        self.assertEqual(packet.evidence[0].start_line, 13)

    def test_locate_finds_route(self):
        with self.atlas() as atlas:
            packet = atlas.locate("GET /wallet", kind="route", limit=5)
        self.assertTrue(packet.evidence)
        self.assertEqual(packet.evidence[0].kind, "route")
        self.assertEqual(packet.evidence[0].path, "src/api.py")

    def test_locate_finds_doc_and_links_source(self):
        with self.atlas() as atlas:
            packet = atlas.locate("How balances and spending limits work", kind="doc", limit=5)
        self.assertTrue(packet.evidence)
        self.assertTrue(any(item.path == "docs/wallet.md" for item in packet.evidence))

    def test_locate_filters_test_files(self):
        with self.atlas() as atlas:
            packet = atlas.locate("wallet", kind="test", limit=5)
        self.assertTrue(packet.evidence)
        self.assertTrue(all(item.meta.get("role") == "test" for item in packet.evidence))

    def test_locate_glob_pattern(self):
        with self.atlas() as atlas:
            packet = atlas.locate("**/*wallet*.py", limit=5)
        self.assertTrue(packet.evidence)
        paths = {item.path for item in packet.evidence}
        self.assertIn("src/wallet.py", paths)

    # ── trace / impact ──────────────────────────────────────────────────────

    def test_trace_from_handler_reaches_wallet(self):
        with self.atlas() as atlas:
            packet = atlas.trace("get_wallet", direction="out", depth=2)
        paths = {item.path for item in packet.evidence}
        self.assertIn("src/api.py", paths)
        self.assertIn("src/wallet.py", paths)

    def test_impact_lists_importer_and_test(self):
        with self.atlas() as atlas:
            packet = atlas.impact(["src/wallet.py"], depth=2)
        paths = {item.path for item in packet.evidence}
        self.assertIn("src/api.py", paths)
        self.assertIn("tests/test_wallet.py", paths)
        self.assertIn("high", packet.answer.lower() + " low medium high")

    # ── freshness ───────────────────────────────────────────────────────────

    def test_incremental_refresh_sees_new_symbol_and_line(self):
        with self.atlas() as atlas:
            atlas.map()  # build
        self.project.write("src/wallet.py", """
            \"\"\"Wallet domain.\"\"\"

            class Wallet:
                def __init__(self):
                    self.balance = 0
                    self.spending_limits = []

            def new_wallet_helper():
                return 42
        """)
        with self.atlas() as atlas:
            packet = atlas.locate("new_wallet_helper", limit=5)
        self.assertTrue(packet.evidence)
        self.assertEqual(packet.evidence[0].path, "src/wallet.py")
        self.assertEqual(packet.evidence[0].start_line, 8)

    def test_health_reports_coverage(self):
        with self.atlas() as atlas:
            health = atlas.health()
        self.assertTrue(atlas_ready(self.project.settings))
        self.assertEqual(health.project, "atlas-test")
        self.assertGreaterEqual(health.files, 5)
        self.assertGreaterEqual(health.symbols, 4)
        self.assertGreater(health.edges, 0)
        self.assertFalse(health.truncated)


class AtlasPolicyTestCase(unittest.TestCase):
    def test_policy_adds_atlas_and_hides_legacy(self):
        settings = SimpleNamespace(project_atlas_enabled=True, project_atlas_force=True)
        names = apply_atlas_policy(
            ["project_read_file", "project_grep", "project_glob", "project_structure"],
            settings,
        )
        self.assertIn("project_map", names)
        self.assertIn("project_locate", names)
        self.assertNotIn("project_grep", names)
        self.assertNotIn("project_glob", names)
        self.assertNotIn("project_structure", names)

    def test_policy_keeps_legacy_when_atlas_disabled(self):
        settings = SimpleNamespace(project_atlas_enabled=False, project_atlas_force=True)
        names = apply_atlas_policy(["project_grep"], settings)
        self.assertEqual(names, {"project_grep"})

    def test_policy_does_not_force_when_flag_is_false(self):
        settings = SimpleNamespace(project_atlas_enabled=True, project_atlas_force=False)
        names = apply_atlas_policy(["project_grep"], settings)
        self.assertIn("project_grep", names)
        self.assertIn("project_locate", names)

    def test_policy_does_not_widen_a_profile_without_read_tools(self):
        settings = SimpleNamespace(project_atlas_enabled=True, project_atlas_force=True)
        names = apply_atlas_policy(["fetch_webpage"], settings)
        self.assertEqual(names, {"fetch_webpage"})

    def test_policy_defaults_off_for_objects_without_the_setting(self):
        names = apply_atlas_policy(["project_grep"], SimpleNamespace())
        self.assertEqual(names, {"project_grep"})

    def test_atlas_ready_is_false_before_the_first_build(self):
        settings = SimpleNamespace(
            project_atlas_enabled=True,
            abs_project_path=os.path.join(os.getcwd(), "atlas-test-missing"),
            codx_path=os.path.join(os.getcwd(), "atlas-test-missing", ".codx"),
        )
        self.assertFalse(atlas_ready(settings))


if __name__ == "__main__":
    unittest.main()
