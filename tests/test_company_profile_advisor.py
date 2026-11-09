"""
Tests for the profile/team advisor and the assistant flow that uses it.

The advisor is pure: it inspects a temporary project folder, maps a plain
language need to roles and returns a serializable suggestion. The assistant test
injects a fake ProfileManager so no AI stack or real project settings are
needed.

Run with either::

    pytest tests/test_company_profile_advisor.py -q
    python -m unittest discover -s tests -p 'test_company_profile_advisor.py' -v
"""

import json
import pathlib
import shutil
import tempfile
import unittest

from types import SimpleNamespace

from codx.junior.company.assistant import CompanyAssistant
from codx.junior.company.manager import CompanyManager
from codx.junior.company.profile_advisor import (
    detect_stack,
    profile_content,
    recommend,
)


BASE_PROFILES = [
    "software_developer",
    "analyst",
    "orchestrator",
    "project",
    "browser",
    "arts",
    "wiki",
    "teacher",
]

TOOLS = [
    "project_search",
    "project_grep",
    "project_glob",
    "project_read_file",
    "project_write_file",
    "project_changes",
    "apply_file_changes",
    "create_task",
    "repository_log",
    "repository_status",
    "docker_ps",
    "docker_logs",
    "docker_inspect",
    "start_session",
    "browse_action",
    "get_screenshot",
    "fetch_webpage",
]


def build_project(root: str) -> None:
    """Create a tiny project folder with a detectable stack."""
    path = pathlib.Path(root)
    (path / "package.json").write_text(
        json.dumps({
            "dependencies": {"vue": "^3", "express": "^4"},
            "devDependencies": {"vitest": "^1"},
        }),
        encoding="utf-8",
    )
    (path / "Dockerfile").write_text("FROM node:20\n", encoding="utf-8")
    (path / "src").mkdir()
    (path / "src" / "App.vue").write_text("<template><div /></template>", encoding="utf-8")
    (path / "src" / "app.ts").write_text("export const app = true\n", encoding="utf-8")


class FakeProfileManager:
    """Minimal ProfileManager used by the assistant flow test."""

    def __init__(self, names, project_id):
        self.names = names
        self.project_id = project_id
        self.saved = []

    def list_all_profiles(self):
        return [SimpleNamespace(name=name) for name in self.names]

    def save_profile(self, profile):
        self.saved.append(profile)
        if profile.name not in self.names:
            self.names.append(profile.name)


class ProfileAdvisorTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="profile-advisor-")
        build_project(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def recommend(self, need):
        return recommend(
            need,
            company_name="Acme",
            available_profiles=BASE_PROFILES,
            available_tools=TOOLS,
            projects=[{
                "project_id": "p1",
                "project_name": "Acme App",
                "project_path": self.root,
            }],
        )

    def test_detects_the_project_stack(self):
        stack = detect_stack([self.root])
        self.assertIn("vue", stack["languages"])
        self.assertIn("typescript", stack["languages"])
        self.assertTrue(stack["has_docker"])
        self.assertIn("docker", stack["frameworks"])

    def test_i_need_a_developer_suggests_a_profile(self):
        suggestion = self.recommend("I need a developer")
        self.assertEqual(suggestion["mode"], "profile")
        self.assertEqual(len(suggestion["roles"]), 1)
        developer = suggestion["roles"][0]
        self.assertEqual(developer["role_id"], "developer")
        self.assertIn("software_developer", developer["bases"])
        self.assertTrue(developer["create"])
        self.assertIn("project_search", developer["tools"])
        content = profile_content(
            developer,
            company_name="Acme",
            project_name="Acme App",
            stack=suggestion["stack"],
        )
        self.assertIn("Developer", content)
        self.assertIn("software_developer", content)
        self.assertIn("Acme App", content)

    def test_i_need_an_it_team_suggests_a_team_and_profiles(self):
        suggestion = self.recommend("I need an IT team")
        self.assertEqual(suggestion["mode"], "team")
        self.assertEqual(suggestion["team_name"], "IT Team")
        role_ids = [role["role_id"] for role in suggestion["roles"]]
        self.assertIn("it_lead", role_ids)
        self.assertIn("developer", role_ids)
        self.assertIn("devops_engineer", role_ids)
        devops = next(role for role in suggestion["roles"] if role["role_id"] == "devops_engineer")
        self.assertIn("docker_ps", devops["tools"])
        self.assertIn("Docker", suggestion["summary"])

    def test_existing_profiles_are_reused(self):
        suggestion = recommend(
            "I need a developer",
            available_profiles=BASE_PROFILES + ["developer"],
            available_tools=TOOLS,
            projects=[{
                "project_id": "p1",
                "project_name": "Acme App",
                "project_path": self.root,
            }],
        )
        developer = suggestion["roles"][0]
        self.assertFalse(developer["create"])
        self.assertTrue(developer["existing"])


class AssistantBuildTeamTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="profile-advisor-project-")
        build_project(self.root)
        self.project = {
            "project_id": "proj_1",
            "project_name": "Acme App",
            "project_path": self.root,
            "codx_path": str(pathlib.Path(self.root) / ".codx"),
        }
        self.profile_names = list(BASE_PROFILES)
        self.manager = CompanyManager(
            root_path=tempfile.mkdtemp(prefix="profile-advisor-company-"),
            projects_provider=lambda: [self.project],
            users_provider=lambda: [],
            profiles_provider=lambda project_ids=None: [
                {"name": name, "category": "agent", "description": "", "projects": ["Acme App"]}
                for name in self.profile_names
            ],
        )
        self.company = self.manager.create_company(
            {"name": "Acme", "owner": "alice"},
            actor="alice",
            project_ids=["proj_1"],
        )
        self.profile_manager = FakeProfileManager(self.profile_names, self.project["project_id"])
        self.assistant = CompanyAssistant(
            self.manager,
            security=SimpleNamespace(),
            profile_manager_factory=lambda project_id: self.profile_manager,
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.manager.store.root_path, ignore_errors=True)

    def ask(self, message="", **kwargs):
        return self.assistant.respond(
            company=self.manager.get_company(self.company.id),
            message=message,
            actor="alice",
            can_manage=True,
            can_admin=True,
            **kwargs,
        )

    def test_assistant_builds_an_it_team_and_its_profiles(self):
        start = self.ask("I need an IT team")
        self.assertEqual(start["state"]["intent"], "build_team")
        self.assertEqual(start["state"]["step"], "confirm")
        self.assertIn("IT Team", start["reply"])
        option_values = [option["value"] for option in start["options"]]
        self.assertIn("create", option_values)

        done = self.ask("create", state=start["state"])
        self.assertTrue(done["changed"])
        saved = {profile.name for profile in self.profile_manager.saved}
        self.assertIn("it_lead", saved)
        self.assertIn("developer", saved)
        self.assertIn("devops_engineer", saved)
        team = self.manager.get_company(self.company.id).team_by_name("IT Team")
        self.assertIsNotNone(team)
        member_names = {member.name for member in team.members}
        self.assertIn("it_lead", member_names)
        self.assertIn("developer", member_names)
        self.assertEqual(team.lead_name, "it_lead")

    def test_assistant_creates_a_single_profile_for_a_developer_need(self):
        start = self.ask("I need a developer")
        self.assertEqual(start["state"]["step"], "confirm")
        self.assertIn("Developer", start["reply"])

        done = self.ask("create", state=start["state"])
        self.assertTrue(done["changed"])
        saved = {profile.name for profile in self.profile_manager.saved}
        self.assertIn("developer", saved)
        # A single-profile need does not create a team.
        self.assertEqual(self.manager.get_company(self.company.id).teams, [])

    def test_existing_profiles_only_does_not_create_profiles(self):
        start = self.ask("I need an IT team")
        done = self.ask("use existing profiles only", state=start["state"])
        self.assertFalse(self.profile_manager.saved)
        team = self.manager.get_company(self.company.id).team_by_name("IT Team")
        self.assertIsNotNone(team)
        self.assertTrue(team.members)


if __name__ == "__main__":
    unittest.main()
