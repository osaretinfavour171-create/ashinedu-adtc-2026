#!/usr/bin/env python3
"""PidginPharma Orchestrator.

REPL that routes input through the full pipeline:

    Pidgin/English input
        -> PidginNormalizer (to clean English query)
        -> SymptomDetector  (is this a symptom or drug question?)
        -> ClinicalIntake   (if symptom: ask age, weight, symptoms, allergies...)
        -> Cache check      (instant response for repeated queries)
        -> DocReaderClient  (official local data: conditions + interactions)
        -> LLMClient        (local llama.cpp model, offline)
        -> PidginReformulator (back to Pidgin-flavoured answer)
        -> ResponseCache store

Usage:
    python orchestrator.py [--no-model] [--no-docreader] [--lang en|pidgin]
                           [--intake] [--no-intake]

Exit commands: exit, quit, q
"""

import argparse
import atexit
import logging
import os
import random
import signal
import subprocess
import sys
import time

# Windows consoles default to cp1252, which cannot print medical characters
# like β (beta) from the guidelines. Force UTF-8 output everywhere.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from cache import ResponseCache
from docreader_client import DocReaderClient
from intake import PatientContext, quick_intake, run_intake
from llm import LLMClient
from metrics import Metrics
from pinchtab_client import PinchTabClient
from pidgin.normalizer import PidginNormalizer
from pidgin.reformulator import PidginReformulator
from dosage import calculate_dose, get_red_flags, needs_iv_fluids, format_iv_recommendation
from followup import FollowUpTracker
from inference import infer_context, build_patient_context_from_query, get_question_prompt
from symptom_detector import classify_query
from translations import (
    get_intake_prompt, get_loading_messages, get_response,
    get_red_flag, get_iv_guidance, get_summary,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pidginpharma")

# Paths for auto-restart (relative to app/ directory)
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_HERE)
_TOOLS = os.path.join(_PROJECT, "tools")
_DATA = os.path.join(_HERE, "data")
_DOCREADER_BIN = os.path.join(_TOOLS, "docreader.exe")
_LLAMA_BIN = os.path.join(_TOOLS, "llamacpp", "llama-server.exe")
_MODELS_DIR = os.path.join(_PROJECT, "model")

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

HELP_TEXT = """Type your question in English, Pidgin, Hausa, or Yoruba:
  "my pikin get hot body and dey vomit"     (symptom - will ask follow-up questions)
  "artemether lumefantrine and quinine"     (drug interaction - direct answer)
  "treatment for acute diarrhoea"           (general health question)
  "metronidazole plus warfarin"             (drug question - direct answer)

Commands: help, status, stats, clear-cache, follow-up, lang, exit
"""

# Calming messages are now loaded from translations module based on language.
# FALLBACK_MESSAGES used if translations module is unavailable.
FALLBACK_MESSAGES = [
    "Please wait... I dey check the official guidelines for you.",
    "Hold on small... I dey look through the treatment book.",
    "Just a moment... I dey search for the right medicine info.",
    "One second... I dey check the drug interaction table for you.",
    "Hold on... I dey find di best answer from di Nigeria guidelines.",
]

# ---- Interactive health tips shown while the model loads ----
HEALTH_TIPS = [
    ("TIP: For malaria, always use ACT (Artemisinin-based Combination Therapy). "
     "Never use Chloroquine alone — resistance don already."),
    ("DID YOU KNOW: ORS (Oral Rehydration Salts) fit save pikin wey get diarrhoea. "
     "Mix am with clean water and give am small small."),
    ("TIP: Paracetamol dose for pikin na 10-15 mg per kg body weight. "
     "No give adult dose to pikin!"),
    ("REMEMBER: Fever + convulsions + difficulty breathing = REFER IMMEDIATELY. "
     "No try am for clinic."),
    ("DID YOU KNOW: Metronidazole no dey mix well with alcohol. "
     "Tell patient to dey avoid alcohol during treatment."),
    ("TIP: For pregnant women, IPTp-SP (Sulfadoxine-Pyrimethamine) "
     "dey given from 13 weeks. At least 3 doses."),
    ("REMEMBER: Antibiotics no dey work for viral infection. "
     "Don't prescribe am for common cold."),
    ("DID YOU KNOW: Zinc supplement dey very important for pikin with diarrhoea. "
     "Give 20mg daily for 10-14 days for pikin wey don reach 6 months."),
    ("TIP: Before giving any medicine, always ask about allergy. "
     "Penicillin allergy na very common."),
    ("REMEMBER: For severe dehydration, IV fluid na the way to go. "
     "Use Normal Saline or Ringer Lactate."),
    ("DID YOU KNOW: Artemether-Lumefantrine (AL) dey work best when you take am with food "
     "or fatty drink. E help am absorb better."),
    ("TIP: For hypertension, first-line drugs na Amlodipine, Enalapril, or Hydrochlorothiazide. "
     "Start with low dose."),
]

