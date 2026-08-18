"""Output reformulator: turns a formal English answer into Pidgin-flavoured text.

Strategy (keeps clinical accuracy, adds warmth):
  1. Shorten formal connectives ("Additionally" -> "Also", ...).
  2. Rewrite key clinical phrases into plain-Pidgin equivalents from a
     hand-built map (e.g. "is contraindicated" -> "no go use am together").
  3. Wrap key recommendations with Pidgin emphasis ("Make sure say...",
     "Abeg note am well...").
  4. Keep drug names, doses, and numbers untouched.
"""

import re

from .glossary import norm

_PIDGIN_PHRASES = {
    "is contraindicated": "no go use am together",
    "contraindicated": "no go use am",
    "should not be used": "no go use am",
    "should not be taken": "no go take am",
    "should be avoided": "make you avoid am",
    "avoid": "make you no use",
    "monitor": "dey check",
    "monitoring": "dey check",
    "watch for": "dey look for",
    "the patient": "di patient",
    "the child": "di pikin",
    "the baby": "di pikin",
    "your child": "your pikin",
    "the mother": "di mama",
    "breastfeeding": "dey breastfeed",
    "liver": "liver",
    "kidney": "kidney",
    "heart": "heart",
    "blood pressure": "blood pressure",
    "please note": "abeg note am well",
    "note": "note am",
    "important": "e dey very important",
    "make sure": "make sure say",
    "always": "always",
    "never": "never ever",
    "immediately": "right away",
    "seek medical attention": "go see doctor quick quick",
    "see a doctor": "go see doctor",
    "consult a health worker": "go ask di health worker",
    "stop taking": "stop to take",
    "reduce the dose": "make di dose small small",
    "increase fluid intake": "drink plenty water",
    "drink plenty of water": "drink plenty water",
    "side effects": "side effect",
    "adverse effects": "bad side effect",
    "overdose": "overdose",
    "do not give": "no go give am",
    "do not take": "no go take am",
    "may cause": "fit cause",
    "can cause": "fit cause",
    "may increase": "fit increase",
    "may decrease": "fit reduce",
    "may lead to": "fit lead to",
    "can lead to": "fit lead to",
    "is used to treat": "dey use am to treat",
    "used to treat": "dey use am for",
    "take with food": "take am with food",
    "take on an empty stomach": "take am before food",
    "take once daily": "take am once every day",
    "take twice daily": "take am two times every day",
    "take three times daily": "take am three times every day",
    "per day": "every day",
    "for 7 days": "for 7 days",
    "for 5 days": "for 5 days",
    "for 3 days": "for 3 days",
    "for 14 days": "for 14 days",
    "at bedtime": "before im go sleep",
    "every 8 hours": "every 8 hours",
    "every 6 hours": "every 6 hours",
    "every 12 hours": "every 12 hours",
    "by mouth": "by mouth",
    "intravenously": "through drip",
    "intramuscular": "with injection for muscle",
    "refer to hospital": "send am go hospital",
    "referral": "make dem refer am go hospital",
    "emergency": "emergency",
    "danger sign": "danger sign",
    "danger signs": "danger signs",
    "red flag": "danger sign",
}

# Sentence-openers to soften.
_OPENERS = {
    "additionally": "also",
    "furthermore": "also",
    "moreover": "also",
    "however": "but",
    "therefore": "so",
    "thus": "so",
    "consequently": "so",
    "in addition": "also",
    "nevertheless": "but still",
    "nonetheless": "but still",
    "in conclusion": "to finish",
    "finally": "last last",
    "first": "first",
    "second": "second",
    "third": "third",
}


class PidginReformulator:
    """Reformulate formal English clinical text into Pidgin-flavoured text."""

    def __init__(self, glossary_path=None):
        from .glossary import load_glossary

        self.glossary = load_glossary(glossary_path) if glossary_path else load_glossary()
        # Build english -> first pidgin variant map for common terms so we can
        # re-inject pidgin variants in answers.
        self._term_variants = {
            eng: variants[0]
            for eng, variants in self.glossary.get("medical_terms", {}).items()
            if variants
        }
        # Phrases sorted longest-first.
        self._phrases_sorted = sorted(_PIDGIN_PHRASES.keys(), key=len, reverse=True)

    # ------------------------------------------------------------------
    def reformulate(self, text: str) -> str:
        """Return a Pidgin-flavoured version of *text*."""
        if not text:
            return text
        out = text
        # 1. Phrase rewrites (case-insensitive).
        for phrase in self._phrases_sorted:
            out = re.sub(
                re.escape(phrase), _PIDGIN_PHRASES[phrase], out, flags=re.IGNORECASE
            )
        # 2. Sentence openers at start or after punctuation.
        for opener, repl in _OPENERS.items():
            out = re.sub(
                r"(^|[.;!?]\s+)" + re.escape(opener) + r"\b",
                lambda m: m.group(1) + repl,
                out,
                flags=re.IGNORECASE,
            )
        # 3. Inject a Pidgin sign-off for advice-type content.
        if self._looks_like_advice(text):
            out = out.rstrip() + (
                "\n\nAbeg take note well: dis advice na from di official "
                "Nigeria treatment guideline. If di patient dey worse, "
                "make you send am go hospital quick quick."
            )
        return out

    # ------------------------------------------------------------------
    def _looks_like_advice(self, text: str) -> bool:
        lowered = text.lower()
        markers = (
            "take", "give", "dose", "mg", "ml", "monitor", "avoid",
            "watch", "should", "must", "do not", "recommend", "interaction",
        )
        return any(m in lowered for m in markers)

    # ------------------------------------------------------------------
    def pidginize_terms(self, text: str) -> str:
        """Replace common English symptom words with Pidgin variants (light touch)."""
        out = text
        for eng, variant in self._term_variants.items():
            out = re.sub(
                r"\b" + re.escape(eng) + r"\b", variant, out, flags=re.IGNORECASE
            )
        return out
