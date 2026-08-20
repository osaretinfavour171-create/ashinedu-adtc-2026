"""Clinical intake flow for PidginPharma.

When a user describes symptoms (rather than asking a direct drug question),
this module guides them through a structured patient intake to collect:

  1. Patient age (critical for dosing)
  2. Patient weight (critical for mg/kg dosing)
  3. Gender
  4. Main symptoms + duration
  5. Temperature (if available)
  6. Allergies
  7. Pregnancy status (for women of childbearing age)
  8. Current medications (for interaction checks)
  9. Relevant medical history

The intake is conversational and in Pidgin. Each answer is validated
before moving to the next question. The final PatientContext is passed
to the LLM as structured data for much more accurate diagnosis.

Design:
  - SKILL model: each question is a (key, prompt, validator, required) tuple.
  - "skip" or "i no know" or empty → field marked unknown, move on.
  - Max 9 questions, but early exit if enough info is gathered.
  - The intake is OPTIONAL — user can type a full question to skip it.
"""

import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class PatientContext:
    """Structured patient information collected during intake."""
    age: Optional[str] = None            # "3 years", "adult", "25 years"
    age_years: Optional[float] = None    # numeric age in years
    weight_kg: Optional[float] = None
    gender: Optional[str] = None         # "male", "female", "unknown"
    symptoms: Optional[str] = None       # "fever, vomiting, diarrhoea"
    duration: Optional[str] = None       # "2 days", "since yesterday"
    temperature: Optional[str] = None    # "38.5°C", "very hot"
    allergies: Optional[str] = None      # "penicillin", "none"
    pregnant: Optional[bool] = None
    current_meds: Optional[str] = None   # "paracetamol, amoxicillin"
    history: Optional[str] = None        # "asthma, diabetes"

    def to_prompt_block(self) -> str:
        """Format as a structured context block for the LLM."""
        lines = ["PATIENT INFORMATION:"]
        if self.age:
            lines.append(f"  Age: {self.age}")
        if self.weight_kg:
            lines.append(f"  Weight: {self.weight_kg} kg")
        if self.gender:
            lines.append(f"  Gender: {self.gender}")
        if self.symptoms:
            lines.append(f"  Symptoms: {self.symptoms}")
        if self.duration:
            lines.append(f"  Duration: {self.duration}")
        if self.temperature:
            lines.append(f"  Temperature: {self.temperature}")
        if self.allergies:
            lines.append(f"  Allergies: {self.allergies}")
        if self.pregnant is not None:
            lines.append(f"  Pregnant: {'Yes' if self.pregnant else 'No'}")
        if self.current_meds:
            lines.append(f"  Current medications: {self.current_meds}")
        if self.history:
            lines.append(f"  Medical history: {self.history}")
        return "\n".join(lines)

    def is_complete(self) -> bool:
        """We have enough info if we have age + symptoms at minimum."""
        return bool(self.age and self.symptoms)

    def summary_line(self) -> str:
        """One-line summary for the user to confirm."""
        parts = []
        if self.age:
            parts.append(self.age)
        if self.gender:
            parts.append(self.gender)
        if self.weight_kg:
            parts.append(f"{self.weight_kg}kg")
        if self.symptoms:
            parts.append(self.symptoms)
        return ", ".join(parts) if parts else "Patient info incomplete"


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _parse_age(text: str) -> tuple[Optional[str], Optional[float]]:
    """Parse age from user input. Returns (display, numeric_years)."""
    text = text.lower().strip()
    if not text or text in ("skip", "i no know", "no", "idk"):
        return None, None

    # "3 years", "3 yrs", "3y"
    m = re.search(r"(\d+)\s*(?:year|yr|y)\b", text)
    if m:
        y = float(m.group(1))
        return f"{int(y)} years", y

    # "3 months", "3 mos", "3m"
    m = re.search(r"(\d+)\s*(?:months?|mos)\b", text)
    if m:
        months = float(m.group(1))
        return f"{int(months)} months", months / 12.0

    # "3 days"
    m = re.search(r"(\d+)\s*(?:days?)\b", text)
    if m:
        days = float(m.group(1))
        return f"{int(days)} days", days / 365.0

    # Just a number → assume years
    m = re.search(r"(\d+)", text)
    if m:
        y = float(m.group(1))
        return f"{int(y)} years", y

    # Word forms
    word_nums = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "teen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
        "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    }
    for word, num in word_nums.items():
        if word in text:
            return f"{num} years", float(num)

    # Common Pidgin age expressions
    if "adult" in text or "grown" in text or "man" in text or "woman" in text:
        return "adult", 30.0
    if "babe" in text or "baby" in text or "newborn" in text or "new born" in text:
        return "newborn", 0.0
    if "pikin" in text or "child" in text or "small" in text:
        return "child (age unknown)", 5.0  # default to 5 for dosing

    return None, None


