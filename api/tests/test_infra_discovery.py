"""
Unit tests for the project Docker asset scan and Dockerfile builds.

Run with::

    PYTHONPATH=api python -m unittest api.tests.test_infra_discovery -v

The tests use only the filesystem and a fake manager, so they do not need a
Docker daemon (the CLI invocation is mocked).
"""

import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from codx.junior.infra import discovery, dockerfiles
from codx.junior.infra.compose import merge_project_stacks
from codx.junior.infra.models import (
    InfraProjectDockerfileBuildRequest,
    InfraStack,
    InfraStackService,
)


def write(path, content=""):
    """Create a file (and its parent directories) with the given content."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


class FakeManager:
    """Minimal manager surface used by the Docker build helper."""

    def host_config(self, host_id=None):
        return type(
            "Host", (),
            {"id": host_id or "host-local", "endpoint": "unix:///var/run/docker.sock"},
        )()


class ProjectDiscoveryTest(unittest.TestCase):
    def setUp(self):
        discovery.invalidate_scan_cache()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        discovery.invalidate_scan_cache()
        self._tmp.cleanup()

    def test_scan_finds_compose_projects_and_dockerfiles(self):
        write(
            os.path.join(self.root, "docker-compose.yml"),
            "name: shop\nservices:\n  web:\n    build:\n      context: .\n"
            "      dockerfile: Dockerfile\n  db:\n    image: postgres:16\n",
        )
        write(
            os.path.join(self.root, "docker-compose.override.yml"),
            "services:\n  web:\n    environment:\n      DEBUG: '1'\n",
        )
        write(
            os.path.join(self.root, "Dockerfile"),
            "FROM node:20-alpine AS build\nFROM build AS runtime\n",
        )
        write(os.path.join(self.root, ".dockerignore"), "node_modules\n")

        write(
            os.path.join(self.root, "api", "compose.yaml"),
            "services:\n  worker:\n    image: busybox\n",
        )
        write(
            os.path.join(self.root, "api", "Dockerfile.dev"),
            "FROM python:3.12 AS base\n",
        )
        write(
            os.path.join(self.root, "libs", "child", "docker-compose.yml"),
            "services:\n  child:\n    image: alpine\n",
        )
        # Heavy dependency folders must never be walked.
        write(os.path.join(self.root, "node_modules", "pkg", "Dockerfile"), "FROM x\n")

        roots = [
            discovery.ScanRoot(self.root, "app"),
            discovery.ScanRoot(os.path.join(self.root, "libs", "child"), "child"),
        ]
        result = discovery.scan_project_docker(roots)
        by_name = {project.name: project for project in result.compose}

        self.assertEqual(set(by_name), {"shop", "api", "child"})
        self.assertFalse(result.cached)

        shop = by_name["shop"]
        self.assertEqual(
            [os.path.basename(path) for path in shop.files],
            ["docker-compose.yml", "docker-compose.override.yml"],
        )
        self.assertEqual(shop.declared_services, ["web", "db"])
        self.assertEqual(shop.path, os.path.join(self.root, "docker-compose.yml"))

        dockerfiles_by_name = {item.name: item for item in result.dockerfiles}
        self.assertIn("Dockerfile", dockerfiles_by_name)
        self.assertIn("Dockerfile.dev", dockerfiles_by_name)
        self.assertNotIn("Dockerfile", [item.name for item in result.dockerfiles if "node_modules" in item.path])

        root_dockerfile = dockerfiles_by_name["Dockerfile"]
        self.assertEqual(root_dockerfile.base_images, ["node:20-alpine", "build"])
        self.assertEqual(root_dockerfile.stages, ["build", "runtime"])
        self.assertEqual(root_dockerfile.compose_project, "shop")
        self.assertEqual(root_dockerfile.compose_service, "web")
        self.assertEqual(root_dockerfile.context, self.root)
        self.assertTrue(root_dockerfile.has_dockerignore)

        child = by_name["child"]
        self.assertEqual(child.project, "child")
        self.assertEqual(child.relative_path, "docker-compose.yml")

    def test_project_name_env_wins_and_directory_name_is_normalized(self):
        write(
            os.path.join(self.root, "My Project", "docker-compose.yml"),
            "services:\n  web:\n    image: nginx\n",
        )
        result = discovery.scan_project_docker([discovery.ScanRoot(os.path.join(self.root, "My Project"))])
        self.assertEqual(result.compose[0].name, "myproject")

        write(
            os.path.join(self.root, "My Project", ".env"),
            "COMPOSE_PROJECT_NAME=chosen_name\n",
        )
        discovery.invalidate_scan_cache()
        result = discovery.scan_project_docker([discovery.ScanRoot(os.path.join(self.root, "My Project"))])
        self.assertEqual(result.compose[0].name, "chosen_name")

    def test_scan_cache_can_be_bypassed(self):
        write(
            os.path.join(self.root, "docker-compose.yml"),
            "services:\n  web:\n    image: nginx\n",
        )
        roots = [discovery.ScanRoot(self.root, "app")]
        first = discovery.scan_project_docker(roots)
        self.assertFalse(first.cached)

        write(
            os.path.join(self.root, "extra", "docker-compose.yml"),
            "services:\n  extra:\n    image: alpine\n",
        )
        cached = discovery.scan_project_docker(roots)
        self.assertTrue(cached.cached)
        self.assertEqual(len(cached.compose), 1)

        forced = discovery.scan_project_docker(roots, force=True)
        self.assertFalse(forced.cached)
        self.assertEqual(len(forced.compose), 2)

    def test_resolve_compose_target_rejects_outside_roots(self):
        compose_path = write(
            os.path.join(self.root, "docker-compose.yml"),
            "services:\n  web:\n    image: nginx\n",
        )
        roots = [discovery.ScanRoot(self.root, "app")]
        found = discovery.resolve_compose_target(compose_path, roots)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, os.path.basename(self.root).lower())

        self.assertIsNone(
            discovery.resolve_compose_target(os.path.join(self.root, "README.md"), roots)
        )
        with tempfile.TemporaryDirectory() as other:
            outside = write(
                os.path.join(other, "docker-compose.yml"),
                "services:\n  web:\n    image: nginx\n",
            )
            self.assertIsNone(discovery.resolve_compose_target(outside, roots))

    def test_dockerfile_target_and_default_tag(self):
        dockerfile = write(
            os.path.join(self.root, "api", "Dockerfile.worker"),
            "FROM python:3.12 AS base\n",
        )
        roots = [discovery.ScanRoot(self.root, "app")]
        asset = discovery.resolve_dockerfile_target(dockerfile, roots)
        self.assertIsNotNone(asset)
        self.assertEqual(asset.name, "Dockerfile.worker")
        self.assertEqual(dockerfiles.default_image_tag(asset), "api-worker:latest")

        with tempfile.TemporaryDirectory() as other:
            outside = write(os.path.join(other, "Dockerfile"), "FROM alpine\n")
            self.assertIsNone(discovery.resolve_dockerfile_target(outside, roots))

    def test_build_dockerfile_runs_docker_build(self):
        dockerfile = write(
            os.path.join(self.root, "app", "Dockerfile"),
            "FROM python:3.12 AS runtime\n",
        )
        request = InfraProjectDockerfileBuildRequest(
            path=dockerfile,
            tag="app:dev",
            build_args={"VERSION": "1.2.3"},
        )
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="Step 1/2\nSuccessfully built app\n"
        )
        roots = [discovery.ScanRoot(self.root, "app")]
        with patch(
            "codx.junior.infra.dockerfiles.shutil.which", return_value="/usr/bin/docker"
        ), patch(
            "codx.junior.infra.dockerfiles.subprocess.run", return_value=completed
        ) as run:
            result = dockerfiles.build_dockerfile(FakeManager(), request, roots)

        command = run.call_args.args[0]
        self.assertEqual(result.tag, "app:dev")
        self.assertEqual(result.dockerfile, dockerfile)
        self.assertIn("--build-arg", command)
        self.assertIn("VERSION=1.2.3", command)
        self.assertEqual(command[-1], os.path.dirname(dockerfile))
        self.assertTrue(result.output)

    def test_build_dockerfile_rejects_paths_outside_the_project(self):
        with tempfile.TemporaryDirectory() as other:
            outside = write(os.path.join(other, "Dockerfile"), "FROM alpine\n")
            request = InfraProjectDockerfileBuildRequest(path=outside, tag="x:latest")
            with self.assertRaises(ValueError):
                dockerfiles.build_dockerfile(
                    FakeManager(), request, [discovery.ScanRoot(self.root, "app")]
                )


    def test_merge_project_stacks_overlays_runtime_status(self):
        asset = discovery.ComposeProject(
            name="shop",
            path=os.path.join(self.root, "docker-compose.yml"),
            directory=self.root,
            files=[os.path.join(self.root, "docker-compose.yml")],
            declared_services=["web", "db"],
            project="app",
            project_root=self.root,
            relative_path="docker-compose.yml",
        )
        runtime = InfraStack(
            name="shop",
            path=asset.path,
            status="running",
            running=1,
            total=1,
            services=[
                InfraStackService(service="web", name="web-1", state="running", id="abc")
            ],
        )
        merged = merge_project_stacks([runtime], [asset], "host-local")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].source, "project")
        self.assertEqual(merged[0].running, 1)
        self.assertEqual(merged[0].total, 2)
        self.assertEqual(merged[0].status, "degraded")
        self.assertEqual(merged[0].declared_services, ["web", "db"])

    def test_normalize_project_name(self):
        self.assertEqual(discovery.normalize_project_name("My Project (dev)"), "myprojectdev")
        self.assertEqual(discovery.normalize_project_name("__"), "")


if __name__ == "__main__":
    unittest.main()
