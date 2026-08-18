"""Optional PinchTab layer: browser-based retrieval over pre-converted HTML.

PinchTab drives a local headless Chrome and exposes the accessibility tree
via an HTTP API / CLI. This client navigates to the local HTML versions of
the Nigeria EML and STG condition index (served on 127.0.0.1 by a tiny
static server) and extracts a token-efficient snapshot for the given query.

Design notes:
  * OPTIONAL - DocReader (JSON lookups) remains the default retrieval path.
    PinchTab adds semantic browsing over the converted HTML when the machine
    has RAM headroom (Chrome ~300-800 MB extra).
  * On Windows, PinchTab text extraction is best-effort; the accessibility
    snapshot endpoint is reliable, so we prefer snapshots and fall back to
    text when available.
  * All calls go through the PinchTab CLI (which handles auth/config), never
    the public internet.
"""

import logging
import os
import re
import shutil
import subprocess
import time

log = logging.getLogger("pidginpharma.pinchtab")

DEFAULT_HTML_BASE = "http://127.0.0.1:8766"
STG_PAGE = "STG_conditions.html"
EML_PAGE = "EML_2020.html"

# Smallest page that counts as "rendered" - avoids racing Chrome startup.
_RENDER_WAIT = 1.5


class PinchTabClient:
    """Thin wrapper over the pinchtab CLI (present on PATH after install)."""

    def __init__(self, html_base: str = DEFAULT_HTML_BASE, timeout: float = 45.0):
        self.html_base = html_base
        self.timeout = timeout
        self._bin = shutil.which("pinchtab")

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """True if the pinchtab CLI is installed."""
        return self._bin is not None

    def is_ready(self) -> bool:
        """True if a PinchTab server + Chrome are reachable."""
        if not self.is_available():
            return False
        try:
            out = subprocess.run(
                [self._bin, "doctor", "browsers"],
                capture_output=True, text=True, timeout=20,
            )
            return "chrome" in out.stdout and "ready" in out.stdout
        except Exception:
            return False

    # ------------------------------------------------------------------
    def _run(self, args, timeout=None):
        timeout = timeout or self.timeout
        try:
            proc = subprocess.run(
                [self._bin] + args,
                capture_output=True, text=True, timeout=timeout,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as exc:
            return -2, "", str(exc)

    # ------------------------------------------------------------------
    def snapshot(self, page: str = STG_PAGE) -> str:
        """Navigate to a local HTML doc and return the accessibility snapshot.

        Returns "" on any failure so callers can degrade gracefully.
        """
        if not self.is_available():
            return ""
        url = f"{self.html_base}/{page}"
        rc, _, err = self._run(["nav", url])
        if rc != 0:
            log.warning("pinchtab nav failed: %s", err.strip()[:200])
            return ""
        time.sleep(_RENDER_WAIT)
        rc, out, err = self._run(["snap"])
        if rc != 0:
            log.warning("pinchtab snap failed: %s", err.strip()[:200])
            return ""
        return out

    def text(self, page: str = STG_PAGE) -> str:
        """Extract full page text (best-effort; may be empty on Windows)."""
        if not self.is_available():
            return ""
        url = f"{self.html_base}/{page}"
        rc, _, err = self._run(["nav", url])
        if rc != 0:
            return ""
        time.sleep(_RENDER_WAIT)
        rc, out, _ = self._run(["text", "--raw"], timeout=30)
        return out if rc == 0 else ""

    # ------------------------------------------------------------------
    def search(self, query: str, page: str = STG_PAGE) -> str:
        """Extract content from the HTML doc relevant to *query*.

        Strategy: snapshot the page (reliable), filter lines that mention
        any query keyword. Falls back to raw text if snapshot is empty.
        Returns a compact context block, or "" if PinchTab is unavailable.
        """
        qwords = {w for w in re.findall(r"[a-z]{3,}", query.lower())}
        if not qwords:
            return ""

        snap = self.snapshot(page)
        if snap:
            lines = [ln.strip() for ln in snap.splitlines()
                     if ln.strip() and not ln.startswith(("#", "WARNING", "<"))]
            # headings look like: e12:heading "Acute Diarrhoea"
            hits = []
            for ln in lines:
                m = re.search(r'heading "([^"]+)"', ln)
                if m and any(w in m.group(1).lower() for w in qwords):
                    hits.append(m.group(1))
            if hits:
                # de-duplicate, keep order
                seen, uniq = set(), []
                for h in hits:
                    if h.lower() not in seen:
                        seen.add(h.lower())
                        uniq.append(h)
                return ("SEMANTIC BROWSER (PinchTab over local HTML guidelines):\n"
                        "Conditions matching the query in the STG 2022 index: "
                        + ", ".join(uniq[:8]))

        # fallback: raw text, filtered to keyword sentences
        txt = self.text(page)
        if txt:
            sentences = [s.strip() for s in txt.splitlines() if s.strip()]
            kept = [s for s in sentences if any(w in s.lower() for w in qwords)]
            if kept:
                return ("SEMANTIC BROWSER (PinchTab over local HTML guidelines):\n"
                        + "\n".join(kept[:6]))
        return ""
