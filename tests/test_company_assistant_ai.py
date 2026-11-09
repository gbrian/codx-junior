"""
Tests for the company assistant's AI-reasoning fallback, language handling and
user personalisation.

The real SmolAgent is never invoked: the assistant accepts an injected reasoner
and the tests assert what it receives (user, language, history, context).

Run with either::

    pytest tests/test_company_assistant_ai.py -q
    python -m unittest discover -s tests -p 'test_company_assistant_ai.py' -v
"""

import shutil
import tempfile
import unittest

from types import SimpleNamespace

from codx.junior.company.assistant import CompanyAssistant
from codx.junior.company.language import (
    detect_language,
    language_name,
    normalize_language,
    resolve_language,
)
from codx.junior.company.manager import CompanyManager
from codx.junior.model.user import CodxUser


class LanguageTestCase(unittest.TestCase):
    def test_detects_common_languages(self):
        cases = {
            "I need a developer for the new project": "en",
            "Hola, necesito un equipo de desarrollo por favor": "es",
            "Olá, preciso de uma equipe de projeto por favor": "pt",
            "Bonjour, j'ai besoin d'une équipe pour le projet s'il vous plaît": "fr",
            "Hallo, ich brauche ein Team für das Projekt bitte": "de",
            "Ciao, ho bisogno di una squadra per il progetto per favore": "it",
            "Привет, мне нужна команда для проекта": "ru",
            "你好，我需要一个开发团队": "zh",
            "こんにちは、開発チームが必要です": "ja",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(detect_language(text), expected)

    def test_normalizes_tags_and_names(self):
        self.assertEqual(normalize_language("es-ES"), "es")
        self.assertEqual(normalize_language("PT_br"), "pt")
        self.assertEqual(normalize_language("Spanish"), "es")
        self.assertEqual(normalize_language("auto"), "")
        self.assertEqual(language_name("fr"), "French")

    def test_resolution_priority(self):
        # Explicit user preference wins.
        self.assertEqual(resolve_language("de", "hola necesito equipo", "es"), "de")
        # Otherwise the message language wins over the browser.
        self.assertEqual(resolve_language("auto", "hola necesito equipo", "de"), "es")
        # Browser is used for an English/ambiguous message.
        self.assertEqual(resolve_language("auto", "hello", "pt-BR"), "pt")
        self.assertEqual(resolve_language("", "hello", ""), "en")


class AssistantAIFallbackTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="company-ai-")
        self.manager = CompanyManager(
            root_path=self.root,
            projects_provider=lambda: [],
            users_provider=lambda: [],
            profiles_provider=lambda project_ids=None: [],
        )
        self.company = self.manager.create_company(
            {"name": "Acme", "owner": "alice", "mission": "Help customers"},
            actor="alice",
        )
        self.user = CodxUser(
            username="alice",
            email="alice@example.com",
            role="manager",
            language="auto",
            companies=[{"company_id": self.company.id, "role": "admin"}],
        )
        self.calls = []

        def reasoner(**kwargs):
            self.calls.append(kwargs)
            return {"reply": "Respuesta personalizada, Alice."}

        self.assistant = CompanyAssistant(
            self.manager,
            security=SimpleNamespace(),
            ai_reasoner=reasoner,
        )

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def ask(self, message, **kwargs):
        return self.assistant.respond(
            company=self.manager.get_company(self.company.id),
            message=message,
            actor="alice",
            can_manage=True,
            can_admin=True,
            user=self.user,
            **kwargs,
        )

    def test_unknown_message_uses_ai_reasoning_with_user_and_language(self):
        response = self.ask("Hola, necesito algo que no entiendes, por favor")
        self.assertTrue(response.get("ai_fallback"))
        self.assertEqual(response["language"], "es")
        self.assertIn("Alice", response["reply"])
        self.assertEqual(len(self.calls), 1)
        call = self.calls[0]
        self.assertIs(call["user"], self.user)
        self.assertEqual(call["language"], "es")
        self.assertIn("company", call)

    def test_known_action_does_not_use_ai(self):
        response = self.ask("show teams")
        self.assertFalse(response.get("ai_fallback"))
        self.assertEqual(self.calls, [])
        self.assertIn("team", response["reply"].lower())

    def test_fallback_reply_is_used_when_ai_returns_nothing(self):
        assistant = CompanyAssistant(
            self.manager,
            security=SimpleNamespace(),
            ai_reasoner=lambda **kwargs: None,
        )
        response = assistant.respond(
            company=self.manager.get_company(self.company.id),
            message="quux frobnicate wibble",
            actor="alice",
            can_manage=True,
            can_admin=True,
            user=self.user,
        )
        self.assertFalse(response.get("ai_fallback"))
        self.assertIn("codx-junior", response["reply"])

    def test_system_prompt_contains_user_info_and_language(self):
        prompt = self.assistant._ai_system_prompt(
            self.manager.get_company(self.company.id),
            self.user,
            "es",
            "home",
            [{"role": "user", "content": "hola"}],
        )
        self.assertIn("Alice", prompt)
        self.assertIn("alice@example.com", prompt)
        self.assertIn("Spanish", prompt)
        self.assertIn("Acme", prompt)
        self.assertIn("Help customers", prompt)


if __name__ == "__main__":
    unittest.main()
