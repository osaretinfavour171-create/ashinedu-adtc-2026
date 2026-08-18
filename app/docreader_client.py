"""DocReader client: talks to the local Go DocReader server.

The DocReader holds the official drug-interaction matrix and the indexed
Nigerian Standard Treatment Guidelines (270 conditions). It runs locally,
so this client has zero network dependency beyond localhost.
"""

import json
import logging
import urllib.request

log = logging.getLogger("pidginpharma.docreader")

DEFAULT_DR_URL = "http://127.0.0.1:8765"


class DocReaderClient:
    def __init__(self, url: str = DEFAULT_DR_URL, timeout: float = 15.0):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def is_ready(self) -> bool:
        try:
            req = urllib.request.urlopen(
                urllib.request.Request(f"{self.url}/health", method="GET"),
                timeout=3,
            )
            return req.status == 200
        except Exception:
            return False

    def search(self, query: str) -> dict:
        payload = json.dumps({"query": query}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # ------------------------------------------------------------------
    def build_context(self, query: str) -> str:
        """Query DocReader and format a compact, factual context block."""
        if not self.is_ready():
            log.warning("DocReader not reachable - skipping local data context")
            return ""
        try:
            result = self.search(query)
        except Exception as exc:
            log.warning("DocReader search failed: %s", exc)
            return ""

        parts = []

        conditions = result.get("conditions") or []
        if conditions:
            cond_lines = []
            for c in conditions[:3]:
                name = c.get("condition_name", "")
                intro = c.get("introduction", "")
                cond_lines.append(f"- {name}: {intro[:300]}")
                treat = c.get("treatment") or {}
                drugs = treat.get("drug") or []
                if drugs:
                    cond_lines.append(f"  Treatment (NSTG): {'; '.join(drugs[:3])}")
                if treat.get("goals"):
                    cond_lines.append(f"  Goals: {'; '.join(treat['goals'][:3])}")
            parts.append("CONDITIONS (from Nigeria Standard Treatment Guidelines 2022):\n"
                         + "\n".join(cond_lines))

        interactions = result.get("interactions") or []
        drug = result.get("drug_match")
        if drug and interactions:
            int_lines = [f"INTERACTIONS for {drug} (from local interaction database):"]
            for it in interactions[:5]:
                sev = it.get("severity", "unknown")
                int_lines.append(
                    f"- {it.get('drug_a')} + {it.get('drug_b')} "
                    f"[{sev.upper()}]: {it.get('mechanism', '')} "
                    f"Recommendation: {it.get('recommendation', '')}"
                )
            parts.append("\n".join(int_lines))

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    def format_interaction_answer(self, result: dict) -> str:
        """Human-readable English answer when the query is about interactions."""
        drug = result.get("drug_match")
        interactions = result.get("interactions") or []
        if not drug or not interactions:
            return ""
        lines = [f"Drug interaction check for {drug}:"]
        for it in interactions:
            sev = it.get("severity", "unknown")
            lines.append(
                f"- With {it.get('drug_b') if it.get('drug_a') == drug else it.get('drug_a')} "
                f"({sev.upper()}): {it.get('mechanism', '')} "
                f"{it.get('recommendation', '')}"
            )
        return "\n".join(lines)
