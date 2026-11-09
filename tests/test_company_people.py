"""
Tests for the company shell: user roles, memberships, snapshot roster and the
always-present company assistant.

The auth stack is not imported: the assistant accepts an injected security
manager, so these tests run with the same light dependencies as
``tests/test_company.py``.

Run with either::

    pytest tests/test_company_people.py -q
    python -m unittest discover -s tests -p 'test_company_people.py' -v
"""

import shutil
import tempfile
import unittest

from codx.junior.company.assistant import CompanyAssistant
from codx.junior.company.manager import CompanyManager
from codx.junior.company.models import SpendEntry, now_iso
from codx.junior.model.user import (
    COMPANY_ROLE_ADMIN,
    COMPANY_ROLE_MANAGER,
    CodxUser,
    CompanyMembership,
    USER_ROLE_ADMIN,
    USER_ROLE_COMPANY_ADMIN,
    USER_ROLE_MANAGER,
    USER_ROLE_USER,
    WORKSPACE_MODE_AUTO,
    WORKSPACE_MODE_COMPANY,
    WORKSPACE_MODE_WORK,
)


PROFILES = [
    {"name": "developer", "category": "agent", "projects": []},
    {"name": "analyst", "category": "agent", "projects": []},
]


class FakeSecurity:
    """In-memory stand-in for UserSecurityManager (no auth stack)."""

    def __init__(self):
        self.created = []
        self.removed = []

    def create_company_user(self, company_id, username, password="", email="", role="member", title="", user_role="user"):
        created = not any(item["username"] == username for item in self.created)
        membership = {"company_id": company_id, "role": role, "title": title}
        if created:
            self.created.append(
                {
                    "username": username,
                    "email": email,
                    "role": user_role,
                    "membership": membership,
                    "created": True,
                }
            )
        return {"username": username, "created": created, "membership": membership}

    def remove_company_member(self, company_id, username):
        self.removed.append((company_id, username))
        return True


class UserModelCompanyTestCase(unittest.TestCase):
    """Role-driven product shell and company memberships."""

    def test_manager_role_enters_company_mode(self):
        user = CodxUser(username="alice", role=USER_ROLE_MANAGER)
        self.assertEqual(user.resolved_workspace_mode(), WORKSPACE_MODE_COMPANY)
        self.assertTrue(user.is_company_mode)
        self.assertEqual(user.workspace_mode, WORKSPACE_MODE_AUTO)

    def test_company_admin_role_enters_company_mode(self):
        user = CodxUser(username="alice", role=USER_ROLE_COMPANY_ADMIN)
        self.assertEqual(user.resolved_workspace_mode(), WORKSPACE_MODE_COMPANY)

    def test_regular_user_keeps_working_mode(self):
        user = CodxUser(username="dev", role=USER_ROLE_USER)
        self.assertEqual(user.resolved_workspace_mode(), WORKSPACE_MODE_WORK)

    def test_admin_defaults_to_working_mode_but_can_switch(self):
        admin = CodxUser(username="root", role=USER_ROLE_ADMIN)
        self.assertEqual(admin.resolved_workspace_mode(), WORKSPACE_MODE_WORK)
        switched = CodxUser(username="root", role=USER_ROLE_ADMIN, workspace_mode="company")
        self.assertEqual(switched.resolved_workspace_mode(), WORKSPACE_MODE_COMPANY)

    def test_any_company_membership_enters_company_mode(self):
        user = CodxUser(
            username="bob",
            role=USER_ROLE_USER,
            companies=[{"company_id": "cmp-1", "role": COMPANY_ROLE_MANAGER}],
        )
        self.assertEqual(user.resolved_workspace_mode(), WORKSPACE_MODE_COMPANY)
        self.assertEqual(user.company_role("cmp-1"), COMPANY_ROLE_MANAGER)
        self.assertEqual(user.company_ids, ["cmp-1"])
        self.assertTrue(user.is_company_manager("cmp-1"))
        self.assertFalse(user.is_company_admin("cmp-1"))

    def test_explicit_work_mode_wins(self):
        user = CodxUser(
            username="bob",
            role=USER_ROLE_MANAGER,
            workspace_mode=WORKSPACE_MODE_WORK,
        )
        self.assertEqual(user.resolved_workspace_mode(), WORKSPACE_MODE_WORK)

    def test_membership_requires_company_and_valid_role(self):
        with self.assertRaises(ValueError):
            CompanyMembership(company_id="")
        with self.assertRaises(ValueError):
            CompanyMembership(company_id="cmp-1", role="owner")


