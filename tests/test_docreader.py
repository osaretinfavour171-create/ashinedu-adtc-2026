"""Tests for DocReader: JSON data integrity + live HTTP end-to-end.

Data integrity tests run offline. The HTTP tests require the DocReader
server to be running (start.sh or tests/start_docreader.sh), and are
skipped automatically otherwise.
"""

import json
import os
import subprocess
import sys
import unittest
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "app", "data")
DR_URL = "http://127.0.0.1:8765"


class TestDataIntegrity(unittest.TestCase):
    def test_interactions_json(self):
        with open(os.path.join(DATA, "interactions.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data["interactions"]), 100)
        for it in data["interactions"]:
            for key in ("drug_a", "drug_b", "severity", "mechanism", "recommendation"):
                self.assertIn(key, it, f"missing {key} in {it}")
            self.assertIn(it["severity"], ("low", "moderate", "high"))

    def test_condition_json_files(self):
        cond_dir = os.path.join(DATA, "stg_conditions")
        files = [f for f in os.listdir(cond_dir) if f.endswith(".json")]
        self.assertGreaterEqual(len(files), 200)
        for fname in files[:40]:
            with open(os.path.join(cond_dir, fname), encoding="utf-8") as f:
                c = json.load(f)
            self.assertTrue(c.get("condition_name"), fname)
            self.assertTrue(c.get("condition_slug"), fname)

    def test_glossary_and_phrases(self):
        with open(os.path.join(ROOT, "app", "pidgin", "pidgin_glossary.json"), encoding="utf-8") as f:
            g = json.load(f)
        self.assertGreaterEqual(len(g["medical_terms"]), 200)
        with open(os.path.join(ROOT, "app", "pidgin", "pidgin_phrases.json"), encoding="utf-8") as f:
            p = json.load(f)
        self.assertGreaterEqual(len(p["phrase_map"]), 300)


def _dr_available():
    try:
        req = urllib.request.urlopen(
            urllib.request.Request(f"{DR_URL}/health", method="GET"), timeout=2
        )
        return req.status == 200
    except Exception:
        return False


@unittest.skipUnless(_dr_available(), "DocReader server not running")
class TestDocReaderHTTP(unittest.TestCase):
    def test_health(self):
        with urllib.request.urlopen(f"{DR_URL}/health", timeout=5) as r:
            body = json.loads(r.read().decode())
        self.assertTrue(body["ok"])
        self.assertGreater(body["conditions"], 200)
        self.assertGreater(body["interactions"], 100)

    def _search(self, query):
        req = urllib.request.Request(
            f"{DR_URL}/search",
            data=json.dumps({"query": query}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())

    def test_condition_lookup(self):
        r = self._search("bronchial asthma treatment")
        names = [c["condition_name"] for c in r["conditions"]]
        self.assertIn("Bronchial Asthma", names)

    def test_interaction_lookup(self):
        r = self._search("metronidazole and warfarin")
        self.assertEqual(r["drug_match"], "Metronidazole")
        partners = {i["drug_b"] for i in r["interactions"]}
        self.assertIn("Warfarin", partners)

    def test_artemether_quinine(self):
        r = self._search("artemether lumefantrine and quinine")
        self.assertEqual(r["drug_match"], "Artemether/Lumefantrine")
        partners = {i["drug_b"] for i in r["interactions"]}
        self.assertIn("Quinine", partners)


if __name__ == "__main__":
    unittest.main()
