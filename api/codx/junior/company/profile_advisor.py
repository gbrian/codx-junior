"""
Profile and team advisor for the company assistant.

The target user is a manager, not an engineer: they say *"I need a developer"*
or *"I need an IT team"* and expect codx-junior to know which profiles exist,
which new profiles to create and which tools those profiles need.

This module is deliberately **pure and deterministic**:

* it inspects the linked project folders to detect the stack (languages,
  frameworks, tests, Docker, CI),
* it maps a plain-language need to roles from :data:`ROLES`,
* it reuses existing project/built-in profiles whenever possible and only marks
  a role for creation when a suitable profile is missing,
* it selects tools from the runtime registry (only available names are kept),
* it returns a serializable suggestion the assistant can confirm and apply.

No AI stack is imported here, so the advisor is fast and testable.
"""

from __future__ import annotations

import json
import logging
import os
import re

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# Folders that never describe the product stack and can be huge.
IGNORED_DIRS = {
    ".git", ".hg", ".svn", ".codx", ".idea", ".vscode",
    "node_modules", "vendor", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "dist", "build", "coverage", ".next", ".nuxt", "target", "bin", "obj",
}

LANGUAGE_EXTENSIONS = {
    "python": {".py", ".pyi"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "vue": {".vue"},
    "svelte": {".svelte"},
    "go": {".go"},
    "rust": {".rs"},
    "java": {".java", ".kt", ".kts"},
    "csharp": {".cs"},
    "php": {".php"},
    "ruby": {".rb"},
    "c_cpp": {".c", ".h", ".cpp", ".hpp", ".cc"},
    "swift": {".swift"},
    "sql": {".sql"},
    "shell": {".sh", ".bash"},
    "terraform": {".tf", ".tfvars"},
}

MANIFESTS = {
    "package.json": "Node.js",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "Pipfile": "Python",
    "poetry.lock": "Poetry",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java/Maven",
    "build.gradle": "Java/Gradle",
    "composer.json": "PHP",
    "Gemfile": "Ruby",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "terraform.tf": "Terraform",
    "k8s": "Kubernetes",
}

FRONTEND_PACKAGES = (
    "vue", "react", "svelte", "next", "nuxt", "angular", "vite",
    "tailwindcss", "daisyui", "@vitejs/plugin-vue",
)
BACKEND_PACKAGES = (
    "fastapi", "django", "flask", "express", "nestjs", "rails", "spring",
    "gin", "fiber", "actix", "axum",
)
TEST_PACKAGES = (
    "jest", "vitest", "mocha", "pytest", "playwright", "cypress",
    "unittest", "phpunit", "rspec",
)

MAX_SCAN_FILES = 1200
MAX_SCAN_DEPTH = 6


# ---------------------------------------------------------------------------
# Role catalog
# ---------------------------------------------------------------------------
# Each role is a *recipe*: base profiles to compose, tools to grant and the
# responsibilities written into the generated profile. Keep descriptions in
# plain language: they are shown to a non-technical manager.

COMMON_CODE_TOOLS = [
    "project_map", "project_locate", "project_trace", "project_impact",
    "project_health", "search_codx",
    "project_read_file", "project_write_file", "project_changes",
    "apply_file_changes", "create_task",
]
COMMON_ANALYSIS_TOOLS = [
    "project_map", "project_locate", "project_trace", "project_impact",
    "project_health", "search_codx",
    "project_read_file", "project_changes", "create_task",
    "list_profiles_summary", "team_context",
]
DOCKER_TOOLS = [
    "docker_ps", "docker_logs", "docker_inspect", "docker_images",
    "docker_run", "docker_start", "docker_stop", "docker_restart",
    "docker_compose_run", "docker_compose_start", "docker_compose_stop",
    "docker_compose_restart", "docker_container", "docker_compose_service",
]
BROWSER_TOOLS = [
    "start_session", "browse_action", "get_screenshot", "get_source_code",
    "browser_activity", "finish_session", "browser_status", "browser_control",
    "list_browser_scripts", "get_browser_script", "run_browser_script",
    "save_browser_script", "delete_browser_script",
]
GIT_TOOLS = [
    "repository_overview", "repository_status", "repository_branches",
    "repository_log", "repository_compare", "repository_commit_message",
    "get_file_last_version", "create_pr_branch", "close_pr", "abandon_pr",
    "restore_changes",
]
CREATIVE_TOOLS = ["generate_image", "explain_image"]


ROLES: Dict[str, Dict[str, Any]] = {
    "it_lead": {
        "title": "IT Lead",
        "profile_name": "it_lead",
        "category": "assistant",
        "description": (
            "Coordinates the IT team, turns manager requests into concrete work "
            "and keeps the team focused on the most valuable outcome."
        ),
        "bases": ["orchestrator", "analyst", "project"],
        "tools": COMMON_ANALYSIS_TOOLS + [
            "orchestrator", "delegate", "project_manager", "project_structure",
            "list_profiles_summary", "team_context", "create_task",
        ],
        "responsibilities": [
            "Break each request into clear, small steps",
            "Decide which team member should do each step",
            "Keep the manager informed in plain language",
        ],
        "keywords": ("lead", "manager", "head", "coordinator", "it team"),
    },
    "developer": {
        "title": "Developer",
        "profile_name": "developer",
        "category": "agent",
        "description": (
            "Implements product changes, fixes bugs and writes code that fits "
            "the project's stack and conventions."
        ),
        "bases": ["software_developer", "analyst"],
        "tools": COMMON_CODE_TOOLS + GIT_TOOLS,
        "responsibilities": [
            "Read the relevant code before changing it",
            "Implement small, tested changes",
            "Explain the change and any risks in plain language",
        ],
        "keywords": ("developer", "engineer", "programmer", "coder", "software"),
    },
    "frontend_developer": {
        "title": "Frontend Developer",
        "profile_name": "frontend_developer",
        "category": "agent",
        "description": (
            "Builds and fixes the user interface: screens, components, styles "
            "and accessibility."
        ),
        "bases": ["software_developer", "arts", "analyst"],
        "tools": COMMON_CODE_TOOLS + BROWSER_TOOLS + GIT_TOOLS,
        "responsibilities": [
            "Keep the interface consistent with the existing design",
            "Check the result in a real browser",
            "Prefer simple, accessible components",
        ],
        "keywords": ("frontend", "front-end", "ui", "interface", "vue", "react"),
    },
    "backend_developer": {
        "title": "Backend Developer",
        "profile_name": "backend_developer",
        "category": "agent",
        "description": (
            "Builds the services, APIs and data access behind the product."
        ),
        "bases": ["software_developer", "analyst"],
        "tools": COMMON_CODE_TOOLS + GIT_TOOLS + [
            "project_structure", "project_manager",
        ],
        "responsibilities": [
            "Keep APIs and data models coherent",
            "Write migrations and tests for every change",
            "Watch performance and error handling",
        ],
        "keywords": ("backend", "back-end", "api", "service", "database", "server"),
    },
    "qa_engineer": {
        "title": "QA Engineer",
        "profile_name": "qa_engineer",
        "category": "agent",
        "description": (
            "Tests what the team builds, reproduces problems and protects the "
            "product from regressions."
        ),
        "bases": ["analyst", "software_developer"],
        "tools": COMMON_CODE_TOOLS + BROWSER_TOOLS + ["create_task"],
        "responsibilities": [
            "Turn requirements into clear checks",
            "Test the real user flow, not only the code",
            "Report reproducible problems with evidence",
        ],
        "keywords": ("qa", "tester", "testing", "quality", "test"),
    },
    "devops_engineer": {
        "title": "DevOps Engineer",
        "profile_name": "devops_engineer",
        "category": "agent",
        "description": (
            "Keeps the project running: containers, deployments, environments "
            "and continuous integration."
        ),
        "bases": ["software_developer", "browser", "analyst"],
        "tools": COMMON_CODE_TOOLS + DOCKER_TOOLS + GIT_TOOLS,
        "responsibilities": [
            "Keep containers and deployments reproducible",
            "Check logs and health before changing production",
            "Document how to run and recover the system",
        ],
        "keywords": ("devops", "infrastructure", "deploy", "docker", "cloud", "sre"),
    },
    "security_engineer": {
        "title": "Security Engineer",
        "profile_name": "security_engineer",
        "category": "agent",
        "description": (
            "Reviews changes for security and privacy risks and helps the team "
            "fix them."
        ),
        "bases": ["analyst", "software_developer"],
        "tools": COMMON_CODE_TOOLS + GIT_TOOLS + [
            "fetch_webpage", "duckduckgo_search", "docker_inspect",
        ],
        "responsibilities": [
            "Look for secrets, unsafe input and dangerous defaults",
            "Check dependencies and permissions",
            "Explain the risk and the safest fix",
        ],
        "keywords": ("security", "secure", "privacy", "audit", "compliance"),
    },
    "data_analyst": {
        "title": "Data Analyst",
        "profile_name": "data_analyst",
        "category": "agent",
        "description": (
            "Answers business questions with data and turns numbers into clear "
            "recommendations."
        ),
        "bases": ["analyst", "software_developer"],
        "tools": COMMON_ANALYSIS_TOOLS + ["duckduckgo_search", "fetch_webpage"],
        "responsibilities": [
            "Check the data before drawing conclusions",
            "Show the reasoning and the numbers",
            "Recommend one clear next action",
        ],
        "keywords": ("data", "analytics", "report", "metrics", "insights"),
    },
    "designer": {
        "title": "Designer",
        "profile_name": "designer",
        "category": "agent",
        "description": (
            "Creates and reviews visual and written material: screens, images, "
            "identity and content."
        ),
        "bases": ["arts", "browser"],
        "tools": CREATIVE_TOOLS + BROWSER_TOOLS + [
            "project_read_file", "project_map", "project_locate",
            "project_impact", "fetch_webpage",
        ],
        "responsibilities": [
            "Keep everything visually consistent",
            "Explain design choices in plain language",
            "Deliver usable assets, not only ideas",
        ],
        "keywords": ("design", "designer", "creative", "brand", "visual", "ux"),
    },
    "product_manager": {
        "title": "Product Manager",
        "profile_name": "product_manager",
        "category": "assistant",
        "description": (
            "Turns company goals into a clear product direction and decides what "
            "is worth building next."
        ),
        "bases": ["analyst", "project", "orchestrator"],
        "tools": COMMON_ANALYSIS_TOOLS + [
            "project_manager", "create_task", "fetch_webpage", "duckduckgo_search",
        ],
        "responsibilities": [
            "Keep the product focused on the company mission",
            "Write clear outcomes and acceptance criteria",
            "Say no to work that does not move the goal",
        ],
        "keywords": ("product", "product manager", "project manager", "pm", "roadmap", "requirements"),
    },
    "technical_writer": {
        "title": "Technical Writer",
        "profile_name": "technical_writer",
        "category": "agent",
        "description": (
            "Turns technical work into clear documentation, guides and help for "
            "customers and the team."
        ),
        "bases": ["wiki", "teacher", "analyst"],
        "tools": [
            "project_map", "project_locate", "project_trace", "project_impact",
            "project_health", "project_read_file",
            "fetch_webpage", "markdown_to_pdf", "markdown_to_docx",
            "html_to_markdown", "create_task",
        ],
        "responsibilities": [
            "Write for the reader, not for the author",
            "Keep guides short and task-oriented",
            "Update documentation with every change",
        ],
        "keywords": ("writer", "documentation", "docs", "content", "help"),
    },
    "support_engineer": {
        "title": "Support Engineer",
        "profile_name": "support_engineer",
        "category": "agent",
        "description": (
            "Handles day-to-day user problems, finds the cause and either fixes "
            "it or escalates it with evidence."
        ),
        "bases": ["browser", "analyst", "software_developer"],
        "tools": BROWSER_TOOLS + [
            "project_map", "project_locate", "project_impact",
            "project_read_file", "create_task", "fetch_webpage",
        ],
        "responsibilities": [
            "Reproduce the problem before changing anything",
            "Answer the user in plain language",
            "Escalate with logs and exact steps",
        ],
        "keywords": ("support", "help desk", "helpdesk", "customer support", "incident"),
    },
}


TEAM_PRESETS: Dict[str, Dict[str, Any]] = {
    "it": {
        "team_name": "IT Team",
        "roles": ["it_lead", "developer", "support_engineer", "devops_engineer"],
        "keywords": ("it team", "it department", "technology team", "tech team"),
    },
    "engineering": {
        "team_name": "Engineering Team",
        "roles": ["it_lead", "developer", "qa_engineer", "devops_engineer"],
        "keywords": ("development team", "dev team", "engineering team", "software team"),
    },
    "product": {
        "team_name": "Product Team",
        "roles": ["product_manager", "designer", "developer"],
        "keywords": ("product team", "product department"),
    },
    "data": {
        "team_name": "Data Team",
        "roles": ["data_analyst", "developer"],
        "keywords": ("data team", "analytics team", "data department"),
    },
    "security": {
        "team_name": "Security Team",
        "roles": ["security_engineer", "devops_engineer"],
        "keywords": ("security team", "security department"),
    },
    "support": {
        "team_name": "Support Team",
        "roles": ["support_engineer", "technical_writer", "developer"],
        "keywords": ("support team", "help desk team", "customer support team"),
    },
    "design": {
        "team_name": "Design Team",
        "roles": ["designer", "frontend_developer"],
        "keywords": ("design team", "creative team", "brand team"),
    },
}


# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------


def _package_dependencies(project_path: Path) -> List[str]:
    """Read package.json dependency names (best effort)."""
    package_json = project_path / "package.json"
    if not package_json.is_file():
        return []
    try:
        data = json.loads(package_json.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    names: List[str] = []
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        names.extend((data.get(section) or {}).keys())
    return names


def detect_stack(project_paths: Iterable[str]) -> Dict[str, Any]:
    """
    Inspect project folders and return a small, human-readable stack summary.

    The scan is bounded (files, depth, ignored folders), so a huge repository
    cannot block the assistant.
    """
    extensions: Counter = Counter()
    manifests: set = set()
    packages: set = set()
    has_tests = False
    files_seen = 0
    paths = [str(path) for path in project_paths if path]

    for raw_path in paths:
        if not raw_path:
            continue
        project_path = Path(raw_path)
        if not project_path.is_dir():
            continue
        for name in MANIFESTS:
            if (project_path / name).is_file():
                manifests.add(name)
        packages.update(_package_dependencies(project_path))

        base_depth = len(project_path.parts)
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            depth = len(Path(root).parts) - base_depth
            if depth > MAX_SCAN_DEPTH:
                dirs[:] = []
                continue
            for filename in files:
                if files_seen >= MAX_SCAN_FILES:
                    break
                files_seen += 1
                suffix = Path(filename).suffix.lower()
                for language, suffixes in LANGUAGE_EXTENSIONS.items():
                    if suffix in suffixes:
                        extensions[language] += 1
                        break
                if filename in ("Dockerfile", "docker-compose.yml", "docker-compose.yaml"):
                    manifests.add(filename)
                if filename.startswith("test_") or filename.endswith("_test.py") \
                        or ".test." in filename or ".spec." in filename:
                    has_tests = True
            if files_seen >= MAX_SCAN_FILES:
                break

    languages = [language for language, _ in extensions.most_common(5)]
    frameworks: List[str] = []
    lower_packages = {package.lower() for package in packages}
    if lower_packages & set(FRONTEND_PACKAGES) or "vue" in languages or "svelte" in languages:
        frameworks.append("frontend")
    if lower_packages & set(BACKEND_PACKAGES):
        frameworks.append("backend")
    if lower_packages & set(TEST_PACKAGES) or has_tests:
        frameworks.append("tests")
    if any("docker" in name.lower() for name in manifests):
        frameworks.append("docker")
    if "pyproject.toml" in manifests or "requirements.txt" in manifests:
        frameworks.append("python")
    if "package.json" in manifests:
        frameworks.append("node")
    # CI/config heuristics (cheap checks on the first project root).
    for raw_path in paths:
        if not raw_path:
            continue
        root = Path(raw_path)
        if (root / ".github" / "workflows").is_dir():
            frameworks.append("ci")
        if (root / "terraform.tf").is_file() or (root / "infra").is_dir():
            frameworks.append("infra")
        break

    parts: List[str] = []
    if languages:
        parts.append("Languages: " + ", ".join(languages))
    if frameworks:
        parts.append("Detected: " + ", ".join(sorted(set(frameworks))))
    if manifests:
        parts.append("Manifests: " + ", ".join(sorted(manifests)[:8]))
    return {
        "languages": languages,
        "frameworks": sorted(set(frameworks)),
        "manifests": sorted(manifests),
        "has_tests": has_tests or "tests" in frameworks,
        "has_docker": "docker" in frameworks,
        "files_seen": files_seen,
        "summary": " · ".join(parts) or "No obvious stack detected",
    }


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def _match_preset(need: str) -> Optional[str]:
    lowered = (need or "").lower()
    for preset_id, preset in TEAM_PRESETS.items():
        if any(keyword in lowered for keyword in preset["keywords"]):
            return preset_id
    return None


def _match_roles(need: str) -> List[str]:
    lowered = (need or "").lower()
    roles: List[str] = []
    for role_id, role in ROLES.items():
        if role_id == "it_lead":
            continue
        if any(keyword in lowered for keyword in role["keywords"]):
            roles.append(role_id)
    # A specialized developer role replaces the generic one for the same need.
    if any(role in roles for role in ("frontend_developer", "backend_developer")):
        roles = [role for role in roles if role != "developer"]
    # A manager/lead request maps to the IT lead when no other role matched.
    if not roles and any(word in lowered for word in ("manager", "lead", "head of")):
        roles.append("it_lead")
    # "developer" is the safe default for a generic "I need someone to build X".
    if not roles:
        roles.append("developer")
    return list(dict.fromkeys(roles))


def _clean_profile_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "").strip("._") or "profile"


def _team_name_for(need: str, mode: str, roles: List[str]) -> str:
    preset_id = _match_preset(need)
    if preset_id:
        return TEAM_PRESETS[preset_id]["team_name"]
    if mode == "team":
        if "developer" in roles and "qa_engineer" in roles:
            return "Engineering Team"
        if "data_analyst" in roles:
            return "Data Team"
        if "designer" in roles:
            return "Design Team"
        if "support_engineer" in roles:
            return "Support Team"
        return "Company Team"
    title = ROLES[roles[0]]["title"]
    return f"{title} Team"


def recommend(
    need: str,
    *,
    company_name: str = "",
    available_profiles: Optional[Iterable[str]] = None,
    available_tools: Optional[Iterable[str]] = None,
    projects: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Recommend profiles and a team for a plain-language need.

    Args:
        need: What the manager asked for ("I need an IT team", …).
        company_name: Company name, used in generated instructions.
        available_profiles: Profile names visible from the target project.
        available_tools: Tool names registered in the runtime.
        projects: Discovered projects with ``project_id``, ``project_name`` and
            ``project_path``.

    Returns:
        A serializable suggestion: ``mode`` (profile/team), ``team_name``,
        ``project``, ``stack``, ``roles`` and a markdown ``summary``.
    """
    profiles = [str(name) for name in (available_profiles or [])]
    tools = set(str(name) for name in (available_tools or []))
    project_list = list(projects or [])
    project = project_list[0] if project_list else {}

    preset_id = _match_preset(need)
    if preset_id:
        preset = TEAM_PRESETS[preset_id]
        role_ids = list(preset["roles"])
        mode = "team"
    else:
        role_ids = _match_roles(need)
        mode = "team" if len(role_ids) > 1 or " team" in f" {need} ".lower() else "profile"

    stack = detect_stack(
        [project.get("project_path") for project in project_list if project.get("project_path")]
    )

    roles: List[Dict[str, Any]] = []
    for role_id in role_ids:
        role = ROLES[role_id]
        existing = [name for name in profiles if name == role["profile_name"]]
        bases = [name for name in role["bases"] if name in profiles]
        fallback = next(
            (name for name in ("software_developer", "analyst", "project", "orchestrator") if name in profiles),
            profiles[0] if profiles else "",
        )
        if not bases and fallback:
            bases = [fallback]
        # A project profile can always be created; a base profile is preferred
        # but not mandatory (the generated instructions still work).
        create = not existing and bool(project.get("project_id"))
        profile_name = role["profile_name"] if create or existing else (
            bases[0] if bases else role["profile_name"]
        )
        selected_tools = list(dict.fromkeys(
            tool for tool in role["tools"] if not tools or tool in tools
        ))
        roles.append({
            "role_id": role_id,
            "title": role["title"],
            "profile_name": profile_name,
            "description": role["description"],
            "category": role["category"],
            "bases": bases,
            "tools": selected_tools,
            "responsibilities": list(role["responsibilities"]),
            "create": create,
            "existing": bool(existing),
            "reason": _role_reason(role_id, stack, need),
        })

    team_name = _team_name_for(need, mode, role_ids)
    summary = _summary(need, company_name, project, stack, roles, mode, team_name)
    return {
        "need": need.strip(),
        "mode": mode,
        "team_name": team_name,
        "project_id": project.get("project_id", ""),
        "project_name": project.get("project_name", ""),
        "stack": stack,
        "roles": roles,
        "summary": summary,
    }


def _role_reason(role_id: str, stack: Dict[str, Any], need: str) -> str:
    languages = ", ".join(stack.get("languages") or []) or "the detected project"
    reason = {
        "it_lead": "someone has to turn your requests into work for the team",
        "developer": f"the project uses {languages} and needs someone to change the code",
        "frontend_developer": "the project has a user interface that must be built and checked",
        "backend_developer": "the project exposes services/data that must stay reliable",
        "qa_engineer": "changes must be tested before you accept them",
        "devops_engineer": "the project needs someone to run containers/deployments"
        if stack.get("has_docker") else "the project needs someone to keep it running",
        "security_engineer": "someone should review changes for security and privacy",
        "data_analyst": "the project needs its numbers turned into decisions",
        "designer": "the product needs a consistent visual and content direction",
        "product_manager": "someone must keep the work aligned with the company goal",
        "technical_writer": "the team and customers need clear documentation",
        "support_engineer": "users need someone to reproduce and solve their problems",
    }
    return reason.get(role_id, "this role matches what you asked for")


def _summary(
    need: str,
    company_name: str,
    project: Dict[str, Any],
    stack: Dict[str, Any],
    roles: List[Dict[str, Any]],
    mode: str,
    team_name: str,
) -> str:
    project_name = project.get("project_name") or "the project"
    lines = [
        f"### For “{need.strip()}”",
        f"I looked at **{project_name}** — {stack.get('summary', 'no stack detected')}.",
        "",
    ]
    if mode == "team":
        lines.append(f"I'd create **{team_name}** with:")
    else:
        lines.append("I'd set up this profile:")
    for role in roles:
        action = "reuse" if role["existing"] else ("create" if role["create"] else "use")
        bases = ", ".join(role["bases"]) or "no base profile"
        lines.append(
            f"- **{role['title']}** — {action} `{role['profile_name']}` "
            f"(based on: {bases})"
        )
        lines.append(f"  {role['reason']}.")
    if stack.get("has_docker"):
        lines.append("")
        lines.append("The project uses Docker, so the team also gets container tools.")
    return "\n".join(lines)


def profile_content(
    role: Dict[str, Any],
    *,
    company_name: str,
    project_name: str,
    stack: Dict[str, Any],
) -> str:
    """Generate the Markdown instructions of a new profile."""
    bases = ", ".join(role.get("bases") or []) or "none"
    tools = ", ".join(role.get("tools") or []) or "the tools granted by the project"
    responsibilities = "\n".join(
        f"- {item}" for item in role.get("responsibilities") or []
    )
    stack_summary = stack.get("summary") or "No stack detected"
    return f"""# {role.get('title', role.get('profile_name'))}

You are the **{role.get('title')}** of **{company_name or 'the company'}**, working on **{project_name or 'the project'}**.

## Why you exist
{role.get('description', '')}

## What you own
{responsibilities}

## How you work
- Read the existing code and documentation before changing anything.
- Prefer small, verifiable steps over large rewrites.
- Explain decisions and risks in plain language for a non-technical manager.
- Ask for missing information instead of inventing it.
- Leave the project in a better state than you found it.

## Project context
- Stack: {stack_summary}
- Base profiles: {bases}
- Tools available: {tools}

## Handover
When you finish, summarize what changed, how it was verified and what (if
anything) the manager should decide next.
"""


# Made with ❤️ by codx-junior
