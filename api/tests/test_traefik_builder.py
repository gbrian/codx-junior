"""
Unit tests for the custom Traefik rule builder.

Run with::

    PYTHONPATH=api /tmp/traefik-test-venv/bin/python -m pytest api/tests/test_traefik_builder.py -q
"""

from codx.junior.traefik.builder import (
    build_traefik,
    sanitize_id,
    validate_rule_structure,
)
from codx.junior.traefik.model import TraefikRule, TraefikTargetType
from codx.junior.workspaces.model import Workspace, WorkspaceApp


AUTH = "codx-junior-auth@docker"


def make_workspace():
    return Workspace(
        id="ws-id",
        name="Workspace",
        folder_path="ws1",
        apps=[
            WorkspaceApp(
                id="ext",
                name="External",
                path="http://10.0.0.5:8080/app",
            ),
            WorkspaceApp(
                id="app",
                name="App",
                path="/ws/ws1/app",
                port=3000,
            ),
        ],
    )


def make_rule(**overrides):
    data = {
        "id": "r1",
        "name": "Rule 1",
        "rule": "Host(`app.example.com`) && PathPrefix(`/public`)",
        "target_type": TraefikTargetType.URL,
        "url": "http://service:8080/base",
        "strip_prefix": True,
        "path_prefix": "/public",
    }
    data.update(overrides)
    return TraefikRule(**data)


