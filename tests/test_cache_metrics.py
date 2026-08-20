"""Unit tests for the LRU cache and metrics tracker."""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from cache import ResponseCache
from metrics import Metrics


class TestResponseCache(unittest.TestCase):
    def test_basic_put_get(self):
        c = ResponseCache(max_size=10, ttl_seconds=60)
        c.put("fever treatment", "pidgin", "Paracetamol for fever")
        result = c.get("fever treatment", "pidgin")
        self.assertEqual(result, "Paracetamol for fever")

    def test_miss_returns_none(self):
        c = ResponseCache()
        self.assertIsNone(c.get("nonexistent query", "pidgin"))

    def test_eviction(self):
        c = ResponseCache(max_size=2)
        c.put("q1", "pidgin", "a1")
        c.put("q2", "pidgin", "a2")
        c.put("q3", "pidgin", "a3")  # should evict q1
        self.assertIsNone(c.get("q1", "pidgin"))
        self.assertEqual(c.get("q2", "pidgin"), "a2")
        self.assertEqual(c.get("q3", "pidgin"), "a3")

    def test_ttl_expiry(self):
        c = ResponseCache(ttl_seconds=0.1)
        c.put("quick query", "pidgin", "answer")
        time.sleep(0.2)
        self.assertIsNone(c.get("quick query", "pidgin"))

    def test_stats(self):
        c = ResponseCache()
        c.put("q1", "pidgin", "a1")
        c.get("q1", "pidgin")  # hit
        c.get("q2", "pidgin")  # miss
        stats = c.stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)

    def test_clear(self):
        c = ResponseCache()
        c.put("q1", "pidgin", "a1")
        c.clear()
        self.assertIsNone(c.get("q1", "pidgin"))
        self.assertEqual(c.stats()["size"], 0)

    def test_lang_separation(self):
        """Same query in different languages should be separate cache entries."""
        c = ResponseCache()
        c.put("fever", "pidgin", "hot body")
        c.put("fever", "en", "fever")
        self.assertEqual(c.get("fever", "pidgin"), "hot body")
        self.assertEqual(c.get("fever", "en"), "fever")


class TestMetrics(unittest.TestCase):
    def test_record_query(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            m = Metrics(persist_path=path)
            m.record_query("fever treatment", 1.5, "llm", success=True)
            m.record_query("drug interaction", 0.1, "cache", success=True)
            summary = m.summary()
            self.assertIn("Total queries:  2", summary)
            self.assertIn("llm", summary)
            self.assertIn("cache", summary)
        finally:
            os.unlink(path)

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            m1 = Metrics(persist_path=path)
            m1.record_query("test query", 2.0, "docreader", success=True)
            m1.save()
            # Load from same file
            m2 = Metrics(persist_path=path)
            self.assertEqual(m2._total_queries, 1)
        finally:
            os.unlink(path)

    def test_error_tracking(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            m = Metrics(persist_path=path)
            m.record_query("bad query", 0.0, "fallback", success=False)
            self.assertEqual(m._total_errors, 1)
        finally:
            os.unlink(path)

    def test_summary_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            m = Metrics(persist_path=path)
            self.assertIn("No queries", m.summary())
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
