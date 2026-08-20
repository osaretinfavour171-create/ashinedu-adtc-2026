"""Query metrics tracker for PidginPharma.

Tracks response times, query counts, error rates, and popular queries.
Data is saved to a local JSON file on exit and can be viewed via the
`stats` command in the REPL.

Design principles:
  - Zero external dependencies (stdlib only).
  - Thread-safe writes.
  - Persistent across sessions (saved to tools/metrics.json).
  - Lightweight: only stores aggregates, not individual queries.
"""

import json
import os
import threading
import time
from collections import Counter
from datetime import datetime

_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
_METRICS_FILE = os.path.join(_TOOLS_DIR, "metrics.json")


class Metrics:
    """Track query metrics across a PidginPharma session."""

    def __init__(self, persist_path: str = _METRICS_FILE):
        self._path = persist_path
        self._lock = threading.Lock()
        self._session_start = time.time()
        self._total_queries = 0
        self._total_errors = 0
        self._response_times: list[float] = []
        self._source_counts = Counter()  # "docreader" | "llm" | "cache" | "fallback"
        self._popular_queries = Counter()
        self._load()

    def _load(self) -> None:
        """Load previous session metrics if they exist."""
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._total_queries = data.get("total_queries", 0)
                self._total_errors = data.get("total_errors", 0)
                self._response_times = data.get("response_times", [])[-1000:]
                self._source_counts = Counter(data.get("source_counts", {}))
                self._popular_queries = Counter(data.get("popular_queries", {}))
            except (json.JSONDecodeError, OSError):
                pass  # Corrupted file — start fresh

    def record_query(self, query: str, response_time: float,
                     source: str, success: bool = True) -> None:
        """Record a completed query.

        Args:
            query: The normalized query text.
            response_time: Seconds taken to generate the answer.
            source: Where the answer came from ("docreader", "llm", "cache", "fallback").
            success: Whether the query completed without error.
        """
        # Truncate query for storage (keep first 80 chars)
        short_query = query[:80].strip()
        with self._lock:
            self._total_queries += 1
            if not success:
                self._total_errors += 1
            self._response_times.append(round(response_time, 3))
            # Keep only last 1000 response times
            if len(self._response_times) > 1000:
                self._response_times = self._response_times[-1000:]
            self._source_counts[source] += 1
            if short_query:
                self._popular_queries[short_query] += 1

    def save(self) -> None:
        """Persist metrics to disk."""
        with self._lock:
            data = {
                "total_queries": self._total_queries,
                "total_errors": self._total_errors,
                "response_times": self._response_times,
                "source_counts": dict(self._source_counts),
                "popular_queries": dict(self._popular_queries.most_common(50)),
                "last_updated": datetime.now().isoformat(),
            }
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def summary(self) -> str:
        """Return a human-readable summary of metrics."""
        with self._lock:
            total = self._total_queries
            errors = self._total_errors
            rt = self._response_times

        if total == 0:
            return "No queries recorded yet this session."

        avg_time = sum(rt) / len(rt) if rt else 0
        p95_time = sorted(rt)[int(len(rt) * 0.95)] if len(rt) > 1 else avg_time
        fastest = min(rt) if rt else 0
        slowest = max(rt) if rt else 0

        lines = [
            "=== PidginPharma Session Stats ===",
            f"Total queries:  {total}",
            f"Errors:         {errors}",
            f"Avg response:   {avg_time:.1f}s",
            f"Fastest:        {fastest:.1f}s",
            f"Slowest:        {slowest:.1f}s",
            f"P95 response:   {p95_time:.1f}s",
            "",
            "Answer sources:",
        ]
        for src, count in self._source_counts.most_common():
            pct = count / total * 100
            lines.append(f"  {src:12s}: {count:4d} ({pct:.0f}%)")

        top = self._popular_queries.most_common(5)
        if top:
            lines.append("")
            lines.append("Most asked questions:")
            for q, c in top:
                lines.append(f"  [{c}x] {q}")

        return "\n".join(lines)
