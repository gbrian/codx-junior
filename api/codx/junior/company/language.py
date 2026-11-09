"""
Small, dependency-free language detection for the company assistant.

The rule-based assistant speaks English; when it falls back to AI reasoning the
model must answer in the manager's own language. This module detects the
language from the message (script + common function words) and resolves it
against, in order:

1. an explicit user preference (``CodxUser.language``),
2. the language the manager is writing right now,
3. the browser/request language,
4. English.

It is intentionally simple and fast: no model download, no network, no extra
dependency. Known languages: English, Spanish, Portuguese, French, German,
Italian, Catalan, Dutch, Russian, Ukrainian, Arabic, Hebrew, Hindi, Chinese,
Japanese, Korean, Turkish, Polish, Swedish and Greek.
"""

from __future__ import annotations

import re

from typing import Dict, Optional

#: code -> display name (the name is what we send to the LLM).
LANGUAGES: Dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ca": "Catalan",
    "nl": "Dutch",
    "ru": "Russian",
    "uk": "Ukrainian",
    "ar": "Arabic",
    "he": "Hebrew",
    "hi": "Hindi",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "tr": "Turkish",
    "pl": "Polish",
    "sv": "Swedish",
    "el": "Greek",
}

#: Common function words used to score Latin-script languages.
_STOPWORDS: Dict[str, tuple] = {
    "en": ("the", "and", "you", "your", "need", "want", "team", "project", "please", "with", "for", "what"),
    "es": ("el", "la", "los", "las", "y", "de", "que", "necesito", "quiero", "equipo", "proyecto", "por", "favor", "gracias", "con", "para", "crear", "añadir", "agregar"),
    "pt": ("o", "a", "os", "as", "e", "de", "que", "preciso", "quero", "equipe", "projeto", "por", "favor", "obrigado", "com", "para", "criar", "adicionar"),
    "fr": ("le", "la", "les", "et", "de", "que", "besoin", "veux", "équipe", "projet", "s'il", "vous", "plaît", "merci", "avec", "pour", "créer", "ajouter"),
    "de": ("der", "die", "das", "und", "ich", "brauche", "möchte", "team", "projekt", "bitte", "danke", "mit", "für", "erstellen", "hinzufügen"),
    "it": ("il", "la", "gli", "e", "di", "che", "ho", "bisogno", "voglio", "squadra", "progetto", "per", "favore", "grazie", "con", "creare", "aggiungere"),
    "ca": ("el", "la", "els", "i", "de", "que", "necessito", "vull", "equip", "projecte", "si", "us", "plau", "gràcies", "amb", "per", "crear", "afegir"),
    "nl": ("de", "het", "en", "ik", "nodig", "wil", "team", "project", "alsjeblieft", "bedankt", "met", "voor", "maken", "toevoegen"),
    "tr": ("ve", "bir", "için", "istiyorum", "ihtiyacım", "ekip", "proje", "lütfen", "teşekkür", "ile", "oluştur", "ekle"),
    "pl": ("i", "w", "na", "nie", "potrzebuję", "chcę", "zespół", "projekt", "proszę", "dziękuję", "z", "utwórz", "dodaj"),
    "sv": ("och", "jag", "behöver", "vill", "team", "projekt", "snälla", "tack", "med", "för", "skapa", "lägg"),
}

#: Script ranges that identify a language directly.
_SCRIPT_RANGES = (
    ("ru", re.compile(r"[\u0400-\u04FF]")),          # Cyrillic; refined below
    ("ar", re.compile(r"[\u0600-\u06FF]")),
    ("he", re.compile(r"[\u0590-\u05FF]")),
    ("hi", re.compile(r"[\u0900-\u097F]")),
    ("el", re.compile(r"[\u0370-\u03FF]")),
    ("zh", re.compile(r"[\u4E00-\u9FFF]")),
    ("ja", re.compile(r"[\u3040-\u30FF]")),
    ("ko", re.compile(r"[\uAC00-\uD7AF]")),
)

_UKRAINIAN_HINTS = re.compile(r"[іїєґ]", re.I)


def normalize_language(value: Optional[str]) -> str:
    """
    Normalize a language tag/name into a supported code.

    Accepts ``es``, ``es-ES``, ``ES`` and ``spanish``. Unknown values return
    ``""`` so callers can ignore them.
    """
    if not value:
        return ""
    text = str(value).strip().lower().replace("_", "-")
    if not text or text == "auto":
        return ""
    code = text.split("-")[0]
    if code in LANGUAGES:
        return code
    for candidate, name in LANGUAGES.items():
        if text == name.lower():
            return candidate
    return ""


def language_name(code: str) -> str:
    """Return the readable name of a language code (English fallback)."""
    code = normalize_language(code) or "en"
    return LANGUAGES.get(code, "English")


def detect_language(text: str) -> str:
    """
    Return the most likely language code for *text*.

    The detection is conservative: when it cannot tell, it returns ``"en"`` so
    an English message is never accidentally answered in another language.
    """
    value = str(text or "")
    if not value.strip():
        return "en"

    # Non-Latin scripts are unambiguous enough.
    if _UKRAINIAN_HINTS.search(value):
        return "uk"
    for code, pattern in _SCRIPT_RANGES:
        if pattern.search(value):
            if code == "ru" and re.search(r"[іїєґІЇЄҐ]", value):
                return "uk"
            if code == "zh" and re.search(r"[\u3040-\u30FF]", value):
                return "ja"
            return code

    lowered = value.lower()
    words = set(re.findall(r"[a-zà-ÿäöüßçñáéíóúâêôãõ]+", lowered))
    scores = {
        code: sum(1 for word in vocabulary if word in words)
        for code, vocabulary in _STOPWORDS.items()
    }
    best_code, best_score = max(scores.items(), key=lambda item: item[1])
    # A single accidental match is not enough to switch language.
    if best_score < 2:
        return "en"
    return best_code


def resolve_language(
    user_language: Optional[str] = None,
    text: str = "",
    fallback_language: Optional[str] = None,
) -> str:
    """
    Resolve the language to answer in.

    Args:
        user_language: Explicit user preference ("auto" is ignored).
        text: The manager's current message.
        fallback_language: Browser/request language.

    Returns:
        A supported language code.
    """
    explicit = normalize_language(user_language)
    if explicit:
        return explicit
    detected = detect_language(text)
    if detected != "en":
        return detected
    browser = normalize_language(fallback_language)
    return browser or "en"


# Made with ❤️ by codx-junior
