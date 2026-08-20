"""Follow-up flow for PidginPharma.

After the initial consultation and treatment, this module tracks whether
the patient improved. It can be triggered by the CHEW typing "follow up"
or "check up" or by the system remembering previous consultations.

The follow-up asks:
  1. Is the patient better, worse, or the same?
  2. Are there new symptoms?
  3. Did the patient take the medicine as prescribed?
  4. Any side effects?
  5. Temperature now (if available)

Based on the answers, it recommends:
  - Continue current treatment
  - Modify treatment
  - REFER to hospital immediately
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

_HISTORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"
)


@dataclass
class ConsultationRecord:
    """Record of a previous consultation for follow-up tracking."""
    timestamp: float
    patient_summary: str  # "3 years, male, 15kg, fever and vomiting"
    diagnosis: str        # What was diagnosed/prescribed
    treatment_given: str  # What medicine was given
    follow_up_needed: bool = True


@dataclass
class FollowUpResult:
    """Result of a follow-up assessment."""
    status: str  # "improved", "worse", "same", "new_symptoms"
    medication_taken: Optional[str] = None
    side_effects: Optional[str] = None
    temperature_now: Optional[str] = None
    recommendation: str = ""
    refer: bool = False


class FollowUpTracker:
    """Tracks consultations and manages follow-up flows."""

    def __init__(self):
        self._history: list[ConsultationRecord] = []
        self._load_history()

    def _history_path(self) -> str:
        os.makedirs(_HISTORY_DIR, exist_ok=True)
        return os.path.join(_HISTORY_DIR, "consultation_history.json")

    def _load_history(self) -> None:
        path = self._history_path()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._history = [ConsultationRecord(**r) for r in data]
            except (json.JSONDecodeError, OSError):
                self._history = []

    def _save_history(self) -> None:
        path = self._history_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([asdict(r) for r in self._history[-50:]], f,
                          indent=2, ensure_ascii=False)
        except OSError:
            pass

    def record_consultation(self, patient_summary: str, diagnosis: str,
                            treatment: str) -> None:
        """Save a consultation record for future follow-up."""
        rec = ConsultationRecord(
            timestamp=time.time(),
            patient_summary=patient_summary,
            diagnosis=diagnosis,
            treatment_given=treatment,
        )
        self._history.append(rec)
        self._save_history()

    def has_pending_followup(self) -> bool:
        """Check if any consultation is due for follow-up (2+ days old)."""
        now = time.time()
        for rec in self._history:
            if rec.follow_up_needed and (now - rec.timestamp) > 2 * 86400:
                return True
        return False

    def get_pending_followup(self) -> Optional[ConsultationRecord]:
        """Get the oldest consultation needing follow-up."""
        now = time.time()
        for rec in self._history:
            if rec.follow_up_needed and (now - rec.timestamp) > 2 * 86400:
                return rec
        return None

    def run_followup(self, lang: str = "pidgin",
                     input_fn=None, output_fn=None) -> Optional[FollowUpResult]:
        """Run the interactive follow-up flow.

        Returns FollowUpResult with assessment, or None if no follow-up needed.
        """
        if input_fn is None:
            input_fn = input
        if output_fn is None:
            output_fn = print

        record = self.get_pending_followup()
        if not record:
            if lang == "pidgin":
                output_fn("  No follow-up pending. All patients don update.")
            else:
                output_fn("  No follow-up pending. All patients are up to date.")
            return None

        days_ago = int((time.time() - record.timestamp) / 86400)

        output_fn("")
        if lang == "pidgin":
            output_fn(f"  \U0001f50d FOLLOW-UP: {days_ago} days ago you see patient: {record.patient_summary}")
            output_fn(f"  Treatment wey you give: {record.treatment_given}")
            output_fn("")
            output_fn("  Make I ask you about di patient progress:")
        else:
            output_fn(f"  FOLLOW-UP: {days_ago} days ago you saw patient: {record.patient_summary}")
            output_fn(f"  Treatment given: {record.treatment_given}")
            output_fn("")
            output_fn("  Let me ask about the patient's progress:")

        result = FollowUpResult(status="unknown")

        # Q1: Better, worse, or same?
        if lang == "pidgin":
            output_fn("  1. How the patient now? (better / worse / same / new problem)")
        else:
            output_fn("  1. How is the patient now? (better / worse / same / new symptoms)")
        try:
            raw = input_fn("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return result

        if any(w in raw for w in ("better", "well", "good", "fine", "improve")):
            result.status = "improved"
        elif any(w in raw for w in ("worse", "bad", "no good", "dey worse")):
            result.status = "worse"
            result.refer = True
        elif any(w in raw for w in ("new", "different", "another")):
            result.status = "new_symptoms"
        else:
            result.status = "same"

        # Q2: Did they take the medicine?
        if lang == "pidgin":
            output_fn("  2. Di patient take the medicine wey you give am?")
        else:
            output_fn("  2. Did the patient take the medicine as prescribed?")
        try:
            raw = input_fn("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return result

        if any(w in raw.lower() for w in ("yes", "yeah", "dey take", "don take")):
            result.medication_taken = "yes"
        elif any(w in raw.lower() for w in ("no", "nah", "no take", "stop")):
            result.medication_taken = "no"
        else:
            result.medication_taken = raw

        # Q3: Any side effects?
        if lang == "pidgin":
            output_fn("  3. The patient get any side effect? (e.g. vomit, rash, itch). If none, say 'no'.")
        else:
            output_fn("  3. Any side effects? (e.g. vomiting, rash, itching). Say 'none' if none.")
        try:
            raw = input_fn("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return result

        if any(w in raw.lower() for w in ("no", "none", "nothing", "na")):
            result.side_effects = None
        else:
            result.side_effects = raw

        # Q4: Temperature now
        if lang == "pidgin":
            output_fn("  4. You get thermometer now? If yes, wetin e read?")
        else:
            output_fn("  4. Do you have a thermometer now? If yes, what does it read?")
        try:
            raw = input_fn("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            return result

        if any(w in raw.lower() for w in ("no", "skip", "no thermometer")):
            result.temperature_now = None
        else:
            result.temperature_now = raw

        # Generate recommendation
        result.recommendation = self._generate_recommendation(result, record, lang)

        # Mark follow-up as done
        record.follow_up_needed = False
        self._save_history()

        # Show recommendation
        output_fn("")
        output_fn(result.recommendation)
        output_fn("")

        return result

    def _generate_recommendation(self, result: FollowUpResult,
                                 record: ConsultationRecord,
                                 lang: str) -> str:
        """Generate a clinical recommendation based on follow-up answers."""
        if result.refer:
            return (
                "\u26a0\ufe0f REFER TO HOSPITAL NOW.\n"
                "   The patient condition is worse. This needs higher-level care.\n"
                "   Do not delay — send the patient to the nearest hospital."
            )

        if result.status == "improved":
            msg = "\u2705 Good news — the patient is improving!"
            if result.medication_taken == "yes":
                msg += "\n   Continue the current medicine as prescribed."
            else:
                msg += "\n   Make sure the patient finishes ALL the medicine, even if feeling better."
            if result.side_effects:
                msg += f"\n   \u26a0\ufe0f Side effects noted: {result.side_effects}"
                msg += "\n   If side effects are severe, stop the medicine and refer."
            return msg

        if result.status == "new_symptoms":
            return (
                "\u26a0\ufe0f NEW SYMPTOMS detected.\n"
                "   The patient may need a different diagnosis or treatment.\n"
                "   Describe the new symptoms in your next query for reassessment.\n"
                "   If severe (convulsions, difficulty breathing, severe pain), REFER NOW."
            )

        if result.status == "same":
            msg = "\u26a0\ufe0f No improvement after 2-3 days."
            if result.medication_taken == "no":
                msg += (
                    "\n   The patient did NOT take the medicine as prescribed."
                    "\n   Counsel the patient on importance of completing treatment."
                    "\n   If still sick, bring them back for reassessment."
                )
            else:
                msg += (
                    "\n   Treatment may not be working. Consider:"
                    "\n   - Reassess the diagnosis"
                    "\n   - Check for drug resistance"
                    "\n   - Consider a second-line drug"
                    "\n   - If no improvement in 24 more hours, REFER to hospital"
                )
            if result.side_effects:
                msg += f"\n   \u26a0\ufe0f Side effects: {result.side_effects}"
                msg += "\n   Consider switching to an alternative drug."
            return msg

        return "Follow-up recorded. Please continue monitoring the patient."