class CompanyRosterAndAssistantTestCase(unittest.TestCase):
    """Snapshot roster and company-native assistant."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="company-people-tests-")
        self.users = [
            {
                "username": "alice",
                "email": "alice@example.com",
                "role": USER_ROLE_MANAGER,
                "companies": [],
            },
            {
                "username": "bob",
                "email": "bob@example.com",
                "role": USER_ROLE_USER,
                "companies": [],
            },
        ]
        self.manager = CompanyManager(
            root_path=self.root,
            projects_provider=lambda: [],
            users_provider=lambda: self.users,
            profiles_provider=lambda project_ids=None: PROFILES,
        )
        self.company = self.manager.create_company(
            {"name": "Acme cloud", "owner": "alice", "mission": "Ship"},
            actor="alice",
        )
        self.users[0]["companies"] = [
            {"company_id": self.company.id, "role": COMPANY_ROLE_ADMIN, "title": "CEO"}
        ]
        self.users[1]["companies"] = [
            {"company_id": self.company.id, "role": "member", "title": ""}
        ]
        self.company = self.manager.get_company(self.company.id)
        self.security = FakeSecurity()
        self.assistant = CompanyAssistant(self.manager, security=self.security)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def ask(self, message="", view="overview", can_manage=True, can_admin=True, **kwargs):
        return self.assistant.respond(
            company=self.manager.get_company(self.company.id),
            message=message,
            view=view,
            actor="alice",
            can_manage=can_manage,
            can_admin=can_admin,
            **kwargs,
        )

    # -- roster -------------------------------------------------------

    def test_snapshot_contains_company_members_and_roles(self):
        snapshot = self.manager.snapshot(self.company.id)
        members = {member["username"]: member for member in snapshot["members"]}
        self.assertEqual(set(members), {"alice", "bob"})
        self.assertEqual(members["alice"]["company_role"], COMPANY_ROLE_ADMIN)
        self.assertEqual(members["bob"]["company_role"], "member")
        self.assertTrue(members["alice"]["owner"])

    def test_owner_is_reported_even_without_membership(self):
        self.users[0]["companies"] = []
        members = self.manager.company_members(self.manager.get_company(self.company.id))
        alice = next(member for member in members if member["username"] == "alice")
        self.assertEqual(alice["company_role"], COMPANY_ROLE_ADMIN)

    # -- assistant answers -------------------------------------------

    def test_assistant_greets_and_reports_status(self):
        welcome = self.ask("")
        self.assertIn("codx-junior", welcome["reply"])
        self.assertTrue(welcome["suggestions"])

        status = self.ask("what needs my attention?")
        self.assertIn("Acme cloud", status["reply"])
        self.assertIn("open mission", status["reply"])

    def test_assistant_answers_budget(self):
        company = self.manager.add_mission(
            self.company.id,
            {
                "title": "Ship the thing",
                "objective": "Ship it",
                "status": "draft",
                "spent_cxjcoins": 12.5,
                "budget_cxjcoins": 20.0,
            },
            actor="alice",
        )
        mission = company.missions[-1]
        company.spend.append(
            SpendEntry(
                at=now_iso(),
                mission_id=mission.id,
                amount=12.5,
                note="test ledger",
            )
        )
        company.spent_cxjcoins = 12.5
        self.manager.store.save(company)
        self.manager.update_autonomy(
            self.company.id, {"daily_budget_cxjcoins": 10.0}, actor="alice"
        )

        answer = self.ask("how is our budget?")
        self.assertIn("Budget", answer["reply"])
        self.assertIn("12.5", answer["reply"])
        self.assertIn("exhausted", answer["reply"].lower())
        self.assertIn("Ship the thing", answer["reply"])

    def test_assistant_lists_teams_and_people(self):
        self.manager.add_team(
            self.company.id,
            {"name": "Platform", "members": ["profile:developer"]},
            actor="alice",
        )
        teams = self.ask("show teams")
        self.assertIn("Platform", teams["reply"])
        self.assertIn("developer", teams["reply"])

        people = self.ask("who is in the company?")
        self.assertIn("alice", people["reply"])
        self.assertIn("bob", people["reply"])

    # -- guided conversations (no screens, no big forms) ---------------

    def test_create_team_asks_one_question_then_creates(self):
        start = self.ask("create a team")
        self.assertIsNone(start["form"])
        self.assertEqual(start["state"]["intent"], "create_team")
        self.assertIn("call the team", start["reply"])

        confirm = self.ask("Platform", state=start["state"])
        self.assertEqual(confirm["state"]["intent"], "pending_action")
        self.assertIn("create a team", confirm["reply"].lower())

        done = self.ask("ok", state=confirm["state"])
        self.assertTrue(done["changed"])
        self.assertIsNone(done["state"])
        self.assertIsNotNone(self.manager.get_company(self.company.id).team_by_name("Platform"))
        self.assertTrue(done["suggestions"])

    def test_settings_are_only_shown_when_requested(self):
        # The assistant offers a short question, not the settings form.
        start = self.ask("open company settings")
        self.assertIsNone(start["form"])
        self.assertEqual(start["state"]["intent"], "edit_company")

        # "Show all settings" is the explicit request that renders the form.
        full = self.ask("show all settings", state=start["state"])
        self.assertEqual(full["form"]["id"], "edit_company")

    def test_company_details_flow_updates_without_a_form(self):
        start = self.ask("open company settings")
        field = self.ask("Mission", state=start["state"])
        self.assertEqual(field["state"]["step"], "value")
        confirm = self.ask("Make customers happy", state=field["state"])
        self.assertEqual(confirm["state"]["intent"], "pending_action")
        done = self.ask("fine", state=confirm["state"])
        self.assertTrue(done["changed"])
        self.assertIsNone(done["state"])
        self.assertEqual(self.manager.get_company(self.company.id).mission, "Make customers happy")

    def test_manager_can_add_team_member_by_chat(self):
        self.manager.add_team(
            self.company.id,
            {"name": "Platform", "members": ["profile:developer"]},
            actor="alice",
        )
        response = self.ask("Could you add alice to the Platform team?")
        self.assertEqual(response["state"]["intent"], "pending_action")
        done = self.ask("sure", state=response["state"])
        self.assertTrue(done["changed"])
        team = self.manager.get_company(self.company.id).team_by_name("Platform")
        self.assertTrue(any(member.name == "alice" for member in team.members))

    def test_add_person_flow_asks_name_then_role(self):
        start = self.ask("add a person", can_admin=True)
        self.assertEqual(start["state"]["intent"], "add_user")
        self.assertEqual(start["state"]["step"], "name")
        self.assertIn("Who would you like to add", start["reply"])

        named = self.ask("Carol Smith", state=start["state"])
        self.assertEqual(named["state"]["step"], "role")
        option_values = [option.get("value") for option in named["options"]]
        self.assertIn("manager", option_values)

        confirm = self.ask("Help run the company", state=named["state"])
        self.assertEqual(confirm["state"]["intent"], "pending_action")
        done = self.ask("okay", state=confirm["state"])
        self.assertTrue(done["changed"])
        self.assertIsNone(done["state"])
        self.assertEqual(self.security.created[0]["username"], "carol.smith")
        self.assertEqual(self.security.created[0]["membership"]["role"], "manager")
        self.assertIn("temporary password", done["reply"])

    def test_natural_order_confirm_and_cancel(self):
        self.manager.add_team(
            self.company.id,
            {"name": "Platform", "members": ["profile:developer"]},
            actor="alice",
        )
        confirm = self.ask("Could you please add alice to the Platform team?")
        self.assertEqual(confirm["state"]["intent"], "pending_action")
        cancelled = self.ask("no thanks", state=confirm["state"])
        self.assertIsNone(cancelled["state"])
        team = self.manager.get_company(self.company.id).team_by_name("Platform")
        self.assertFalse(any(member.name == "alice" for member in team.members))

        confirm = self.ask("Please add alice to the Platform team.")
        done = self.ask("fine", state=confirm["state"])
        self.assertTrue(done["changed"])
        team = self.manager.get_company(self.company.id).team_by_name("Platform")
        self.assertTrue(any(member.name == "alice" for member in team.members))

    def test_only_company_admins_can_add_users(self):
        denied = self.ask("add a person", can_admin=False)
        self.assertIn("company admin", denied["reply"])
        self.assertIsNone(denied.get("state"))

    def test_mission_flow_creates_a_draft_without_projects(self):
        start = self.ask("create a mission")
        self.assertEqual(start["state"]["intent"], "create_mission")
        self.assertEqual(start["state"]["step"], "title")

        confirm = self.ask("Ship onboarding", state=start["state"])
        self.assertEqual(confirm["state"]["intent"], "pending_action")
        done = self.ask("yes", state=confirm["state"])
        self.assertTrue(done["changed"])
        self.assertIsNone(done["state"])
        missions = self.manager.get_company(self.company.id).missions
        self.assertEqual([mission.title for mission in missions], ["Ship onboarding"])
        self.assertEqual(missions[0].status, "draft")

    def test_review_flow_asks_before_accepting(self):
        company = self.manager.add_mission(
            self.company.id,
            {"title": "Ship onboarding", "status": "draft"},
            actor="alice",
        )
        mission = company.missions[0]
        # Move the mission to review (normally done by the run sync).
        company = self.manager.get_company(self.company.id)
        company.get_mission(mission.id).status = "review"
        self.manager.store.save(company)

        start = self.ask("Review mission Ship onboarding")
        self.assertEqual(start["state"]["intent"], "review_mission")
        self.assertIn("accept the result", start["reply"].lower())

        confirm = self.ask("accept", state=start["state"])
        self.assertEqual(confirm["state"]["intent"], "pending_action")
        done = self.ask("confirm", state=confirm["state"])
        self.assertTrue(done["changed"])
        self.assertEqual(
            self.manager.get_company(self.company.id).get_mission(mission.id).status,
            "done",
        )

    def test_read_only_role_cannot_manage_teams(self):
        response = self.ask("create a team", can_manage=False, can_admin=False)
        self.assertIn("can't", response["reply"])
        self.assertIsNone(response["form"])

    def test_delete_company_requires_confirmation_and_admin(self):
        denied = self.ask("delete company", can_admin=False)
        self.assertIn("company admin", denied["reply"])

        first = self.ask("delete company")
        self.assertEqual(first["state"]["intent"], "pending_action")
        self.assertIn("delete", first["reply"].lower())
        self.assertTrue(self.manager.get_company(self.company.id))

        confirmed = self.ask("ok", state=first["state"])
        self.assertTrue(confirmed["changed"])
        self.assertTrue(confirmed.get("deleted"))
        self.assertFalse(self.manager.store.exists(self.company.id))

    def test_delete_team_requires_confirmation(self):
        self.manager.add_team(self.company.id, {"name": "Platform"}, actor="alice")
        first = self.ask("delete team Platform")
        self.assertEqual(first["state"]["intent"], "pending_action")
        self.assertIn("delete", first["reply"].lower())
        self.assertIsNotNone(self.manager.get_company(self.company.id).team_by_name("Platform"))

        confirmed = self.ask("yes, do it", state=first["state"])
        self.assertTrue(confirmed["changed"])
        self.assertIsNone(self.manager.get_company(self.company.id).team_by_name("Platform"))


if __name__ == "__main__":
    unittest.main()