def _parse_weight(text: str) -> tuple[Optional[float], Optional[str]]:
    """Parse weight from user input. Returns (kg, display)."""
    text = text.lower().strip()
    if not text or text in ("skip", "i no know", "no", "idk"):
        return None, None

    # "30 kg", "30kg", "30 kilo", "30 kilogram"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilo)", text)
    if m:
        w = float(m.group(1))
        return w, f"{w} kg"

    # "66 pounds", "66 lbs"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lb|pound)", text)
    if m:
        w_lbs = float(m.group(1))
        w_kg = w_lbs * 0.453592
        return round(w_kg, 1), f"{round(w_kg, 1)} kg ({int(w_lbs)} lbs)"

    # Just a number — assume kg (most Nigerian health workers use kg)
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if m:
        w = float(m.group(1))
        if 1 <= w <= 200:  # reasonable weight range
            return w, f"{w} kg"

    return None, None


def _parse_gender(text: str) -> Optional[str]:
    text = text.lower().strip()
    if not text or text in ("skip", "i no know", "no", "idk"):
        return None
    if any(w in text for w in ("female", "girl", "woman", "she", "her")):
        return "female"
    if any(w in text for w in ("male", "boy", "man", "he", "him")):
        return "male"
    return None


def _parse_temperature(text: str) -> Optional[str]:
    text = text.lower().strip()
    if not text or text in ("skip", "i no know", "no", "idk", "no thermometer"):
        return None

    # "38.5", "38.5°C", "38.5C", "101.3F"
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*°?\s*([cf])?", text)
    if m:
        val = float(m.group(1))
        unit = (m.group(2) or "c").upper()
        if unit == "F":
            celsius = (val - 32) * 5 / 9
            return f"{celsius:.1f}°C ({val}°F)"
        return f"{val}°C"

    # Qualitative
    if any(w in text for w in ("very hot", "high", "too much", "severe")):
        return "high fever (no thermometer)"
    if any(w in text for w in ("hot", "warm", "mild")):
        return "fever (no thermometer)"
    if any(w in text for w in ("normal", "no", "nothing")):
        return "normal/no fever"

    return None


def _parse_yes_no(text: str) -> Optional[bool]:
    text = text.lower().strip()
    if not text or text in ("skip", "i no know", "no", "idk"):
        return None
    if any(w in text for w in ("yes", "yeah", "yep", "correct", "true", "i be")):
        return True
    if any(w in text for w in ("no", "nah", "nope", "false", "i no be")):
        return False
    return None


# ---------------------------------------------------------------------------
# Intake questions
# ---------------------------------------------------------------------------

@dataclass
class IntakeQuestion:
    key: str
    prompt_pidgin: str
    prompt_english: str
    parser: str  # function name to call
    required: bool = False
    followup: Optional[str] = None  # shown if answer is unclear


