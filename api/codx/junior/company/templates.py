"""
Starter organizations for a new company.

A template is **data**, never a hidden business rule: it only fills the initial
org units, teams and missions. Every field can be edited afterwards with the
normal company API/tools, and templates never touch project files.

Two starters are available:

* ``saas`` — the "codx-junior cloud" example: a SaaS company that offers
  codx-junior as a service (product, engineering, growth, success) with a first
  set of missions that are safe to review before anything is dispatched.
* ``blank`` — no seeded org; just the company shell.

The SaaS template deliberately creates missions in ``draft`` (not ``ready`` and
never ``auto``): a human reviews the initial plan before the autopilot can ever
start work. That keeps "create a company from a template" a safe operation.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

from typing import List, Optional

from .models import (
    AutonomyPolicy,
    Company,
    CompanyMember,
    CompanyProject,
    CompanyTeam,
    Mission,
    new_id,
)

#: Built-in profiles the SaaS template relies on (see api/codx/junior/profiles).
SAAS_PROFILES = {
    "ceo": "project",
    "orchestrator": "orchestrator",
    "builder": "software_developer",
    "analyst": "analyst",
    "qa": "py_test",
    "writer": "wiki",
}

TEMPLATES = ("saas", "blank")


def _member(profile: str, role: str, responsibility: str = "", title: str = "") -> CompanyMember:
    """Build an AI member reference for the template."""
    return CompanyMember(
        kind="profile",
        name=profile,
        role=role,
        title=title or role,
        responsibility=responsibility,
    )


def _team(
    name: str,
    *,
    org_unit_id: str,
    description: str,
    purpose: str,
    lead: str,
    profiles: List[str],
    icon: str,
    project_ids: Optional[List[str]] = None,
    autonomy: str = "supervised",
) -> CompanyTeam:
    """Build a template team with a lead first and the given AI roster."""
    members = [_member(lead, "lead", purpose)]
    members += [_member(profile, profile.replace("_", " "), purpose) for profile in profiles if profile != lead]
    return CompanyTeam(
        id=new_id("team"),
        name=name,
        description=description,
        purpose=purpose,
        org_unit_id=org_unit_id,
        lead_kind="profile",
        lead_name=lead,
        members=members,
        project_ids=list(project_ids or []),
        autonomy=autonomy,
        icon=icon,
    )


def apply_saas_template(company: Company, project_ids: Optional[List[str]] = None) -> Company:
    """
    Seed *company* with a SaaS organization (the codx-junior cloud example).

    The seeded structure is::

        Leadership
        ├── Product
        ├── Engineering
        ├── Go To Market
        └── Customer Success

    and five hybrid teams, plus four draft missions. The first linked project
    is owned by Engineering, the second by Go To Market; when only one project
    is linked every team points at it.

    Args:
        company: Company to mutate (its existing org/teams are kept).
        project_ids: Projects to link; when empty the current company projects
            are used.

    Returns:
        The same company, seeded.
    """
    project_ids = [
        project_id
        for project_id in (project_ids or [project.project_id for project in company.projects])
        if project_id
    ]

    def project_for(index: int) -> List[str]:
        if not project_ids:
            return []
        return [project_ids[index % len(project_ids)]]

    units = {
        "leadership": new_id("org"),
        "product": new_id("org"),
        "engineering": new_id("org"),
        "gtm": new_id("org"),
        "success": new_id("org"),
    }

    company.org_units.extend(
        [
            {
                "id": units["leadership"],
                "name": "Leadership",
                "kind": "function",
                "description": "Sets direction, budget and priorities for the company.",
                "responsibilities": ["Strategy", "Budget", "Hiring and team composition"],
                "icon": "fa-solid fa-chess-king",
                "order": 0,
            },
            {
                "id": units["product"],
                "name": "Product",
                "kind": "department",
                "parent_id": units["leadership"],
                "description": "Turns the company mission into a shippable roadmap.",
                "responsibilities": ["Roadmap", "Discovery", "Acceptance criteria"],
                "icon": "fa-solid fa-map",
                "order": 1,
            },
            {
                "id": units["engineering"],
                "name": "Engineering",
                "kind": "department",
                "parent_id": units["leadership"],
                "description": "Builds, reviews and operates the platform.",
                "responsibilities": ["Delivery", "Quality", "Operations"],
                "icon": "fa-solid fa-code",
                "order": 2,
            },
            {
                "id": units["gtm"],
                "name": "Go To Market",
                "kind": "department",
                "parent_id": units["leadership"],
                "description": "Acquires customers and tells the product story.",
                "responsibilities": ["Positioning", "Pricing", "Demand"],
                "icon": "fa-solid fa-bullhorn",
                "order": 3,
            },
            {
                "id": units["success"],
                "name": "Customer Success",
                "kind": "department",
                "parent_id": units["leadership"],
                "description": "Onboards customers and keeps them successful.",
                "responsibilities": ["Onboarding", "Support", "Retention"],
                "icon": "fa-solid fa-handshake",
                "order": 4,
            },
        ]
    )
    # ``extend`` receives dicts above; validate them into OrgUnit models.
    from .models import OrgUnit  # local import keeps the module import cheap

    company.org_units = [
        unit if isinstance(unit, OrgUnit) else OrgUnit(**unit)
        for unit in company.org_units
    ]

    company.teams.extend(
        [
            _team(
                "Executive",
                org_unit_id=units["leadership"],
                description="Runs the company: strategy, priorities and cross-team unblocking.",
                purpose="Keep the company focused on the outcome that matters now",
                lead=SAAS_PROFILES["ceo"],
                profiles=[SAAS_PROFILES["analyst"]],
                icon="fa-solid fa-chess-king",
                autonomy="supervised",
            ),
            _team(
                "Product",
                org_unit_id=units["product"],
                description="Owns discovery, roadmap and acceptance criteria.",
                purpose="Decide what to build next and why",
                lead=SAAS_PROFILES["analyst"],
                profiles=[SAAS_PROFILES["writer"]],
                icon="fa-solid fa-map",
                autonomy="supervised",
            ),
            _team(
                "Platform",
                org_unit_id=units["engineering"],
                description="Builds and operates the codx-junior cloud platform.",
                purpose="Ship a reliable, multi-tenant codx-junior service",
                lead=SAAS_PROFILES["orchestrator"],
                profiles=[SAAS_PROFILES["builder"], SAAS_PROFILES["qa"]],
                icon="fa-solid fa-server",
                project_ids=project_for(0),
                autonomy="supervised",
            ),
            _team(
                "Growth",
                org_unit_id=units["gtm"],
                description="Positioning, pricing, launch and demand generation.",
                purpose="Turn the platform into a product customers buy",
                lead=SAAS_PROFILES["analyst"],
                profiles=[SAAS_PROFILES["writer"]],
                icon="fa-solid fa-bullhorn",
                project_ids=project_for(1),
                autonomy="supervised",
            ),
            _team(
                "Customer Success",
                org_unit_id=units["success"],
                description="Onboarding, support and retention playbooks.",
                purpose="Make every customer successful with codx-junior cloud",
                lead=SAAS_PROFILES["writer"],
                profiles=[SAAS_PROFILES["analyst"]],
                icon="fa-solid fa-handshake",
                autonomy="supervised",
            ),
        ]
    )

    first_project = project_ids[0] if project_ids else ""
    platform_team = next((team for team in company.teams if team.name == "Platform"), None)
    growth_team = next((team for team in company.teams if team.name == "Growth"), None)
    product_team = next((team for team in company.teams if team.name == "Product"), None)

    if first_project and not company.project(first_project):
        company.projects.append(
            CompanyProject(
                project_id=first_project,
                name="codx-junior cloud",
                role="platform",
                description="The multi-tenant SaaS platform that serves codx-junior as a service.",
                team_id=platform_team.id if platform_team else "",
                priority="critical",
            )
        )

    missions = [
        {
            "title": "Define the codx-junior cloud offering",
            "objective": (
                "Write the one-page offering for codx-junior cloud: who it is for, "
                "what is included, what is not, the pricing model and the promise. "
                "Like Shopify, the customer should be able to run codx-junior "
                "without operating the infrastructure."
            ),
            "acceptance": "A one-page offering with ICP, packaging, pricing and a clear promise.",
            "team_id": product_team.id if product_team else "",
            "priority": "high",
        },
        {
            "title": "Design tenant provisioning",
            "objective": (
                "Design the provisioning flow that creates an isolated codx-junior "
                "workspace per customer: account, project, model keys, storage, "
                "routing and lifecycle. Document the happy path and failure modes."
            ),
            "acceptance": "A design document with data model, flow diagram and failure handling.",
            "team_id": platform_team.id if platform_team else "",
            "priority": "critical",
        },
        {
            "title": "Build the onboarding checklist",
            "objective": (
                "Create the customer onboarding checklist for codx-junior cloud, "
                "from signup to first successful AI-assisted change, including "
                "guardrails and support hand-off."
            ),
            "acceptance": "A checklist a customer can follow end to end without help.",
            "team_id": growth_team.id if growth_team else "",
            "priority": "medium",
        },
        {
            "title": "Publish the launch narrative",
            "objective": (
                "Write the launch narrative and landing page copy for codx-junior "
                "cloud, using the offering and the onboarding checklist."
            ),
            "acceptance": "Landing page copy and a launch post ready for review.",
            "team_id": growth_team.id if growth_team else "",
            "priority": "low",
        },
    ]

    for mission in missions:
        company.missions.append(
            Mission(
                id=new_id("mission"),
                title=mission["title"],
                objective=mission["objective"],
                acceptance=mission["acceptance"],
                status="draft",
                priority=mission["priority"],
                team_id=mission["team_id"],
                project_id=first_project if mission["team_id"] == (platform_team.id if platform_team else "") else "",
                dispatch_mode="manual",
                source="template",
                created_by="template:saas",
                tags=["template", "saas"],
            )
        )

    if not company.mission:
        company.mission = "Offer codx-junior as a service: customers run their company on codx-junior without operating it."
    if not company.autonomy.level:
        company.autonomy = AutonomyPolicy(level="supervised")
    return company


def apply_template(company: Company, template: str, project_ids: Optional[List[str]] = None) -> Company:
    """
    Apply a named starter to *company*.

    Args:
        company: Company to seed.
        template: ``saas``, ``blank`` or empty.
        project_ids: Projects to link with the template.

    Returns:
        The same company (unchanged for ``blank``/unknown templates).
    """
    name = (template or "").strip().lower()
    if name == "saas":
        return apply_saas_template(company, project_ids=project_ids)
    return company


# Made with ❤️ by codx-junior
