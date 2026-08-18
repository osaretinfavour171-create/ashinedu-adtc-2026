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
        self.assertIn("Language layer", out)

    def test_english_mode(self):
        out = self.orch.answer("my pikin get hot body and dey vomit")
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 20)

    @unittest.skipUnless(_dr_available(), "DocReader server not running")
    def test_drug_interaction_answer(self):
        out = self.orch.answer("metronidazole plus warfarin e dey safe?")
        self.assertIn("Metronidazole", out)
        self.assertIn("Warfarin", out)


if __name__ == "__main__":
    unittest.main()
