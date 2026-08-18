"""LLM client for PidginPharma.

Talks to a local llama.cpp server (llama-server) over HTTP on 127.0.0.1.
Zero network dependency: only localhost.

Pipeline contract (see orchestrator.py):
  normalizer  : Pidgin -> English query
  this module : English query + DocReader context -> English clinical answer
  reformulator: English answer -> Pidgin-flavoured answer
"""

import json
import logging
import urllib.request

log = logging.getLogger("pidginpharma.llm")

DEFAULT_LLM_URL = "http://127.0.0.1:8080"

# Strong clinical guardrails for the local model.
SYSTEM_PROMPT = (
    "You are PidginPharma, an offline clinical decision support assistant for "
    "Nigerian community health workers (CHEWs) and pharmacists in primary "
    "healthcare centres. You follow the official Nigeria Essential Medicines "
    "List and Nigeria Standard Treatment Guidelines.\n\n"
    "RULES:\n"
    "1. Answer in plain, clear English. The orchestrator will translate to "
    "Pidgin for the user.\n"
    "2. Be short and practical: cause, what to do, which medicine, dose if "
    "known, and when to refer.\n"
    "3. When drug-interaction or condition data is provided in CONTEXT, use "
    "it as the primary source and cite it (e.g. 'per NSTG 2022').\n"
    "4. Never invent doses or contraindications. If unsure, say so and "
    "recommend referring to the nearest higher-level facility.\n"
    "5. Flag RED FLAGS: severe dehydration, convulsions, difficulty "
    "breathing, altered consciousness, bleeding, high fever in infants, "
    "pregnancy complications - tell the worker to refer immediately.\n"
    "6. If the query is not a clinical question, answer politely in one line "
    "and steer back to health topics."
)

# Separators recognized by the local model's chat template.
CHAT_BEGIN = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
CHAT_END = "<|eot_id|>"
USER_BEGIN = "<|start_header_id|>user<|end_header_id|>\n\n"
ASSISTANT_BEGIN = "<|start_header_id|>assistant<|end_header_id|>\n\n"


def build_prompt(query: str, context: str = "") -> str:
    """Build the full prompt (system + user with context)."""
    ctx_block = ""
    if context:
        ctx_block = (
            "\n\nOFFICIAL LOCAL DATA (use this first):\n"
            "------------------------------------\n"
            f"{context}\n"
            "------------------------------------"
        )
    user_msg = (
        "Patient question / query from a community health worker: "
        f'"{query}"{ctx_block}\n\n'
        "Give a concise, safe, practical clinical answer."
    )
    return (
        f"{CHAT_BEGIN}{SYSTEM_PROMPT}{CHAT_END}"
        f"{USER_BEGIN}{user_msg}{CHAT_END}"
        f"{ASSISTANT_BEGIN}"
    )


def strip_generation(prompt: str, raw: str) -> str:
    """Remove the echoed prompt and trailing chat tokens from the raw output."""
    text = raw
    if prompt and text.startswith(prompt):
        text = text[len(prompt):]
    for tok in (CHAT_END, "<|eot_id|>", "<|end_of_text|>", "<|im_end|>"):
        text = text.replace(tok, "")
    return text.strip()


class LLMClient:
    """Thin HTTP client for the local llama-server."""

    def __init__(self, url: str = DEFAULT_LLM_URL, timeout: float = 180.0,
                 n_predict: int = 512, temperature: float = 0.3,
                 repeat_penalty: float = 1.3):
        self.url = url.rstrip("/")
        # SECURITY: warn if the LLM endpoint is not localhost.
        if "127.0.0.1" not in self.url and "localhost" not in self.url:
            log.warning("LLM URL %s is not localhost; ensure this is intended.", self.url)
        self.timeout = timeout
        self.n_predict = n_predict
        self.temperature = temperature
        self.repeat_penalty = repeat_penalty

    def is_ready(self) -> bool:
        try:
            req = urllib.request.urlopen(
                urllib.request.Request(f"{self.url}/health", method="GET"),
                timeout=3,
            )
            return req.status == 200
        except Exception:
            return False

    def complete(self, prompt: str) -> str:
        """Send a completion to llama-server and return the generated text."""
        payload = {
            "prompt": prompt,
            "n_predict": self.n_predict,
            "temperature": self.temperature,
            "repeat_penalty": self.repeat_penalty,
            "stop": ["<|eot_id|>", "<|end_of_text|>", "</s>"],
            "stream": False,
        }
        req = urllib.request.Request(
            f"{self.url}/completion",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return strip_generation(prompt, data.get("content", ""))

    # Maximum context length (chars) to avoid overwhelming the local model.
    MAX_CONTEXT_LEN = 6000

    def ask(self, query: str, context: str = "") -> str:
        """Full round trip: build prompt, complete, strip tokens."""
        if not self.is_ready():
            raise ConnectionError(
                "Local model server not reachable. Start it with start.sh "
                "(download_model.sh first if models are missing)."
            )
        # Truncate context if too large for the model context window.
        if len(context) > self.MAX_CONTEXT_LEN:
            context = context[:self.MAX_CONTEXT_LEN] + "\n[...truncated...]"
        prompt = build_prompt(query, context)
        return self.complete(prompt)