def _get_intake_questions() -> list[IntakeQuestion]:
    """Return the list of intake questions in order."""
    return [
        IntakeQuestion(
            key="age",
            prompt_pidgin="How old is di patient? (e.g. 3 years, 6 months, adult)",
            prompt_english="What is the patient's age? (e.g. 3 years, 6 months, adult)",
            parser="age",
            required=True,
            followup="Abeg tell me di patient age — even 'pikin' or 'adult' go help.",
        ),
        IntakeQuestion(
            key="weight",
            prompt_pidgin="How heavy is di patient? (e.g. 15 kg, 70 kg). If you no know, say 'skip'.",
            prompt_english="What is the patient's weight? (e.g. 15 kg, 70 kg). Say 'skip' if unknown.",
            parser="weight",
            required=False,
            followup="If you no get scale, you fit estimate — even rough guess dey help.",
        ),
        IntakeQuestion(
            key="gender",
            prompt_pidgin="Na boy or na girl?",
            prompt_english="Is the patient male or female?",
            parser="gender",
            required=False,
        ),
        IntakeQuestion(
            key="symptoms",
            prompt_pidgin="Wetin dey worry di patient? Describe di symptoms (e.g. fever, vomit, run stomach)",
            prompt_english="What symptoms does the patient have? (e.g. fever, vomiting, diarrhoea)",
            parser="text",
            required=True,
            followup="Tell me wetin dey wrong — wetin you see, wetin di patient dey feel.",
        ),
        IntakeQuestion(
            key="duration",
            prompt_pidgin="How long e don dey like dis? (e.g. 2 days, since yesterday)",
            prompt_english="How long has the patient had these symptoms? (e.g. 2 days, since yesterday)",
            parser="text",
            required=False,
        ),
        IntakeQuestion(
            key="temperature",
            prompt_pidgin="You get thermometer? If yes, wetin e read? If no, say 'skip'.",
            prompt_english="Do you have a thermometer reading? If yes, what is it? Say 'skip' if not.",
            parser="temperature",
            required=False,
        ),
        IntakeQuestion(
            key="allergies",
            prompt_pidgin="Di patient get any medicine wey e no fit take? (allergy). If none, say 'no'.",
            prompt_english="Does the patient have any drug allergies? Say 'no' if none.",
            parser="text",
            required=False,
        ),
        IntakeQuestion(
            key="pregnant",
            prompt_pidgin="Na woman of childbearing age? If yes, she don born before or she fit dey pregnant?",
            prompt_english="Is this a woman of childbearing age? Could she be pregnant?",
            parser="pregnant",
            required=False,
            followup="This one dey important for drug safety. Even 'I no know' go help.",
        ),
        IntakeQuestion(
            key="current_meds",
            prompt_pidgin="Di patient dey take any medicine now? (e.g. paracetamol, amoxicillin). If none, say 'no'.",
            prompt_english="Is the patient currently taking any medications? Say 'no' if none.",
            parser="text",
            required=False,
        ),
        IntakeQuestion(
            key="history",
            prompt_pidgin="Di patient get any long-term sickness? (e.g. asthma, diabetes, HIV). If none, say 'no'.",
            prompt_english="Does the patient have any chronic conditions? (e.g. asthma, diabetes, HIV). Say 'no' if none.",
            parser="text",
            required=False,
        ),
    ]


# ---------------------------------------------------------------------------
# Main intake function
# ---------------------------------------------------------------------------

