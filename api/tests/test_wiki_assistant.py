"""Tests for wiki assistant retrieval and graceful degradation."""

import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from codx.junior.wiki.assistant import WikiAssistant
from codx.junior.wiki.site import WikiSiteBuilder


class FakeSettings:
    def __init__(self, root):
        self.project_name = "demo"
        self.project_id = "demo-id"
        self.abs_project_path = root
        self.codx_path = os.path.join(root, ".codx")
        self.project_wiki = True
        self.project_icon = ""
        self.repo_url = ""
        self.project_wiki_path = None
        self.wiki_auto_update = True
        self.wiki_assistant_enabled = True
        self.wiki_model = ""
        self.rag_model = ""

    def get_project_wiki_path(self):
        return os.path.join(self.codx_path, "wiki")

    def get_project_dependencies(self):
        return []

    def get_sub_projects(self):
        return []

    def get_rag_model(self):
        return ""

    def get_wiki_model(self):
        return ""


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


class WikiAssistantTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.settings = FakeSettings(self.root)
        self.wiki = self.settings.get_project_wiki_path()
        write(
            os.path.join(self.wiki, "home.md"),
            "---\ntitle: Demo\ndescription: Demo docs\n---\n# Demo\n\nWelcome.\n",
        )
        write(
            os.path.join(self.wiki, "guides", "auth.md"),
            "---\ntitle: Authentication\ndescription: How login and tokens work\n"
            "tags: [auth, security]\n---\n# Authentication\n\n"
            "## Overview\n\nAuthentication uses signed tokens. " + ("word " * 200) + "\n",
        )
        write(
            os.path.join(self.wiki, "guides", "billing.md"),
            "---\ntitle: Billing\ndescription: Invoices and payments\n---\n# Billing\n\nBilling.\n",
        )
        with patch.object(WikiSiteBuilder, "_project_description", return_value="Demo."), \
                patch.object(WikiSiteBuilder, "_related_projects", return_value=([], None)):
            WikiSiteBuilder(settings=self.settings).build()

    def tearDown(self):
        self.tmp.cleanup()

    async def test_selects_relevant_page_and_cites_it(self):
        assistant = WikiAssistant(settings=self.settings)
        site = assistant.site_builder.load()
        pages = list(site["pages"].values())
        selected = assistant._select_pages("How does authentication work?", pages, None)
        self.assertEqual(selected[0]["path"], "guides/auth")

        assistant._ask_ai = AsyncMock(side_effect=RuntimeError("model offline"))
        with patch.object(assistant, "_search_knowledge", return_value=[]):
            result = await assistant.answer("How does authentication work?")
        self.assertEqual(result["mode"], "fallback")
        self.assertIn("Authentication", result["answer"])
        self.assertTrue(any(citation["path"] == "guides/auth" for citation in result["citations"]))
        self.assertTrue(result["suggestions"])

    async def test_current_page_is_used_as_a_hint(self):
        assistant = WikiAssistant(settings=self.settings)
        site = assistant.site_builder.load()
        pages = list(site["pages"].values())
        selected = assistant._select_pages("Tell me more", pages, "guides/billing")
        self.assertEqual(selected[0]["path"], "guides/billing")

    async def test_empty_question_is_rejected(self):
        assistant = WikiAssistant(settings=self.settings)
        with self.assertRaises(ValueError):
            await assistant.answer("   ")


if __name__ == "__main__":
    unittest.main()