# Messages shown during service recovery (while it restarts).
RECOVERING_TIPS = [
    "I don notice say one part of me stop work. I dey fix am now...",
    "Small wahala — I dey restart the brain. Hold on small...",
    "One service dey sleep. I dey wake am up for you...",
]

# Language display names
LANG_NAMES = {
    "pidgin": "Pidgin English",
    "en": "English",
}


def _pick_model() -> str:
    """Return the best available model filename, or empty string."""
    primary = os.path.join(_MODELS_DIR, "medgemma-1.5-4b-it-Q8_0.gguf")
    fallback = os.path.join(_MODELS_DIR, "qwen2.5-1.5b-instruct-q8_0.gguf")
    if os.path.isfile(primary):
        return "medgemma-1.5-4b-it-Q8_0.gguf"
    if os.path.isfile(fallback):
        return "qwen2.5-1.5b-instruct-q8_0.gguf"
    return ""


def _show_health_tips(duration: int, tips_pool: list = None) -> None:
    """Show rotating health tips for `duration` seconds."""
    if tips_pool is None:
        tips_pool = HEALTH_TIPS
    tips = random.sample(tips_pool, min(len(tips_pool), max(1, duration // 3)))
    elapsed = 0
    for tip in tips:
        if elapsed >= duration:
            break
        print(f"  \U0001f48a {tip}")
        wait = min(3, duration - elapsed)
        time.sleep(wait)
        elapsed += wait


def _try_start_docreader() -> bool:
    """Attempt to start DocReader in the background. Returns True if started."""
    if not os.path.isfile(_DOCREADER_BIN):
        return False
    try:
        log_path = os.path.join(_TOOLS, "docreader.log")
        log_fh = open(log_path, "w")
        subprocess.Popen(
            [_DOCREADER_BIN, "-addr", "127.0.0.1:8765", "-data", _DATA],
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            cwd=_PROJECT,
        )
        for _ in range(10):
            time.sleep(1)
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2)
                return True
            except Exception:
                continue
    except Exception as exc:
        log.warning("Failed to start DocReader: %s", exc)
    return False


def _try_start_llm() -> bool:
    """Attempt to start the LLM server in the background. Returns True if started."""
    if not os.path.isfile(_LLAMA_BIN):
        return False
    model = _pick_model()
    if not model:
        return False
    model_path = os.path.join(_MODELS_DIR, model)
    try:
        log_path = os.path.join(_TOOLS, "llama.log")
        log_fh = open(log_path, "w")
        subprocess.Popen(
            [_LLAMA_BIN, "-m", model_path,
             "--host", "127.0.0.1", "--port", "8080",
             "-c", "2048", "--threads", "4", "--no-webui"],
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            cwd=_PROJECT,
        )
        for _ in range(60):
            time.sleep(1)
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2)
                return True
            except Exception:
                continue
    except Exception as exc:
        log.warning("Failed to start LLM server: %s", exc)
    return False


class Orchestrator:
    def __init__(self, use_model=True, use_docreader=True, use_pinchtab=False,
                 lang="pidgin", intake_enabled=True):
        self.lang = lang
        self.use_model = use_model
        self.use_docreader = use_docreader
        self.use_pinchtab = use_pinchtab
        self.intake_enabled = intake_enabled
        self.normalizer = PidginNormalizer()
        self.reformulator = PidginReformulator()
        self.docreader = DocReaderClient() if use_docreader else None
        self.llm = LLMClient() if use_model else None
        self.pinchtab = PinchTabClient() if use_pinchtab else None
        self.cache = ResponseCache()
        self.metrics = Metrics()
        self.followup = FollowUpTracker()

        # Register cleanup handlers
        atexit.register(self._cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\n\nSaving session data... Bye bye! Stay safe.")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        """Save metrics on exit."""
        try:
            self.metrics.save()
        except Exception:
            pass

    # ------------------------------------------------------------------
    @staticmethod
    def loading_message(lang: str = "pidgin") -> str:
        """Return a random calming loading message in the selected language."""
        try:
            msgs = get_loading_messages(lang)
        except Exception:
            msgs = FALLBACK_MESSAGES
        return random.choice(msgs)

    def status(self) -> str:
        lines = []
        if self.docreader:
            ok = self.docreader.is_ready()
            lines.append("Data server:   " + ("READY" if ok else "OFFLINE"))
        if self.llm:
            ok = self.llm.is_ready()
            lines.append("Model server:  " + ("READY" if ok else "OFFLINE"))
        if self.pinchtab:
            ok = self.pinchtab.is_ready()
            lines.append("Browser layer: " + ("READY" if ok else "OFFLINE"))
        lang_name = LANG_NAMES.get(self.lang, self.lang)
        lines.append(f"Language: {lang_name} (type 'lang' to switch between Pidgin and English)")
        lines.append("Intake: " + ("ON" if self.intake_enabled else "OFF"))
        # Cache stats
        cs = self.cache.stats()
        lines.append(f"Cache: {cs['size']}/{cs['max_size']} entries ({cs['hit_rate']} hit rate)")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    def _ensure_services(self) -> None:
        """Check services and restart any that have crashed."""
        if self.docreader and not self.docreader.is_ready():
            print(f"\n  {random.choice(RECOVERING_TIPS)}")
            log.info("DocReader is down, attempting restart...")
            if _try_start_docreader():
                log.info("DocReader restarted successfully.")
                print("  \u2705 Data server is back!\n")
            else:
                log.warning("DocReader restart failed.")
                print("  \u26a0\ufe0f  Data server could not restart. Drug lookups may not work.\n")

        if self.llm and not self.llm.is_ready():
            print(f"\n  {random.choice(RECOVERING_TIPS)}")
            log.info("Model server is down, attempting restart...")
            print("  While I dey load, here are some health tips:\n")
            _show_health_tips(20)
            if _try_start_llm():
                log.info("Model server restarted successfully.")
                print("  \u2705 Clinical brain is back!\n")
            else:
                log.warning("Model server restart failed.")
                print("  \u26a0\ufe0f  Clinical brain could not restart. Drug interactions still work.\n")

    def answer(self, raw: str, patient_ctx: PatientContext = None) -> tuple[str, str]:
        """Full pipeline for one user input.

        Args:
            raw: The raw user input (Pidgin or English).
            patient_ctx: Optional structured patient info from intake flow.

        Returns:
            (answer, source) where source is "cache", "docreader", "llm", or "fallback".
        """
        # Ensure services are alive before processing.
        _start = time.time()
        self._ensure_services()

        query = self.normalizer.normalize(raw)
        if not query:
            return ("Abeg, tell me wetin dey worry di patient small small.", "fallback")

        # 0. Check cache first (instant response for repeated queries).
        cache_key = query
        if patient_ctx and patient_ctx.symptoms:
            # Include patient context in cache key for personalized answers
            cache_key = f"{query}|{patient_ctx.age or ''}|{patient_ctx.weight_kg or ''}"
        cached = self.cache.get(cache_key, self.lang)
        if cached is not None:
            return (cached, "cache")

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
            except Exception:
                log.warning("PinchTab search error: %s", exc)

        # 2. Build patient context block for the LLM.
        patient_block = ""
        if patient_ctx:
            patient_block = patient_ctx.to_prompt_block()

        # 3. If this is a clear drug-interaction query, answer from local
        #    data directly (fast + authoritative) and skip the model.
        if interaction_text:
            english = self._compose_drug_answer(interaction_text, query, context)
            source = "docreader"
        elif self.llm and self.llm.is_ready():
            try:
                english = self.llm.ask(query, context, patient_block=patient_block)
                source = "llm"
            except Exception as exc:
                log.warning("LLM error: %s", exc)
                english = self._fallback_answer(context)
                source = "fallback"
        else:
            english = self._fallback_answer(context)
            source = "fallback"

        # 4. Add dosage calculations if we have patient context.
        if patient_ctx and patient_ctx.age_years is not None and patient_ctx.weight_kg:
            # Check for red flags based on vitals
            red_flags = get_red_flags(
                patient_ctx.age_years, patient_ctx.weight_kg,
                patient_ctx.temperature, patient_ctx.pulse,
                patient_ctx.respiratory_rate, patient_ctx.spo2,
            )
            if red_flags:
                english = "\n\n".join(red_flags) + "\n\n" + english

            # Try to calculate doses for mentioned drugs
            dose_info = self._calculate_doses_for_query(query, patient_ctx)
            if dose_info:
                english = english + "\n\nRECOMMENDED DOSING (based on patient weight " + str(patient_ctx.weight_kg) + "kg):\n" + "\n".join(dose_info)

        # 5. Reformulate based on language.
        #    Pidgin: full reformulation to Pidgin-flavoured text.
        #    English/Hausa/Yoruba: return English (clinical accuracy).
        if self.lang == "pidgin":
            answer = self.reformulator.reformulate(english)
        else:
            answer = english

        # 6. Store in cache for instant future lookups.
        self.cache.put(cache_key, self.lang, answer)

        # 7. Record metrics.
        elapsed = time.time() - _start
        self.metrics.record_query(raw, elapsed, source)
        return (answer, source)

    # ------------------------------------------------------------------
    def _calculate_doses_for_query(self, query: str, ctx) -> list[str]:
        """Try to calculate doses for drugs mentioned in the query."""
        results = []
        # Common drug names to look for in the query
        drug_names = [
            "paracetamol", "ibuprofen", "amoxicillin", "metronidazole",
            "artemether", "lumefantrine", "coartem", "doxycycline",
            "azithromycin", "erythromycin", "ciprofloxacin", "zinc",
            "ors", "oral rehydration", "amlodipine", "enalapril",
            "diazepam", "phenobarbitone", "aspirin", "sulfadoxine",
            "pyrimethamine", "artesunate",
            "normal saline", "ringer lactate", "drip",
            "iv paracetamol", "iv amoxicillin", "iv metronidazole",
            "iv artesunate", "iv diazepam",
        ]
        query_lower = query.lower()
        for drug in drug_names:
            if drug in query_lower:
                dose = calculate_dose(drug, ctx.age_years, ctx.weight_kg)
                if dose:
                    results.append(dose.format_pidgin())
        return results

    # ------------------------------------------------------------------
    def _compose_drug_answer(self, interaction_text, query, context) -> str:
        parts = [interaction_text]
        if context:
            parts.append(context)
        return "\n\n".join(parts)

    def _fallback_answer(self, context) -> str:
        """The model is unavailable. If we have guideline context, show it."""
        if context:
            return (
                "I no fit use di clinical brain now, but from di official Nigeria "
                "guidelines wey I get:\n\n"
                + context
                + "\n\nIf di patient dey worse, send am go hospital quick quick."
            )
        return (
            "Sorry - something dey wrong with the system. "
            "I no fit answer clinical questions now.\n\n"
            "Please:\n"
            "  1. Try again in a few minutes\n"
            "  2. If e no work, restart the computer and try again\n"
            "  3. If e still no work, ask your supervisor or ICT person for help\n\n"
            "If this is an emergency, please refer the patient to hospital now."
        )


# Source labels for the user (in Pidgin)
SOURCE_LABELS = {
    "cache": "\u26a1 (instant - from memory)",
    "docreader": "\U0001f4da (from official guidelines)",
    "llm": "\U0001f9e0 (from clinical brain)",
    "fallback": "\u26a0\ufe0f (basic info)",
}


def _set_ctx_field(ctx, field, value):
    """Set a field on PatientContext from raw user input."""
    from intake import _parse_age, _parse_weight, _parse_gender, _parse_temperature
    if field == "age":
        display, years = _parse_age(value)
        if display:
            ctx.age = display
            ctx.age_years = years
    elif field == "weight":
        kg, _ = _parse_weight(value)
        if kg:
            ctx.weight_kg = kg
    elif field == "gender":
        g = _parse_gender(value)
        if g:
            ctx.gender = g
    elif field == "symptoms":
        ctx.symptoms = value
    elif field == "duration":
        ctx.duration = value
    elif field == "temperature":
        t = _parse_temperature(value)
        if t:
            ctx.temperature = t
    elif field == "allergies":
        ctx.allergies = value
    elif field == "current_meds":
        ctx.current_meds = value
    elif field == "history":
        ctx.history = value


def main(argv=None):
    parser = argparse.ArgumentParser(description="PidginPharma orchestrator REPL")
    parser.add_argument("--no-model", action="store_true", help="skip the local LLM")
    parser.add_argument("--no-docreader", action="store_true", help="skip the DocReader")
    parser.add_argument("--pinchtab", action="store_true",
                        help="enable optional PinchTab browser layer (uses ~300-800MB extra RAM)")
    parser.add_argument("--lang", choices=["en", "pidgin"], default="pidgin",
                        help="answer language (default: pidgin)")
    parser.add_argument("--once", metavar="QUERY", help="answer one query and exit")
    parser.add_argument("--intake", action="store_true", default=True,
                        help="enable clinical intake flow for symptom queries (default: on)")
    parser.add_argument("--no-intake", action="store_true",
                        help="disable clinical intake flow (answer directly)")
    args = parser.parse_args(argv)

    intake_enabled = not args.no_intake

    orch = Orchestrator(
        use_model=not args.no_model,
        use_docreader=not args.no_docreader,
        use_pinchtab=args.pinchtab,
        lang=args.lang,
        intake_enabled=intake_enabled,
    )

    if args.once:
        print(Orchestrator.loading_message())
        answer, source = orch.answer(args.once)
        print(answer)
        print(f"\n  {SOURCE_LABELS.get(source, '')}")
        return 0

    print(BANNER)
    print(HELP_TEXT)
    print(orch.status())
    print()

    while True:
        try:
            raw = input("PidginPharma > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSaving session data... Bye bye! Stay safe.")
            orch.metrics.save()
            return 0
        if not raw:
            continue
        low = raw.lower()
        if low in ("exit", "quit", "q"):
            print("Saving session data... Bye bye! Stay safe.")
            orch.metrics.save()
            return 0
        if low in ("help", "h", "?"):
            print(HELP_TEXT)
            continue
        if low == "status":
            print(orch.status())
            continue
        if low == "stats":
            print(orch.metrics.summary())
            print()
            print(orch.cache.stats())
            continue
        if low == "clear-cache":
            orch.cache.clear()
            print("Cache cleared. All queries will be re-processed.")
            continue
        if low.startswith("lang ") or low.startswith("language "):
            new_lang = low.split(None, 1)[-1].strip()
            if new_lang in ("pidgin", "en"):
                orch.lang = new_lang
                lang_name = LANG_NAMES.get(new_lang, new_lang)
                print(f"  Language changed to: {lang_name}. All responses will now use this language.")
            else:
                print("  Available languages: pidgin, en, hausa, yoruba")
            continue
        if low in ("follow-up", "followup", "checkup", "check up"):
            result = orch.followup.run_followup(lang=orch.lang)
            if result:
                orch.metrics.record_query("followup", 0, "followup")
            continue
        try:
            # SECURITY: cap input length to prevent abuse.
            if len(raw) > 1000:
                print("Input too long. Keep your question short (under 1000 characters).")
                continue

            # Check if this needs the intake flow.
            query_type = classify_query(orch.normalizer.normalize(raw))
            patient_ctx = None

            if query_type == "symptom" and orch.intake_enabled:
                # Symptom query detected - run clinical intake.
                print(f"\n  \U0001f3e5 {get_response('symptom_detected', orch.lang)}\n")
                patient_ctx = run_intake(lang=orch.lang)
                # Use the symptoms from intake as the query context
                if patient_ctx.symptoms:
                    raw = patient_ctx.symptoms
                print(Orchestrator.loading_message(lang=orch.lang) + "\n")
            elif query_type == "symptom" and not orch.intake_enabled:
                # Intake disabled but symptom detected - try to extract from query
                patient_ctx = quick_intake(raw)
                print("\n" + Orchestrator.loading_message(lang=orch.lang) + "\n")
            else:
                print("\n" + Orchestrator.loading_message(lang=orch.lang) + "\n")

            answer, source = orch.answer(raw, patient_ctx=patient_ctx)
            print("\n" + answer + "\n")
            # Show source attribution
            src_label = SOURCE_LABELS.get(source, "")
            if src_label:
                print(f"  {src_label}\n")
        except Exception as exc:
            log.error("error: %s", exc)
            print("Something dey wrong. Try again small.\n")


if __name__ == "__main__":
    sys.exit(main())
