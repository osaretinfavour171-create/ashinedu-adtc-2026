"""Glossary loader for the Pidgin layer.

Loads pidgin_glossary.json (English term -> Pidgin variants) and
pidgin_phrases.json (Pidgin phrase -> English) from disk, with caching.
"""

import json
import os
import re
from functools import lru_cache

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GLOSSARY = os.path.join(_HERE, "pidgin_glossary.json")
DEFAULT_PHRASES = os.path.join(_HERE, "pidgin_phrases.json")


@lru_cache(maxsize=8)
def load_glossary(path: str = DEFAULT_GLOSSARY) -> dict:
    """Return {medical_terms: {english: [pidgin variants]}, ...}."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=8)
def load_phrases(path: str = DEFAULT_PHRASES) -> dict:
    """Return {phrase_map: {pidgin_phrase_lower: english}}."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build_variant_index(glossary: dict) -> dict:
    """Map every Pidgin variant (lowercased) -> canonical English term."""
    index = {}
    for english, variants in glossary.get("medical_terms", {}).items():
        for v in variants:
            index[v.strip().lower()] = english
    return index


def norm(text: str) -> str:
    """Lowercase and collapse whitespace, keep apostrophes."""
    return re.sub(r"\s+", " ", text.strip().lower())