def test_external_workspace_app_is_published():
    result = build_traefik(
        workspaces=[make_workspace()],
        global_rules=[],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    routers = result["config"]["http"]["routers"]
    services = result["config"]["http"]["services"]
    middlewares = result["config"]["http"]["middlewares"]

    rid = "codx-ws-ws1-ext"
    assert routers[rid]["rule"] == "Host(`example.com`) && PathPrefix(`/ws/ws1/ext`)"
    assert routers[rid]["service"] == rid
    assert routers[rid]["middlewares"] == [f"{rid}-strip", AUTH]
    assert services[rid]["loadBalancer"]["servers"][0]["url"] == "http://10.0.0.5:8080"
    assert middlewares[f"{rid}-strip"]["replacePathRegex"]["replacement"] == "/app/${1}"


def test_container_workspace_app_is_only_a_row():
    result = build_traefik(
        workspaces=[make_workspace()],
        global_rules=[],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    assert "codx-ws-ws1-app" not in result["config"]["http"].get("routers", {})
    row = next(row for row in result["routes"] if row["router_id"] == "codx-ws-ws1-app")
    assert row["source"] == "workspace"
    assert row["managed_by"] == "docker-labels"
    assert row["editable"] is False
    assert "codx-ws-ws1-app-strip@docker" in row["middlewares"]


def test_global_url_rule_is_published():
    rule = make_rule()
    result = build_traefik(
        workspaces=[],
        global_rules=[rule],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    routers = result["config"]["http"]["routers"]
    services = result["config"]["http"]["services"]
    middlewares = result["config"]["http"]["middlewares"]

    rid = "codx-rule-g-r1"
    assert routers[rid]["service"] == rid
    assert routers[rid]["middlewares"] == [f"{rid}-strip", AUTH]
    assert services[rid]["loadBalancer"]["servers"][0]["url"] == "http://service:8080"
    assert middlewares[f"{rid}-strip"]["replacePathRegex"]["replacement"] == "/base/${1}"

    row = next(row for row in result["routes"] if row["id"] == "r1")
    assert row["scope"] == "global"
    assert row["source"] == "custom"
    assert row["target_url"] == "http://service:8080/base"


def test_project_workspace_app_rule_reuses_docker_service():
    rule = make_rule(
        id="r2",
        target_type=TraefikTargetType.WORKSPACE_APP,
        url="",
        workspace_slug="ws1",
        app_id="app",
        strip_prefix=False,
        path_prefix="",
    )
    result = build_traefik(
        workspaces=[make_workspace()],
        global_rules=[],
        project_rule_sets=[{
            "project_id": "project-1",
            "project_name": "Project One",
            "rules": [rule],
        }],
        domain="example.com",
        auth_middleware=AUTH,
    )

    rid = "codx-rule-p-project-1-r2"
    routers = result["config"]["http"]["routers"]
    assert routers[rid]["service"] == "codx-ws-ws1-app@docker"
    assert rid not in result["config"]["http"].get("services", {})

    row = next(row for row in result["routes"] if row["id"] == "r2")
    assert row["scope"] == "project"
    assert row["project_name"] == "Project One"
    assert row["target"] == "Workspace / App"


def test_project_external_workspace_app_rule_reuses_http_service():
    rule = make_rule(
        id="r3",
        target_type=TraefikTargetType.WORKSPACE_APP,
        url="",
        workspace_slug="ws1",
        app_id="ext",
        strip_prefix=False,
        path_prefix="",
    )
    result = build_traefik(
        workspaces=[make_workspace()],
        global_rules=[],
        project_rule_sets=[{
            "project_id": "project-1",
            "project_name": "Project One",
            "rules": [rule],
        }],
        domain="example.com",
        auth_middleware=AUTH,
    )

    rid = "codx-rule-p-project-1-r3"
    assert result["config"]["http"]["routers"][rid]["service"] == "codx-ws-ws1-ext"
    assert rid not in result["config"]["http"].get("services", {})


def test_external_workspace_app_custom_strip_keeps_external_subpath():
    rule = make_rule(
        id="r3b",
        target_type=TraefikTargetType.WORKSPACE_APP,
        url="",
        workspace_slug="ws1",
        app_id="ext",
        strip_prefix=True,
        path_prefix="/public",
    )
    result = build_traefik(
        workspaces=[make_workspace()],
        global_rules=[rule],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    rid = "codx-rule-g-r3b"
    assert result["config"]["http"]["routers"][rid]["service"] == "codx-ws-ws1-ext"
    middleware = result["config"]["http"]["middlewares"][f"{rid}-strip"]
    assert middleware["replacePathRegex"]["replacement"] == "/app/${1}"


def test_container_target_creates_url_service():
    rule = make_rule(
        id="r4",
        target_type=TraefikTargetType.CONTAINER,
        url="",
        container_name="my-container",
        container_port=3000,
        strip_prefix=False,
        path_prefix="",
    )
    result = build_traefik(
        workspaces=[],
        global_rules=[rule],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    rid = "codx-rule-g-r4"
    service = result["config"]["http"]["services"][rid]
    assert service["loadBalancer"]["servers"][0]["url"] == "http://my-container:3000"


def test_disabled_rule_is_not_published():
    rule = make_rule(id="r5", enabled=False)
    result = build_traefik(
        workspaces=[],
        global_rules=[rule],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    assert "codx-rule-g-r5" not in result["config"]["http"].get("routers", {})
    row = next(row for row in result["routes"] if row["id"] == "r5")
    assert row["enabled"] is False
    assert row["issues"] == []


def test_invalid_url_rule_is_not_published_and_reports_issue():
    rule = make_rule(id="r6", url="ftp://service:21")
    result = build_traefik(
        workspaces=[],
        global_rules=[rule],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    assert "codx-rule-g-r6" not in result["config"]["http"].get("routers", {})
    row = next(row for row in result["routes"] if row["id"] == "r6")
    assert any("absolute http" in issue for issue in row["issues"])


def test_rule_structure_validation():
    assert validate_rule_structure(make_rule()) == []

    missing_target = make_rule(url="")
    assert "Target URL is required" in validate_rule_structure(missing_target)

    unbalanced = make_rule(rule="Host(`x`")
    assert any("unbalanced" in issue for issue in validate_rule_structure(unbalanced))


def test_strip_root_prefix_is_a_valid_noop():
    rule = make_rule(id="r-root", path_prefix="/", strip_prefix=True,
                     rule="PathPrefix(`/`)", url="http://service:8080")
    result = build_traefik(
        workspaces=[],
        global_rules=[rule],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    rid = "codx-rule-g-r-root"
    middleware = result["config"]["http"]["middlewares"][f"{rid}-strip"]
    assert middleware["replacePathRegex"]["regex"] == "^(.*)$"
    assert middleware["replacePathRegex"]["replacement"] == "$1"


def test_strip_without_target_subpath_uses_single_dollar_replacement():
    rule = make_rule(id="r-strip", url="http://service:8080", path_prefix="/public")
    result = build_traefik(
        workspaces=[],
        global_rules=[rule],
        project_rule_sets=[],
        domain="example.com",
        auth_middleware=AUTH,
    )

    rid = "codx-rule-g-r-strip"
    middleware = result["config"]["http"]["middlewares"][f"{rid}-strip"]
    assert middleware["replacePathRegex"]["replacement"] == "/${1}"


def test_sanitize_id():
    assert sanitize_id("Hello World!") == "hello-world"
    assert sanitize_id("", fallback="rule") == "rule"
    assert sanitize_id("a_b.c") == "a_b.c"


def test_project_rule_router_ids_are_namespaced():
    rule = make_rule(id="same")
    result = build_traefik(
        workspaces=[],
        global_rules=[rule],
        project_rule_sets=[
            {"project_id": "p1", "project_name": "P1", "rules": [rule]},
            {"project_id": "p2", "project_name": "P2", "rules": [rule]},
        ],
        domain="example.com",
        auth_middleware=AUTH,
    )

    routers = result["config"]["http"]["routers"]
    assert "codx-rule-g-same" in routers
    assert "codx-rule-p-p1-same" in routers
    assert "codx-rule-p-p2-same" in routers