def run_intake(lang: str = "pidgin", input_fn=None, output_fn=None) -> PatientContext:
    """Run the interactive clinical intake flow.

    Args:
        lang: "pidgin" or "en" — controls which prompt language to use.
        input_fn: callable that reads a line (defaults to input()).
        output_fn: callable that prints a line (defaults to print()).

    Returns:
        PatientContext with all collected information.
    """
    if input_fn is None:
        input_fn = input
    if output_fn is None:
        output_fn = print

    ctx = PatientContext()
    questions = _get_intake_questions()
    answered = 0
    max_questions = 9  # safety limit

    output_fn("")
    if lang == "pidgin":
        output_fn("  Let me ask you some questions about di patient make I fit help well well.")
    else:
        output_fn("  Let me ask some questions about the patient to give you the best advice.")
    output_fn("  (You fit say 'skip' or 'i no know' for any question wey you no get answer.)")
    output_fn("")

    for q in questions:
        if answered >= max_questions:
            break

        # Show the prompt
        prompt = q.prompt_pidgin if lang == "pidgin" else q.prompt_english
        output_fn(f"  {prompt}")

        try:
            raw = input_fn("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            break

        # Parse the answer
        parsed = _parse_answer(q, raw)

        if parsed is not None:
            _set_field(ctx, q.key, parsed)
            answered += 1
        elif q.required and not ctx.is_complete():
            # Required field with no valid answer — ask followup once
            if q.followup:
                output_fn(f"  {q.followup}")
                try:
                    raw2 = input_fn("  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    output_fn("")
                    break
                parsed2 = _parse_answer(q, raw2)
                if parsed2 is not None:
                    _set_field(ctx, q.key, parsed2)
                    answered += 1
            else:
                output_fn("  Abeg, I need this one to help you well.")
                try:
                    raw3 = input_fn("  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    output_fn("")
                    break
                parsed3 = _parse_answer(q, raw3)
                if parsed3 is not None:
                    _set_field(ctx, q.key, parsed3)
                    answered += 1

    # Show summary
    output_fn("")
    if lang == "pidgin":
        output_fn(f"  OK, I don hear. Patient info: {ctx.summary_line()}")
    else:
        output_fn(f"  OK, got it. Patient info: {ctx.summary_line()}")
    output_fn("")

    return ctx


def _parse_answer(q: IntakeQuestion, raw: str):
    """Route to the correct parser based on the question type."""
    text = raw.lower().strip()
    if text in ("skip", "i no know", "idk", "no", "i dunno", "i no know"):
        return None

    parser_name = q.parser

    if parser_name == "age":
        display, years = _parse_age(raw)
        if display:
            return (display, years)
        return None

    elif parser_name == "weight":
        kg, display = _parse_weight(raw)
        if kg:
            return (kg, display)
        return None

    elif parser_name == "gender":
        return _parse_gender(raw)

    elif parser_name == "temperature":
        return _parse_temperature(raw)

    elif parser_name == "pregnant":
        return _parse_yes_no(raw)

    elif parser_name == "text":
        # Any non-empty text is valid for free-text fields
        if raw.strip():
            return raw.strip()
        return None

    return None


def _set_field(ctx: PatientContext, key: str, value):
    """Set the appropriate field on the PatientContext."""
    if key == "age":
        ctx.age = value[0]
        ctx.age_years = value[1]
    elif key == "weight":
        ctx.weight_kg = value[0]
    elif key == "gender":
        ctx.gender = value
    elif key == "symptoms":
        ctx.symptoms = value
    elif key == "duration":
        ctx.duration = value
    elif key == "temperature":
        ctx.temperature = value
    elif key == "allergies":
        ctx.allergies = value
    elif key == "pregnant":
        ctx.pregnant = value
    elif key == "current_meds":
        ctx.current_meds = value
    elif key == "history":
        ctx.history = value


# ---------------------------------------------------------------------------
# Quick intake (non-interactive, from a single query string)
# ---------------------------------------------------------------------------

def quick_intake(query: str) -> PatientContext:
    """Extract patient info directly from a single query string.

    Used when the user types a full question instead of going through intake.
    E.g. "3 year old pikin get fever and vomit, 15kg, no allergy"
    """
    ctx = PatientContext()

    # Extract age
    display, years = _parse_age(query)
    if display:
        ctx.age = display
        ctx.age_years = years

    # Extract weight
    kg, _ = _parse_weight(query)
    if kg:
        ctx.weight_kg = kg

    # Extract gender
    g = _parse_gender(query)
    if g:
        ctx.gender = g

    # Extract temperature
    t = _parse_temperature(query)
    if t:
        ctx.temperature = t

    # The whole query is the symptoms description
    ctx.symptoms = query.strip()

    return ctx
