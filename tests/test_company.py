"""
Tests for the company domain (models, store, manager, autonomy).

The AI runtime is not needed: the manager accepts injected project/user/profile
catalogs and a fake dispatcher, so these tests cover validation, persistence,
mission dispatch, status sync and the autonomy guard rails without a project.

Run with either::

    pytest tests/test_company.py -q
    python -m unittest tests.test_company -v
"""

import os
import shutil
import tempfile
import unittest

from datetime import datetime

from codx.junior.company.manager import (
    CompanyConflict,
    CompanyDispatchError,
    CompanyManager,
    CompanyNotFound,
    CompanyValidationError,
)
from codx.junior.company.models import CompanyMember, CompanyTeam, Mission
from codx.junior.company.store import CompanyStore


PROJECTS = [
    {
        "project_id": "proj_platform",
        "project_name": "codx-junior",
        "project_path": "/tmp/codx-junior",
        "codx_path": "/tmp/codx-junior/.codx",
    },
    {
        "project_id": "proj_console",
        "project_name": "cloud-console",
        "project_path": "/tmp/cloud-console",
        "codx_path": "/tmp/cloud-console/.codx",
    },
]

PROFILE_NAMES = (
    "orchestrator",
    "software_developer",
    "analyst",
    "project",
    "py_test",
    "wiki",
)

USERS = [{"username": "alice", "avatar": ""}, {"username": "bob", "avatar": ""}]


class FakeClock:
    """Deterministic clock used by the autonomy tests."""

    def __init__(self):
        self.now = datetime(2026, 11, 8, 9, 0, 0)

    def __call__(self):
        return self.now

    def advance(self, minutes: int):
        from datetime import timedelta

        self.now = self.now + timedelta(minutes=minutes)


