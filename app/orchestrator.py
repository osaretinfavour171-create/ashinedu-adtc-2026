#!/usr/bin/env python3
"""PidginPharma Orchestrator.

REPL that routes input through the full pipeline:

    Pidgin/English input
        -> PidginNormalizer (to clean English query)
        -> DocReaderClient  (official local data: conditions + interactions)
        -> LLMClient        (local llama.cpp model, offline)
        -> PidginReformulator (back to Pidgin-flavoured answer)

Usage:
    python orchestrator.py [--no-model] [--no-docreader] [--lang en|pidgin]

Exit commands: exit, quit, q
"""

import argparse
import logging
import random
import sys

# Windows consoles default to cp1252, which cannot print medical characters
# like β (beta) from the guidelines. Force UTF-8 output everywhere.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from docreader_client import DocReaderClient
from llm import LLMClient
from pinchtab_client import PinchTabClient
from pidgin.normalizer import PidginNormalizer
from pidgin.reformulator import PidginReformulator

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pidginpharma")

BANNER = r"""
  ____  _ _            _  __  ____  _                          __
 |  _ \(_) |          (_)/ _|/ ___|| |__  _ __ __ _ _ __ _ __ / /
 | |_) | | |  _____   _| |_ \___ \| '_ \| '_ ` _ \ '_ \| '_ \| |
 |  __/| | | |_____| (_|  _| ___) | | | | | | | | | |_) | | | | |
 |_|   |_|_|         (_)_| |____/|_| |_|_| |_| |_| .__/|_| |_| | |
                                                 |_|
  Offline clinical decision support for Nigerian community health workers
  Data: Nigeria EML 2020 + NSTG 2022 + local drug-interaction database
"""

HELP_TEXT = """Type your question in English or Pidgin, e.g.:
  "my pikin get hot body and dey vomit"
  "artemether lumefantrine and quinine - e dey safe?"
  "treatment for acute diarrhoea"
  "metronidazole plus warfarin"
Commands: help, status, exit
"""

# Calming messages shown while the model processes a query.
LOADING_MESSAGES = [
    "Please wait... I dey check the official guidelines for you.",
    "Hold on small... I dey look through the treatment book.",
    "Just a moment... I dey search for the right medicine info.",
    "One second... I dey check the drug interaction table for you.",
    "Hold on... I dey find di best answer from di Nigeria guidelines.",
]


