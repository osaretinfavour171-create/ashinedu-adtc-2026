"""Tests for the orchestrator wiring (language layer + DocReader client)."""

import os
import sys
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from orchestrator import Orchestrator

DR_URL = "http://127.0.0.1:8765"


def _dr_available():
    try:
        req = urllib.request.urlopen(
            urllib.request.Request(f"{DR_URL}/health", method="GET"), timeout=2
        )
        return req.status == 200
    except Exception:
        return False


class TestOrchestrator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # No model in unit tests: use_model=False keeps tests fast/offline.
        cls.orch = Orchestrator(use_model=False, use_docreader=True)

    def test_status_runs(self):
        out = self.orch.status()
        self.assertIn("Language", out)

    def test_english_mode(self):
        answer, source = self.orch.answer("my pikin get hot body and dey vomit")
        self.assertIsInstance(answer, str)
        self.assertGreater(len(answer), 20)
        self.assertIn(source, ("cache", "docreader", "llm", "fallback"))

    @unittest.skipUnless(_dr_available(), "DocReader server not running")
    def test_drug_interaction_answer(self):
        answer, source = self.orch.answer("metronidazole plus warfarin e dey safe?")
        self.assertIn("Metronidazole", answer)
        self.assertIn("Warfarin", answer)

    def test_cache_works(self):
        """Same query twice should hit cache the second time."""
        q = "what is the treatment for malaria"
        answer1, source1 = self.orch.answer(q)
        answer2, source2 = self.orch.answer(q)
        self.assertEqual(answer1, answer2)
        self.assertEqual(source2, "cache")

    def test_source_is_valid(self):
        """Source should always be one of the known values."""
        _, source = self.orch.answer("diarrhoea treatment")
        self.assertIn(source, ("cache", "docreader", "llm", "fallback"))


if __name__ == "__main__":
    unittest.main()