class CompanyTestCase(unittest.TestCase):
    """Shared setup: a temp companies root and fake catalogs."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="company-tests-")
        self.clock = FakeClock()
        self.dispatched = []
        self.runs = {}

        def dispatcher(company, mission, brief):
            self.dispatched.append({"company": company.id, "mission": mission.id, "brief": brief})
            run_id = f"run-{len(self.dispatched)}"
            self.runs[run_id] = {"status": "running", "progress": 5}
            return {"run_id": run_id, "status": "running"}

        def run_status(project_id, run_id):
            return self.runs.get(run_id) or {"status": "running", "progress": 0}

        self.manager = CompanyManager(
            root_path=self.root,
            projects_provider=lambda: PROJECTS,
            users_provider=lambda: USERS,
            profiles_provider=lambda project_ids=None: [
                {
                    "name": name,
                    "category": "agent",
                    "description": "",
                    "projects": ["codx-junior"],
                }
                for name in PROFILE_NAMES
            ],
            dispatcher=dispatcher,
            run_status_provider=run_status,
            clock=self.clock,
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    # -- helpers -------------------------------------------------------

    def create_company(self, **overrides):
        payload = {"name": "codx-junior cloud", "mission": "Offer codx-junior as a service"}
        payload.update(overrides)
        return self.manager.create_company(
            payload,
            actor="alice",
            template="saas",
            project_ids=["proj_platform"],
        )

    def add_ready_mission(self, company, **overrides):
        team = company.teams[0]
        payload = {
            "title": "Ship the hosted provisioning flow",
            "objective": "Make it possible to provision a tenant end to end.",
            "acceptance": "A tenant can sign up and start a project.",
            "team_id": team.id,
            "project_id": "proj_platform",
            "dispatch_mode": "auto",
            "status": "ready",
        }
        payload.update(overrides)
        company = self.manager.add_mission(company.id, payload, actor="alice")
        return company, company.missions[-1]

    # -- company CRUD ---------------------------------------------------

    def test_create_company_persists_and_journals(self):
        company = self.create_company()
        self.assertTrue(company.id.startswith("cmp-"))
        self.assertEqual(company.owner, "alice")
        self.assertEqual(company.slug, "codx-junior-cloud")

        # A new manager (new process) reads the same document.
        reloaded = CompanyManager(root_path=self.root).get_company(company.id)
        self.assertEqual(reloaded.name, "codx-junior cloud")
        self.assertEqual(len(reloaded.org_units), 5)
        self.assertEqual(len(reloaded.teams), 5)
        self.assertEqual(len(reloaded.missions), 4)

        # Slug lookup and list summary.
        by_slug = self.manager.get_company("codx-junior-cloud")
        self.assertEqual(by_slug.id, company.id)
        summaries = self.manager.list_companies()
        self.assertEqual([item["id"] for item in summaries], [company.id])

        events = self.manager.journal(company.id)
        self.assertEqual(events[0]["type"], "company.created")
        self.assertEqual(events[0]["actor"], "alice")

    def test_company_name_and_slug_are_unique(self):
        self.create_company()
        with self.assertRaises(CompanyConflict):
            self.manager.create_company({"name": "codx-junior cloud"}, actor="bob")

    def test_delete_company_removes_folder(self):
        company = self.create_company()
        result = self.manager.delete_company(company.id, actor="alice")
        self.assertEqual(result["id"] if "id" in result else result["deleted"], company.id)
        with self.assertRaises(CompanyNotFound):
            self.manager.get_company(company.id)

    # -- organization / teams ------------------------------------------

    def test_org_tree_rejects_cycles(self):
        company = self.create_company()
        parent = self.manager.add_org_unit(
            company.id, {"name": "Platform"}, actor="alice"
        ).org_units[-1]
        child = self.manager.add_org_unit(
            company.id,
            {"name": "Runtime", "parent_id": parent.id},
            actor="alice",
        ).org_units[-1]
        with self.assertRaises(CompanyValidationError):
            self.manager.update_org_unit(
                company.id, parent.id, {"parent_id": child.id}, actor="alice"
            )

    def test_team_members_are_hybrid_and_lead_is_kept(self):
        company = self.create_company()
        team = company.teams[0]
        company = self.manager.add_team_members(
            company.id,
            team.id,
            [
                {"kind": "user", "name": "alice", "role": "ceo"},
                {"kind": "profile", "name": "analyst", "role": "research"},
            ],
            actor="alice",
        )
        team = company.team(team.id)
        self.assertEqual(team.human_count, 1)
        self.assertEqual(team.ai_count, len(team.profile_names))
        self.assertIn("alice", team.user_names)
        self.assertIn("analyst", team.profile_names)
        self.assertTrue(team.lead_name)

    def test_unknown_profile_is_rejected(self):
        company = self.create_company()
        with self.assertRaises(CompanyValidationError):
            self.manager.add_team(
                company.id,
                {
                    "name": "Ghosts",
                    "lead_kind": "profile",
                    "lead_name": "does_not_exist",
                    "members": ["does_not_exist"],
                },
                actor="alice",
            )

    def test_remove_team_member_moves_lead(self):
        company = self.create_company()
        team = company.teams[2]
        company = self.manager.add_team_members(
            company.id,
            team.id,
            [{"kind": "user", "name": "bob", "role": "reviewer"}],
            actor="alice",
        )
        company = self.manager.remove_team_members(
            company.id, team.id, [f"profile:{team.lead_name}"], actor="alice"
        )
        team = company.team(team.id)
        self.assertNotEqual(team.lead_name, "")
        self.assertTrue(team.lead_name in [member.name for member in team.members])

    # -- projects -------------------------------------------------------

    def test_link_and_unlink_project(self):
        company = self.create_company()
        company = self.manager.link_project(
            company.id,
            "proj_console",
            actor="alice",
            role="console",
            priority="high",
        )
        self.assertIsNotNone(company.project("proj_console"))
        self.assertEqual(company.project("proj_console").priority, "high")

        with self.assertRaises(CompanyValidationError):
            self.manager.link_project(company.id, "nope", actor="alice")

        company = self.manager.unlink_project(company.id, "proj_console", actor="alice")
        self.assertIsNone(company.project("proj_console"))

    # -- missions -------------------------------------------------------

    def test_mission_dispatch_sync_and_accept(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(company)
        company = self.manager.dispatch_mission(company.id, mission.id, actor="alice")
        mission = company.get_mission(mission.id)
        self.assertEqual(mission.status, "running")
        self.assertEqual(mission.run_id, "run-1")
        self.assertEqual(len(self.dispatched), 1)
        self.assertIn("Acceptance criteria", self.dispatched[0]["brief"])

        # Simulate the project worker completing the run.
        self.runs["run-1"] = {"status": "completed", "progress": 100}
        sync = self.manager.sync_missions(company.id)
        self.assertEqual(sync["changed"], 1)
        company = self.manager.get_company(company.id)
        self.assertEqual(company.get_mission(mission.id).status, "review")
        self.assertEqual(company.get_mission(mission.id).progress, 100)

        company = self.manager.accept_mission(
            company.id, mission.id, result="Provisioning works", actor="alice"
        )
        mission = company.get_mission(mission.id)
        self.assertEqual(mission.status, "done")
        self.assertEqual(mission.result, "Provisioning works")

    def test_dispatch_failure_keeps_mission_ready(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(company)
        self.manager._dispatcher = lambda *args: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(CompanyDispatchError):
            self.manager.dispatch_mission(company.id, mission.id, actor="alice")
        company = self.manager.get_company(company.id)
        mission = company.get_mission(mission.id)
        self.assertEqual(mission.status, "ready")
        self.assertIn("boom", mission.last_error)
        events = [event["type"] for event in self.manager.journal(company.id)]
        self.assertIn("mission.dispatch_failed", events)

    def test_invalid_transition_is_rejected(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(company)
        with self.assertRaises(CompanyValidationError):
            self.manager.transition_mission(company.id, mission.id, "done", actor="alice")

    def test_new_mission_cannot_start_running(self):
        company = self.create_company()
        team = company.teams[0]
        with self.assertRaises(CompanyValidationError):
            self.manager.add_mission(
                company.id,
                {
                    "title": "Already running",
                    "objective": "x",
                    "team_id": team.id,
                    "project_id": "proj_platform",
                    "status": "running",
                },
                actor="alice",
            )

    # -- autonomy -------------------------------------------------------

    def test_autopilot_is_off_until_enabled(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(company)
        result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(len(self.dispatched), 0)

    def test_autopilot_dispatches_one_auto_mission_per_cycle(self):
        company = self.create_company()
        company, first = self.add_ready_mission(company)
        company, second = self.add_ready_mission(
            company, title="Second mission", objective="Do the second thing"
        )
        # A manual mission must never be picked by the autopilot.
        company = self.manager.add_mission(
            company.id,
            {
                "title": "Human only",
                "objective": "Only a human dispatches this",
                "team_id": company.teams[0].id,
                "project_id": "proj_platform",
                "dispatch_mode": "manual",
                "status": "ready",
            },
            actor="alice",
        )
        company = self.manager.update_autonomy(
            company.id,
            {
                "enabled": True,
                "level": "supervised",
                "interval_minutes": 60,
                "max_missions_per_cycle": 1,
            },
            actor="alice",
        )
        result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(result["status"], "ran")
        self.assertEqual(len(result["dispatched"]), 1)
        self.assertEqual(len(self.dispatched), 1)

        # Not due yet: the interval has not elapsed.
        result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(result["status"], "not_due")

        # Next interval dispatches the second mission.
        self.clock.advance(61)
        result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(result["status"], "ran")
        self.assertEqual(len(result["dispatched"]), 1)
        self.assertEqual(len(self.dispatched), 2)
        # The manual mission is still waiting for a human.
        manual = next(
            mission for mission in self.manager.get_company(company.id).missions
            if mission.title == "Human only"
        )
        self.assertEqual(manual.status, "ready")

    def test_autopilot_skips_manual_team(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(company)
        team = company.team(mission.team_id)
        company = self.manager.update_team(
            company.id, team.id, {"autonomy": "manual"}, actor="alice"
        )
        company = self.manager.update_autonomy(
            company.id,
            {"enabled": True, "level": "supervised", "interval_minutes": 5},
            actor="alice",
        )
        result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(result["dispatched"], [])
        self.assertEqual(len(self.dispatched), 0)
        self.assertEqual(
            self.manager.get_company(company.id).get_mission(mission.id).status,
            "ready",
        )

    def test_autopilot_respects_concurrency_limit(self):
        company = self.create_company()
        company, first = self.add_ready_mission(company)
        company, second = self.add_ready_mission(
            company, title="Second mission", objective="Second"
        )
        company = self.manager.update_autonomy(
            company.id,
            {
                "enabled": True,
                "interval_minutes": 5,
                "max_concurrent_missions": 1,
                "max_missions_per_cycle": 1,
            },
            actor="alice",
        )
        first_result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(len(first_result["dispatched"]), 1)
        self.clock.advance(6)
        second_result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(second_result["status"], "ran")
        self.assertEqual(second_result["dispatched"], [])

    def test_snapshot_contains_attention_and_counts(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(company)
        company = self.manager.update_mission(
            company.id, mission.id, {"due_date": "2020-01-01"}, actor="alice"
        )
        snapshot = self.manager.snapshot(company.id)
        self.assertEqual(snapshot["company"]["name"], "codx-junior cloud")
        self.assertGreaterEqual(snapshot["counts"]["teams"], 5)
        reasons = {item["reason"] for item in snapshot["attention"]}
        self.assertIn("overdue", reasons)
        self.assertTrue(snapshot["journal"])

    def test_store_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            CompanyStore(root_path=self.root).company_dir("../escape")


class ModelTestCase(unittest.TestCase):
    """Pure model tests (no filesystem)."""

    def test_member_aliases_and_deduplication(self):
        members = CompanyMember.parse_list(
            ["analyst", "ai:analyst", {"kind": "human", "name": "alice"}, "user:alice"]
        )
        self.assertEqual(len(members), 2)
        self.assertEqual(members[0].kind, "profile")
        self.assertEqual(members[1].kind, "user")

    def test_team_lead_is_added_to_roster(self):
        team = CompanyTeam(
            name="Core",
            lead_kind="profile",
            lead_name="orchestrator",
            members=[{"kind": "user", "name": "alice", "role": "pm"}],
        )
        self.assertIn("orchestrator", team.profile_names)
        self.assertEqual(team.human_count, 1)

    def test_mission_requires_title(self):
        with self.assertRaises(Exception):
            Mission(title="", objective="x")

    def test_autonomy_is_due_after_interval(self):
        from codx.junior.company.models import AutonomyPolicy

        policy = AutonomyPolicy(enabled=True, interval_minutes=15)
        start = datetime(2026, 11, 8, 9, 0, 0)
        self.assertTrue(policy.is_due(start))
        policy.mark_cycle(now=start)
        self.assertFalse(policy.is_due(start))
        self.assertTrue(policy.is_due(start.replace(minute=16)))


if __name__ == "__main__":
    unittest.main()

# Made with ❤️ by codx-junior