class Orchestrator:
    def __init__(self, use_model=True, use_docreader=True, use_pinchtab=False, lang="pidgin"):
        self.lang = lang
        self.use_model = use_model
        self.use_docreader = use_docreader
        self.use_pinchtab = use_pinchtab
        self.normalizer = PidginNormalizer()
        self.reformulator = PidginReformulator()
        self.docreader = DocReaderClient() if use_docreader else None
        self.llm = LLMClient() if use_model else None
        self.pinchtab = PinchTabClient() if use_pinchtab else None
        self._dr_ready = None
        self._llm_ready = None

    # ------------------------------------------------------------------
    @staticmethod
    def loading_message() -> str:
        """Return a random calming loading message."""
        return random.choice(LOADING_MESSAGES)

    def status(self) -> str:
        lines = []
        if self.docreader:
            ok = self.docreader.is_ready()
            self._dr_ready = ok
            lines.append(f"DocReader (official data server): {'ONLINE' if ok else 'OFFLINE - run start.sh'}")
        if self.llm:
            ok = self.llm.is_ready()
            self._llm_ready = ok
            lines.append(f"Local model server (llama.cpp):   {'ONLINE' if ok else 'OFFLINE - run start.sh'}")
        if self.pinchtab:
            ok = self.pinchtab.is_ready()
            lines.append(f"PinchTab browser layer (optional): {'ONLINE' if ok else 'OFFLINE - pinchtab/Chrome not available'}")
        lines.append("Language layer (Pidgin<->English): READY")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def answer(self, raw: str) -> str:
        """Full pipeline for one user input."""
        query = self.normalizer.normalize(raw)
        if not query:
            return "Abeg, tell me wetin dey worry di patient small small."

        # 1. Local official data (conditions + interactions).
        context = ""
        interaction_text = ""
        if self.docreader and self.docreader.is_ready():
            try:
                result = self.docreader.search(query)
                context = self.docreader.build_context(query)
                interaction_text = self.docreader.format_interaction_answer(result)
            except Exception as exc:
                log.warning("DocReader error: %s", exc)

        # 1b. Optional semantic layer: browse the converted HTML guidelines.
        if self.pinchtab and not interaction_text:
            try:
                pb = self.pinchtab.search(query)
                if pb:
                    context = (context + "\n\n" + pb).strip()
            except Exception as exc:
                log.warning("PinchTab search error: %s", exc)

                # 2. If this is a clear drug-interaction query, answer from local
        #    data directly (fast + authoritative) and skip the model.
        if interaction_text:
            english = self._compose_drug_answer(interaction_text, query, context)
        elif self.llm and self.llm.is_ready():
            try:
                english = self.llm.ask(query, context)
            except Exception as exc:
                log.warning("LLM error: %s", exc)
                english = self._fallback_answer(query, context)
        else:
            english = self._fallback_answer(query, context)

        # 3. Reformulate to Pidgin unless the user asked for plain English.
        if self.lang == "en":
            return english
        return self.reformulator.reformulate(english)

    # ------------------------------------------------------------------
    def _compose_drug_answer(self, interaction_text, query, context) -> str:
        parts = [interaction_text]
        if context:
            parts.append(context)
        return "\n\n".join(parts)

    def _fallback_answer(self, query, context) -> str:
        """No model available: answer from official data alone."""
        if context:
            return (
                "I no get di model running now, but from di official Nigeria "
                "guidelines wey I get for dis machine:\n\n"
                + context
                + "\n\nIf di patient dey worse, send am go hospital quick quick."
            )
        return (
            "Sorry - di offline model and data server no dey reachable now. "
            "Run `bash start.sh` make dem start. If e be emergency, send di "
            "patient go hospital now now."
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description="PidginPharma orchestrator REPL")
    parser.add_argument("--no-model", action="store_true", help="skip the local LLM")
    parser.add_argument("--no-docreader", action="store_true", help="skip the DocReader")
    parser.add_argument("--pinchtab", action="store_true",
                        help="enable optional PinchTab browser layer over converted HTML docs (uses ~300-800MB extra RAM)")
    parser.add_argument("--lang", choices=["en", "pidgin"], default="pidgin",
                        help="answer language (default: pidgin)")
    parser.add_argument("--once", metavar="QUERY", help="answer one query and exit")
    args = parser.parse_args(argv)

    orch = Orchestrator(
        use_model=not args.no_model,
        use_docreader=not args.no_docreader,
        use_pinchtab=args.pinchtab,
        lang=args.lang,
    )

    if args.once:
        print(Orchestrator.loading_message())
        print(orch.answer(args.once))
        return 0

    print(BANNER)
    print(HELP_TEXT)
    print(orch.status())
    print()

    while True:
        try:
            raw = input("PidginPharma > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye bye! Stay safe.")
            return 0
        if not raw:
            continue
        low = raw.lower()
        if low in ("exit", "quit", "q"):
            print("Bye bye! Stay safe.")
            return 0
        if low in ("help", "h", "?"):
            print(HELP_TEXT)
            continue
        if low == "status":
            print(orch.status())
            continue
        try:
            # SECURITY: cap input length to prevent abuse.
            if len(raw) > 1000:
                print("Input too long. Keep your question short (under 1000 characters).")
                continue
            print("\n" + Orchestrator.loading_message() + "\n")
            print("\n" + orch.answer(raw) + "\n")
        except Exception as exc:
            log.error("error: %s", exc)
            print("Something dey wrong - try again small.")


if __name__ == "__main__":
    sys.exit(main())
