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
import sys
import tempfile
import types
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


class FakeChat:
    """Minimal hosted-chat object used by the company channel tests."""

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id", None)
        self.messages = kwargs.pop("messages", [])
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        return {
            "id": self.id,
            "name": getattr(self, "name", ""),
            "mode": getattr(self, "mode", ""),
            "profiles": getattr(self, "profiles", []),
            "users": getattr(self, "users", []),
            "updated_at": getattr(self, "updated_at", ""),
        }


# The environment running the domain tests may not have the full chat stack
# installed (db.py imports slugify). Inject a tiny db module when needed; the
# manager only needs the Chat constructor.
try:  # pragma: no cover - depends on the test environment
    import codx.junior.db  # noqa: F401
except Exception:
    _fake_db = types.ModuleType("codx.junior.db")
    _fake_db.Chat = FakeChat
    sys.modules["codx.junior.db"] = _fake_db


class FakeChatManager:
    """In-memory ChatManager stand-in (no project filesystem)."""

    def __init__(self):
        self.chats = {}

    def save_chat(self, chat, chat_only=False):
        if not getattr(chat, "id", None):
            chat.id = f"chat-{len(self.chats) + 1}"
        self.chats[chat.id] = chat
        return chat

    def find_by_id(self, chat_id=None):
        return self.chats.get(chat_id)

    def delete_chat(self, chat_id=None, file_path=None):
        self.chats.pop(chat_id, None)


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

        self.chat_manager = FakeChatManager()
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
            chat_manager_provider=lambda project_id: self.chat_manager,
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

    def test_sync_tracks_spend_without_double_counting(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(company)
        company = self.manager.dispatch_mission(company.id, mission.id, actor="alice")
        self.runs["run-1"] = {
            "status": "running",
            "progress": 50,
            "spent_cxjcoins": 12.5,
        }
        sync = self.manager.sync_missions(company.id)
        self.assertTrue(sync["spend_changed"])
        company = self.manager.get_company(company.id)
        mission = company.get_mission(mission.id)
        self.assertEqual(mission.spent_cxjcoins, 12.5)
        self.assertEqual(company.spent_cxjcoins, 12.5)
        self.assertEqual(len(company.spend), 1)

        # Syncing the same value is idempotent: no second ledger entry.
        sync = self.manager.sync_missions(company.id)
        self.assertFalse(sync["spend_changed"])
        company = self.manager.get_company(company.id)
        self.assertEqual(len(company.spend), 1)

        # A later delta adds only the difference.
        self.runs["run-1"]["spent_cxjcoins"] = 20.0
        self.manager.sync_missions(company.id)
        company = self.manager.get_company(company.id)
        self.assertEqual(company.get_mission(mission.id).spent_cxjcoins, 20.0)
        self.assertEqual(company.spent_cxjcoins, 20.0)
        self.assertEqual(len(company.spend), 2)
        self.assertEqual(
            round(sum(entry.amount for entry in company.spend), 4), 20.0
        )
        budget = self.manager.budget_state(company)
        self.assertEqual(budget["spent_total_cxjcoins"], 20.0)
        self.assertEqual(budget["spent_today_cxjcoins"], 20.0)

    def test_company_channels_use_a_hosted_project_chat(self):
        company = self.create_company()
        team = company.teams[2]
        company = self.manager.create_company_chat(
            company.id,
            name="platform",
            description="Platform team channel",
            team_id=team.id,
            actor="alice",
        )
        self.assertEqual(len(company.chats), 1)
        ref = company.chats[0]
        self.assertTrue(ref.chat_id)
        self.assertEqual(ref.project_id, "proj_platform")

        hosted = self.chat_manager.find_by_id(ref.chat_id)
        self.assertEqual(hosted.mode, "channel")
        self.assertEqual(hosted.name, "platform")
        self.assertEqual(hosted.owner_project_id, "proj_platform")
        self.assertEqual(set(hosted.profiles), set(team.profile_names))

        listed = self.manager.list_company_chats(company.id)
        self.assertEqual(len(listed), 1)
        self.assertTrue(listed[0]["available"])
        self.assertEqual(listed[0]["chat"]["name"], "platform")

        company = self.manager.update_company_chat(
            company.id, ref.chat_id, {"name": "platform-chat", "pinned": True},
            actor="alice",
        )
        self.assertEqual(company.chats[0].name, "platform-chat")
        self.assertEqual(self.chat_manager.find_by_id(ref.chat_id).name, "platform-chat")
        listed = self.manager.list_company_chats(company.id)
        self.assertTrue(listed[0]["pinned"])

        company = self.manager.delete_company_chat(company.id, ref.chat_id, actor="alice")
        self.assertEqual(company.chats, [])
        self.assertIsNone(self.chat_manager.find_by_id(ref.chat_id))

    def test_company_channel_requires_a_linked_project(self):
        company = self.manager.create_company({"name": "No project"}, actor="alice")
        with self.assertRaises(CompanyConflict):
            self.manager.create_company_chat(
                company.id, name="general", actor="alice"
            )

    def test_company_channel_syncs_team_members(self):
        company = self.create_company()
        team = company.teams[0]
        company = self.manager.create_company_chat(
            company.id, name="leadership", team_id=team.id, actor="alice"
        )
        ref = company.chats[0]
        company = self.manager.add_team_members(
            company.id, team.id, [{"kind": "user", "name": "bob", "role": "member"}],
            actor="alice",
        )
        company = self.manager.sync_company_chat_members(
            company.id, ref.chat_id, actor="alice"
        )
        hosted = self.chat_manager.find_by_id(ref.chat_id)
        self.assertIn("bob", hosted.users)

    def test_project_budget_blocks_dispatch(self):
        company = self.create_company()
        company = self.manager.link_project(
            company.id,
            "proj_platform",
            actor="alice",
            budget_cxjcoins=10.0,
        )
        company, first = self.add_ready_mission(company)
        company = self.manager.dispatch_mission(company.id, first.id, actor="alice")
        self.runs["run-1"] = {
            "status": "running",
            "progress": 70,
            "spent_cxjcoins": 10.0,
        }
        self.manager.sync_missions(company.id)

        company = self.manager.get_company(company.id)
        company, second = self.add_ready_mission(
            company, title="Second mission", objective="Do the second thing"
        )
        with self.assertRaises(CompanyConflict):
            self.manager.dispatch_mission(company.id, second.id, actor="alice")

        # The admin escape hatch still works.
        company = self.manager.dispatch_mission(
            company.id, second.id, actor="alice", force=True
        )
        self.assertEqual(company.get_mission(second.id).status, "running")

    def test_team_approval_policy_blocks_until_approved(self):
        company = self.create_company()
        team = company.teams[0]
        company = self.manager.update_team(
            company.id, team.id, {"requires_approval": True}, actor="alice"
        )
        company, mission = self.add_ready_mission(company)
        mission = company.get_mission(mission.id)
        self.assertEqual(mission.approval_status, "pending")
        with self.assertRaises(CompanyConflict):
            self.manager.dispatch_mission(company.id, mission.id, actor="alice")

        company = self.manager.approve_mission(
            company.id, mission.id, note="Looks safe", actor="alice"
        )
        mission = company.get_mission(mission.id)
        self.assertEqual(mission.approval_status, "approved")
        self.assertEqual(mission.approved_by, "alice")
        company = self.manager.dispatch_mission(company.id, mission.id, actor="alice")
        self.assertEqual(company.get_mission(mission.id).status, "running")

    def test_mission_can_require_approval_without_team_policy(self):
        company = self.create_company()
        company, mission = self.add_ready_mission(
            company, requires_approval=True
        )
        mission = company.get_mission(mission.id)
        self.assertEqual(mission.approval_status, "pending")
        with self.assertRaises(CompanyConflict):
            self.manager.dispatch_mission(company.id, mission.id, actor="alice")
        company = self.manager.deny_mission(
            company.id, mission.id, note="Not now", actor="alice"
        )
        self.assertEqual(company.get_mission(mission.id).approval_status, "denied")
        self.assertEqual(
            self.manager.snapshot(company.id)["attention"][0]["reason"], "approval"
        )

    def test_autopilot_skips_unapproved_mission(self):
        company = self.create_company()
        team = company.teams[0]
        company = self.manager.update_team(
            company.id, team.id, {"requires_approval": True}, actor="alice"
        )
        company, mission = self.add_ready_mission(company)
        company = self.manager.update_autonomy(
            company.id,
            {"enabled": True, "level": "supervised", "interval_minutes": 5},
            actor="alice",
        )
        result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(result["status"], "ran")
        self.assertEqual(result["dispatched"], [])
        self.assertEqual(len(self.dispatched), 0)
        self.assertEqual(
            self.manager.get_company(company.id).get_mission(mission.id).status,
            "ready",
        )

    def test_team_budget_blocks_dispatch(self):
        company = self.create_company()
        team = company.teams[0]
        company = self.manager.update_team(
            company.id, team.id, {"budget_cxjcoins": 10.0}, actor="alice"
        )
        company, first = self.add_ready_mission(company)
        company = self.manager.dispatch_mission(company.id, first.id, actor="alice")
        self.runs["run-1"] = {
            "status": "running",
            "progress": 60,
            "spent_cxjcoins": 10.0,
        }
        self.manager.sync_missions(company.id)

        company = self.manager.get_company(company.id)
        company, second = self.add_ready_mission(
            company, title="Second team mission", objective="Second"
        )
        with self.assertRaises(CompanyConflict):
            self.manager.dispatch_mission(company.id, second.id, actor="alice")
        budget = self.manager.budget_state(company)
        team_budget = next(
            item for item in budget["teams"] if item["team_id"] == team.id
        )
        self.assertTrue(team_budget["over_budget"])

    def test_autopilot_stops_when_daily_budget_is_exhausted(self):
        company = self.create_company()
        company, first = self.add_ready_mission(company)
        company = self.manager.update_autonomy(
            company.id,
            {
                "enabled": True,
                "level": "supervised",
                "interval_minutes": 5,
                "daily_budget_cxjcoins": 5.0,
            },
            actor="alice",
        )
        company = self.manager.dispatch_mission(company.id, first.id, actor="alice")
        self.runs["run-1"] = {
            "status": "running",
            "progress": 20,
            "spent_cxjcoins": 6.0,
        }
        self.manager.sync_missions(company.id)

        company = self.manager.get_company(company.id)
        company, second = self.add_ready_mission(
            company, title="Second mission", objective="Second"
        )
        result = self.manager.cycle(company.id, actor="autopilot", force=False)
        self.assertEqual(result["status"], "budget_exhausted")
        self.assertEqual(result["dispatched"], [])
        self.assertEqual(
            self.manager.get_company(company.id).get_mission(second.id).status,
            "ready",
        )
        events = [event["type"] for event in self.manager.journal(company.id)]
        self.assertIn("autopilot.budget_exhausted", events)

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
