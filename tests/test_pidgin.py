"""Unit tests for the Pidgin language layer (normalizer + reformulator)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from pidgin.normalizer import PidginNormalizer
from pidgin.reformulator import PidginReformulator


class TestNormalizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = PidginNormalizer()

    def test_fever_vomit(self):
        self.assertEqual(
            self.n.normalize("my pikin get hot body and dey vomit"),
            "the child has fever and vomiting",
        )

    def test_run_stomach(self):
        self.assertEqual(
            self.n.normalize("di patient dey run stomach since yesterday"),
            "di patient diarrhea since yesterday",
        )

    def test_headache(self):
        self.assertEqual(
            self.n.normalize("head dey pain and body dey hot"),
            "headache and fever",
        )

    def test_pidgin_detection(self):
        self.assertTrue(self.n.has_pidgin("my pikin get hot body"))
        self.assertFalse(self.n.has_pidgin("treatment for acute diarrhoea"))

    def test_english_passthrough(self):
        self.assertEqual(
            self.n.normalize("treatment for acute diarrhoea"),
            "treatment for acute diarrhoea",
        )

    def test_empty(self):
        self.assertEqual(self.n.normalize("   "), "")


class TestReformulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = PidginReformulator()

    def test_keeps_drug_names(self):
        out = self.r.reformulate(
            "Take Artemether/Lumefantrine twice daily for 3 days."
        )
        self.assertIn("Artemether/Lumefantrine", out)
        self.assertIn("twice daily", out)

    def test_rewrites_connectives(self):
        out = self.r.reformulate("Additionally, monitor the patient.")
        self.assertIn("also", out.lower())
        self.assertIn("di patient", out)

    def test_advice_signoff(self):
        out = self.r.reformulate(
            "Give the child oral rehydration solution. Monitor fluid intake."
        )
        self.assertIn("Abeg take note well", out)

    def test_no_clinical_term_corruption(self):
        # "fever" must not become "hot body" inside official data text
        out = self.r.reformulate(
            "Fever is elevation of body temperature. Acute diarrhoea needs ORT."
        )
        self.assertIn("Fever", out)
        self.assertIn("Acute diarrhoea", out)


if __name__ == "__main__":
    unittest.main()
