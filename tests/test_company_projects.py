"""
Tests for company project mapping and child-project visibility.

The company maps top-level projects; discovered projects nested inside them
(e.g. ``platform/web``) must be visible to managers and to the assistant. The
assistant also handles link / unlink / create-project conversations.

Run with either::

    pytest tests/test_company_projects.py -q
    python -m unittest discover -s tests -p 'test_company_projects.py' -v
"""

import pathlib
import shutil
import tempfile
import unittest

from types import SimpleNamespace

from codx.junior.company.assistant import CompanyAssistant
from codx.junior.company.manager import CompanyManager


PROJECTS = [
    {
        "project_id": "proj_platform",
        "project_name": "Platform",
        "project_path": "/tmp/acme/platform",
        "codx_path": "/tmp/acme/platform/.codx",
    },
    {
        "project_id": "proj_web",
        "project_name": "Web Console",
        "project_path": "/tmp/acme/platform/web",
        "codx_path": "/tmp/acme/platform/web/.codx",
    },
    {
        "project_id": "proj_api",
        "project_name": "API",
        "project_path": "/tmp/acme/platform/api",
        "codx_path": "/tmp/acme/platform/api/.codx",
    },
    {
        "project_id": "proj_other",
        "project_name": "Other",
        "project_path": "/tmp/other",
        "codx_path": "/tmp/other/.codx",
    },
]


class CompanyProjectsTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="company-projects-")
        self.manager = CompanyManager(
            root_path=self.root,
            projects_provider=lambda: PROJECTS,
            users_provider=lambda: [],
            profiles_provider=lambda project_ids=None: [],
        )
        self.company = self.manager.create_company(
            {"name": "Acme", "owner": "alice"},
            actor="alice",
            project_ids=["proj_platform"],
        )
        self.assistant = CompanyAssistant(
            self.manager,
            security=SimpleNamespace(),
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def ask(self, message="", **kwargs):
        return self.assistant.respond(
            company=self.manager.get_company(self.company.id),
            message=message,
            actor="alice",
            can_manage=True,
            can_admin=True,
            **kwargs,
        )

    def test_snapshot_includes_child_projects_and_parent_reference(self):
        snapshot = self.manager.snapshot(self.company.id)
        children = {child["project_id"]: child for child in snapshot["child_projects"]}
        self.assertEqual(set(children), {"proj_web", "proj_api"})
        self.assertEqual(children["proj_web"]["parent_project_id"], "proj_platform")
        self.assertEqual(snapshot["counts"]["child_projects"], 2)
        platform = next(
            project for project in snapshot["projects"]
            if project["project_id"] == "proj_platform"
        )
        self.assertEqual(
            {child["project_id"] for child in platform["children"]},
            {"proj_web", "proj_api"},
        )

    def test_linked_child_is_not_reported_as_unmapped_child(self):
        self.manager.link_project(self.company.id, "proj_web", actor="alice")
        snapshot = self.manager.snapshot(self.company.id)
        self.assertNotIn(
            "proj_web",
            {child["project_id"] for child in snapshot["child_projects"]},
        )

    def test_assistant_lists_child_projects(self):
        response = self.ask("show projects")
        self.assertIn("Platform", response["reply"])
        self.assertIn("Web Console", response["reply"])
        self.assertIn("API", response["reply"])
        self.assertIn("child project", response["reply"])

    def test_assistant_links_a_named_project_after_confirmation(self):
        start = self.ask("link Web Console")
        self.assertEqual(start["state"]["intent"], "pending_action")
        self.assertEqual(
            start["state"]["draft"]["action"]["project_id"],
            "proj_web",
        )
        done = self.ask("ok", state=start["state"])
        self.assertTrue(done["changed"])
        linked = {
            project.project_id
            for project in self.manager.get_company(self.company.id).projects
        }
        self.assertEqual(linked, {"proj_platform", "proj_web"})

    def test_assistant_removes_a_project_after_confirmation(self):
        start = self.ask("remove project Platform")
        self.assertEqual(start["state"]["intent"], "pending_action")
        self.assertIn("remove", start["reply"].lower())
        done = self.ask("ok", state=start["state"])
        self.assertTrue(done["changed"])
        self.assertEqual(self.manager.get_company(self.company.id).projects, [])
        # The project is still discovered, only the company mapping was removed.
        self.assertTrue(any(project["project_id"] == "proj_platform" for project in PROJECTS))

    def test_assistant_starts_create_project_and_asks_for_a_name(self):
        start = self.ask("create a new project")
        self.assertEqual(start["state"]["intent"], "create_project")
        self.assertIn("call the new project", start["reply"])

        confirm = self.ask("Billing", state=start["state"])
        self.assertEqual(confirm["state"]["intent"], "pending_action")
        action = confirm["state"]["draft"]["action"]
        self.assertEqual(action["type"], "create_project")
        self.assertEqual(action["name"], "Billing")
        self.assertTrue(action["path"].endswith("billing"))


if __name__ == "__main__":
    unittest.main()
