"""
Company — the top-level hybrid organization of codx-junior.

A **company** is the container above projects: it owns an organization
(departments and functions), hybrid teams made of humans **and** AI profiles,
the projects those teams work on, and the missions the company is executing.

The package is intentionally split so importing it is cheap and testable
without the AI stack:

* :mod:`codx.junior.company.models`  – pydantic domain model (single source of
  truth for the stored shape).
* :mod:`codx.junior.company.store`   – atomic file persistence + journal.
* :mod:`codx.junior.company.manager` – business operations (CRUD, validation,
  missions, dispatch and autonomy cycles).
* :mod:`codx.junior.company.templates` – starter organizations (SaaS, agency).
* :mod:`codx.junior.company.autopilot` – background loop that runs due cycles.
* :mod:`codx.junior.company.assistant` – the always-present manager assistant
  (answers from the company document, executes team/user/settings actions and
  asks one question at a time).
* :mod:`codx.junior.company.profile_advisor` – inspects linked projects and
  suggests which profiles/tools a new team needs (`I need an IT team`).

The REST surface lives in :mod:`codx.junior.api.company`; the profile-facing
tool lives in :mod:`codx.junior.tools.company_tools`.

Made with ❤️ by codx-junior
"""

from .models import (
    AutonomyPolicy,
    Company,
    CompanyChat,
    CompanyEvent,
    CompanyMember,
    CompanyProject,
    CompanyTeam,
    Mission,
    OrgUnit,
    SpendEntry,
)

__all__ = [
    "AutonomyPolicy",
    "Company",
    "CompanyChat",
    "CompanyEvent",
    "CompanyMember",
    "CompanyProject",
    "CompanyTeam",
    "Mission",
    "OrgUnit",
    "SpendEntry",
]

# Made with ❤️ by codx-junior
