"""Tests for the modern wiki docs-site manifest."""

import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from codx.junior.wiki.site import (
    WikiSiteBuilder,
    first_paragraph,
    parse_frontmatter,
    profile_text,
    render_profile_placeholders,
)


class FakeSettings:
    """Subset of CODXJuniorSettings used by the site builder."""

    def __init__(self, root):
        self.project_name = "demo"
        self.project_id = "demo-id"
        self.abs_project_path = root
        self.codx_path = os.path.join(root, ".codx")
        self.project_wiki = True
        self.project_icon = ""
        self.repo_url = ""
        self.project_dependencies = ""
        self.project_wiki_path = None
        self.wiki_auto_update = True

    def get_project_wiki_path(self):
        return os.path.join(self.codx_path, "wiki")

    def get_project_dependencies(self):
        return []

    def get_sub_projects(self):
        return []


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


class WikiSiteBuilderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.settings = FakeSettings(self.root)
        self.wiki = self.settings.get_project_wiki_path()
        write(
            os.path.join(self.wiki, "home.md"),
            "---\ntitle: Demo\ndescription: A demo project page\ntags: [overview]\n---\n"
            "# Demo\n\nWelcome to the demo project documentation.\n",
        )
        write(
            os.path.join(self.wiki, "guides", "auth.md"),
            "---\ntitle: Authentication\ndescription: How login works\ntags: [auth, security]\n---\n"
            "# Authentication\n\n## Overview\n\nLogin uses a token. " + ("word " * 220) + "\n",
        )
        write(
            os.path.join(self.wiki, "domains", "billing.md"),
            "---\ntitle: Billing\ndescription: Billing domain\n---\n"
            "# Billing\n\n```mermaid\nflowchart TD\n  A-->B\n```\n",
        )
        self.builder = WikiSiteBuilder(settings=self.settings)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self):
        with patch.object(
            WikiSiteBuilder, "_project_description", return_value="A demo project."
        ), patch.object(
            WikiSiteBuilder, "_detect_project_kind", return_value=("code", ["Python"])
        ), patch.object(
            WikiSiteBuilder, "_related_projects", return_value=([], None)
        ):
            return self.builder.build()

    def test_build_creates_manifest_navigation_and_derived_files(self):
        site = self.build()
        self.assertEqual(site["version"], 2)
        self.assertEqual(site["project"]["name"], "demo")
        self.assertIn("guides/auth", site["pages"])
        sections = {section["title"] for section in site["navigation"]}
        self.assertIn("Overview", sections)
        self.assertIn("Architecture", sections)
        self.assertGreaterEqual(site["stats"]["pages"], 3)
        self.assertTrue(os.path.isfile(os.path.join(self.wiki, "docs.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.wiki, "llms.txt")))
        self.assertTrue(os.path.isfile(os.path.join(self.wiki, ".vitepress", "config.json")))
        with open(os.path.join(self.wiki, "docs.json"), encoding="utf-8") as handle:
            saved = json.load(handle)
        self.assertEqual(saved["project"]["name"], "demo")

    def test_page_metadata_and_frontmatter_stripping(self):
        self.build()
        page = self.builder.page("guides/auth")
        self.assertIsNotNone(page)
        self.assertEqual(page["title"], "Authentication")
        self.assertEqual(page["tags"], ["auth", "security"])
        self.assertNotIn("---", page["content"][:20])
        self.assertGreaterEqual(page["reading_time"], 1)
        self.assertTrue(page["headings"])

    def test_manifest_is_rebuilt_when_a_page_is_newer(self):
        self.build()
        self.assertFalse(self.builder.is_stale())
        path = os.path.join(self.wiki, "guides", "auth.md")
        write(path, "# Authentication\n\nUpdated content.\n")
        # Force a timestamp clearly after the manifest regardless of filesystem
        # granularity (the production check uses mtimes).
        future = time.time() + 5
        os.utime(path, (future, future))
        self.assertTrue(self.builder.is_stale())
        site = self.builder.build_if_stale()
        self.assertIn("guides/auth", site["pages"])
        past = time.time() - 1
        os.utime(path, (past, past))
        self.assertFalse(self.builder.is_stale())
        status = self.builder.manifest_status()
        self.assertTrue(status["exists"])
        self.assertFalse(status["stale"])
        self.assertGreaterEqual(status["pages"], 3)

    def test_page_blocks_traversal(self):
        self.build()
        self.assertIsNone(self.builder.page("../outside"))
        self.assertIsNone(self.builder.page("does-not-exist"))

    def test_custom_ai_diagram_is_detected(self):
        site = self.build()
        billing = site["pages"]["domains/billing"]
        self.assertTrue(billing["has_diagram"])
        self.assertEqual(billing["kind"], "domain")

    def test_project_card_reads_a_child_site(self):
        child_root = os.path.join(self.root, "api")
        child_wiki = os.path.join(child_root, ".codx", "wiki")
        os.makedirs(child_wiki, exist_ok=True)
        with open(os.path.join(child_wiki, "docs.json"), "w", encoding="utf-8") as handle:
            json.dump({
                "project": {"title": "Demo API", "description": "The API", "icon": ""},
                "pages": {"home": {"path": "home", "title": "Home"}},
                "generated_at": 123,
            }, handle)

        class ChildSettings:
            project_name = "api"
            project_id = "api-id"
            codx_path = os.path.join(child_root, ".codx")
            abs_project_path = child_root
            project_icon = ""
            project_wiki = True

            def get_project_wiki_path(self):
                return child_wiki

        card = self.builder._project_card(ChildSettings())
        self.assertEqual(card["title"], "Demo API")
        self.assertEqual(card["page_count"], 1)
        self.assertEqual(card["status"], "ready")
        self.assertTrue(card["wiki_url"].startswith("?project="))

    def test_profile_placeholders_are_rendered(self):
        class Profile:
            content = "# About {{ project_name }}\nProject's path is: '{{ project_path }}' / {{ projectpath }}\n"
            parsed_content = None

        text = profile_text(Profile(), self.settings)
        self.assertIn("demo", text)
        self.assertIn(self.root, text)
        self.assertNotIn("{{", text)
        self.assertEqual(
            render_profile_placeholders("{{ unknown }}", self.settings),
            "",
        )

    def test_first_paragraph_skips_html_and_comments(self):
        self.assertEqual(
            first_paragraph("<img src=\"x\" />\n// generated\n\nThe real summary is here."),
            "The real summary is here.",
        )

    def test_frontmatter_parser_is_defensive(self):
        frontmatter, body = parse_frontmatter("no frontmatter here")
        self.assertEqual(frontmatter, {})
        self.assertEqual(body, "no frontmatter here")
        frontmatter, body = parse_frontmatter("---\ntitle: X\n---\n# X\n")
        self.assertEqual(frontmatter["title"], "X")
        self.assertIn("# X", body)


if __name__ == "__main__":
    unittest.main()
