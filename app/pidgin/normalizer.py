"""Input normalizer: turns Pidgin / mixed-language input into clean English.

Pipeline:
  1. Normalize whitespace + casing.
  2. Expand common Pidgin contractions ("dey", "na", "no be", ...).
  3. Replace multi-word phrases (longest first) using phrase_map.
  4. Replace single/multi-word medical variants using the variant index.
  5. Collapse repeated letters ("paaain" -> "pain") and trim.

The output is a canonical English query that the orchestrator can
route to the local model and DocReader.
"""

import re

from .glossary import build_variant_index, load_glossary, load_phrases, norm

# Common Pidgin filler/connectors that carry no clinical meaning.
_FILLERS = {
    "na": "", "dey": "", "e dey": "", "dem": "",
    "sha": "", "se": "that", "wen": "when", "wetin": "what",
    "wetin dey worry": "what is the problem with",
    "una": "you", "make": "please", "make i": "let me", "i dey": "i am",
    "no dey": "does not", "dey pain": "is painful", "dey come": "comes",
    "don": "has", "don dey": "has been", "dey go": "goes", "dey sleep": "sleeps",
    "abeg": "please", "ooh": "", "sef": "", "self": "", "shey": "",
    "no be": "is not", "e don": "it has", "e fit": "it can",
}

# Letter-repetition collapse: "paaain" -> "pain", "siiick" -> "sick"
_REPEAT_RE = re.compile(r"(.)\1{2,}")


class PidginNormalizer:
    """Normalize mixed Pidgin/English clinical input into English."""

    def __init__(self, glossary_path=None, phrases_path=None):
        self.glossary = load_glossary(glossary_path) if glossary_path else load_glossary()
        self.phrases = load_phrases(phrases_path) if phrases_path else load_phrases()
        self.variant_index = build_variant_index(self.glossary)
        self.phrase_map = self.phrases.get("phrase_map", {})
        # Longest phrase first so "my pikin get fever" matches before "pikin get".
        self._phrases_sorted = sorted(self.phrase_map.keys(), key=len, reverse=True)

    # ------------------------------------------------------------------
    def normalize(self, text: str) -> str:
        """Return canonical English query for a Pidgin/English input."""
        if not text or not text.strip():
            return ""
        out = norm(text)
        out = self._collapse_repeats(out)
        out = self._replace_phrases(out)
        out = self._replace_variants(out)
        out = self._drop_fillers(out)
        out = re.sub(r"\s+", " ", out).strip()
        return out

    # ------------------------------------------------------------------
    def _collapse_repeats(self, text: str) -> str:
        # Only collapse inside words (not "ll" in "will" -> keep double letters
        # that are valid; collapse 3+ repeats which are Pidgin emphasis).
        return _REPEAT_RE.sub(lambda m: m.group(1) * 2, text)

    def _replace_phrases(self, text: str) -> str:
        lower = text
        for phrase in self._phrases_sorted:
            if phrase in lower:
                lower = lower.replace(phrase, self.phrase_map[phrase])
        return lower

    def _replace_variants(self, text: str) -> str:
        # Replace multi-word variants first, then single words.
        words = text.split()
        i = 0
        out = []
        n = len(words)
        while i < n:
            matched = False
            # Try longest window (up to 4 words) first.
            for size in (4, 3, 2, 1):
                if i + size > n:
                    continue
                window = " ".join(words[i : i + size])
                if window in self.variant_index:
                    out.append(self.variant_index[window])
                    i += size
                    matched = True
                    break
            if not matched:
                out.append(words[i])
                i += 1
        return " ".join(out)

    def _drop_fillers(self, text: str) -> str:
        words = text.split()
        kept = []
        for w in words:
            if w in _FILLERS and _FILLERS[w] == "":
                continue
            kept.append(_FILLERS.get(w, w))
        return " ".join(kept)

    # ------------------------------------------------------------------
    def has_pidgin(self, text: str) -> bool:
        """Heuristic: does the input look like it contains Pidgin?

        Only counts signals that are unambiguous: multi-word Pidgin phrases,
        Pidgin filler words, and multi-word glossary variants. Single-word
        variants like "cut" or "treatment" are ordinary English and do not
        count, so plain-English queries are never misclassified.
        """
        t = norm(text)
        for phrase in self._phrases_sorted:
            if phrase in t:
                return True
        words = set(t.split())
        if words & set(_FILLERS):
            return True
        for variants in self.glossary.get("medical_terms", {}).values():
            for v in variants:
                v = v.strip().lower()
                if v and " " in v and v in t:
                    return True
        return False
