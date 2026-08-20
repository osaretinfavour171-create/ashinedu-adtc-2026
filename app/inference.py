"""Inference engine for PidginPharma.

Decides WHEN to ask clinical questions and WHEN to answer directly.
This is the smart layer between the user's query and the intake flow.

The engine analyzes the query and determines:
  1. Is this a clinical question that needs patient context?
  2. What info do we ALREADY have from the query?
  3. What info is MISSING that would change the answer?
  4. Which questions are ESSENTIAL vs NICE-TO-HAVE?
  5. Can we answer safely without asking anything?

Key principle: ASK LESS, NOT MORE.
  - Drug interaction queries: NO questions needed (just drug names)
  - General health info: NO questions needed
  - Symptom queries with enough context: MINIMAL questions
  - Symptom queries without context: ASK only what changes the answer

The inference engine uses a scoring system:
  - Each clinical scenario has REQUIRED fields (must have to answer safely)
  - Each field has an INFERENCE score (can we guess from the query?)
  - Questions are only asked for fields that are REQUIRED but NOT inferred

This prevents the "20 questions" problem where users get frustrated.
"""

import re
from dataclasses import dataclass
from typing import Optional

from intake import PatientContext


# ---------------------------------------------------------------------------
# Clinical scenario definitions
# ---------------------------------------------------------------------------

@dataclass
class ClinicalScenario:
    """Defines what info is needed for a specific type of clinical question."""
    name: str
    # Fields required to answer safely (must have at least these)
    required_fields: list[str]
    # Fields that significantly change the answer (worth asking)
    important_fields: list[str]
    # Fields that are nice but not critical
    optional_fields: list[str]
    # Can we answer without asking anything? (e.g. drug interactions)
    can_answer_blind: bool = False
    # Minimum confidence needed to answer without questions (0-1)
    min_confidence: float = 0.0


# Pre-defined clinical scenarios
SCENARIOS = {
    "drug_interaction": ClinicalScenario(
        name="drug_interaction",
        required_fields=[],
        important_fields=[],
        optional_fields=["current_meds"],
        can_answer_blind=True,
        min_confidence=0.9,
    ),
    "drug_dosing": ClinicalScenario(
        name="drug_dosing",
        required_fields=["age", "weight"],
        important_fields=["allergies"],
        optional_fields=["gender", "symptoms"],
        can_answer_blind=False,
        min_confidence=0.7,
    ),
    "fever_child": ClinicalScenario(
        name="fever_child",
        required_fields=["age"],
        important_fields=["weight", "temperature", "symptoms", "duration"],
        optional_fields=["allergies", "pulse", "respiratory_rate"],
        can_answer_blind=False,
        min_confidence=0.5,
    ),
    "fever_adult": ClinicalScenario(
        name="fever_adult",
        required_fields=[],
        important_fields=["temperature", "symptoms", "duration"],
        optional_fields=["allergies", "current_meds"],
        can_answer_blind=True,
        min_confidence=0.6,
    ),
    "diarrhoea": ClinicalScenario(
        name="diarrhoea",
        required_fields=["age"],
        important_fields=["weight", "duration", "symptoms"],
        optional_fields=["temperature", "allergies"],
        can_answer_blind=False,
        min_confidence=0.5,
    ),
    "respiratory": ClinicalScenario(
        name="respiratory",
        required_fields=["age"],
        important_fields=["weight", "temperature", "respiratory_rate", "spo2"],
        optional_fields=["pulse", "symptoms", "duration"],
        can_answer_blind=False,
        min_confidence=0.4,
    ),
    "pain": ClinicalScenario(
        name="pain",
        required_fields=[],
        important_fields=["age", "weight", "symptoms", "duration"],
        optional_fields=["temperature", "allergies", "current_meds"],
        can_answer_blind=True,
        min_confidence=0.6,
    ),
    "infection": ClinicalScenario(
        name="infection",
        required_fields=[],
        important_fields=["age", "weight", "symptoms", "duration"],
        optional_fields=["temperature", "allergies", "current_meds"],
        can_answer_blind=True,
        min_confidence=0.5,
    ),
    "hypertension": ClinicalScenario(
        name="hypertension",
        required_fields=[],
        important_fields=["age", "current_meds"],
        optional_fields=["weight", "symptoms"],
        can_answer_blind=True,
        min_confidence=0.7,
    ),
    "pregnancy": ClinicalScenario(
        name="pregnancy",
        required_fields=["age"],
        important_fields=["symptoms", "duration"],
        optional_fields=["current_meds", "allergies"],
        can_answer_blind=False,
        min_confidence=0.5,
    ),
    "paediatric_generic": ClinicalScenario(
        name="paediatric_generic",
        required_fields=["age", "weight"],
        important_fields=["symptoms", "temperature"],
        optional_fields=["allergies", "duration"],
        can_answer_blind=False,
        min_confidence=0.4,
    ),
    "general_health": ClinicalScenario(
        name="general_health",
        required_fields=[],
        important_fields=[],
        optional_fields=[],
        can_answer_blind=True,
        min_confidence=0.8,
    ),
}


# ---------------------------------------------------------------------------
# Scenario detection patterns
# ---------------------------------------------------------------------------

# Maps keyword patterns to scenario names
_SCENARIO_PATTERNS = {
    "drug_interaction": [
        r"\b(?:interaction|combine|mix|together|safe with|contraindicated)\b",
        r"\b(?:plus|and)\b.*\b(?:plus|and)\b",  # "A plus B and C"
    ],
    "drug_dosing": [
        r"\b(?:dose|dosage|how much|how many|mg|frequency)\b",
        r"\b(?:give|take|administer)\b.*\b(?:child|baby|pikin|infant)\b",
    ],
    "fever_child": [
        r"\b(?:fever|hot body|temperature|febrile)\b",
        r"\b(?:child|baby|pikin|infant|toddler)\b",
    ],
    "fever_adult": [
        r"\b(?:fever|hot body|temperature|febrile)\b",
    ],
    "diarrhoea": [
        r"\b(?:diarrh|run stomach|loose stool|watery stool)\b",
    ],
    "respiratory": [
        r"\b(?:breath|cough|wheeze|pneumonia|asthma|chest)\b",
        r"\b(?:no fit breathe|breathing hard|short of breath)\b",
    ],
    "pain": [
        r"\b(?:pain|ache|hurt|sore)\b",
    ],
    "infection": [
        r"\b(?:infection|wound|abscess|pus|swelling|red)\b",
    ],
    "hypertension": [
        r"\b(?:hypertension|blood pressure|bp|high bp)\b",
    ],
    "pregnancy": [
        r"\b(?:pregnant|pregnancy|antenatal|antenatal|labour|delivery)\b",
    ],
    "paediatric_generic": [
        r"\b(?:child|baby|pikin|infant|toddler|neonate)\b",
    ],
}


# ---------------------------------------------------------------------------
# Inference engine
# ---------------------------------------------------------------------------

@dataclass
class InferenceResult:
    """Result of the inference engine's analysis."""
    scenario: str              # Detected clinical scenario
    confidence: float          # How confident we are in the scenario detection (0-1)
    already_known: dict        # Fields we can infer from the query itself
    missing_required: list     # Required fields we MUST ask about
    missing_important: list    # Important fields we SHOULD ask about
    missing_optional: list     # Optional fields we could ask about
    should_ask: bool           # Whether to trigger the intake flow
    questions_to_ask: list     # Ordered list of questions to actually ask
    can_answer_blind: bool     # Can we answer without any questions?


def infer_context(query: str, normalizer=None) -> InferenceResult:
    """Analyze a query and determine what patient info is needed.

    This is the core inference logic. It:
      1. Detects the clinical scenario from the query
      2. Extracts any patient info already in the query
      3. Determines what's missing
      4. Decides whether to ask questions or answer directly
    """
    query_lower = query.lower().strip()

    # Step 1: Detect scenario
    scenario_name, confidence = _detect_scenario(query_lower)

    # Step 2: Extract info already in the query
    already_known = _extract_existing_info(query_lower)

    # Step 3: Get the scenario requirements
    scenario = SCENARIOS.get(scenario_name, SCENARIOS["general_health"])

    # Step 4: Determine what's missing
    all_needed = scenario.required_fields + scenario.important_fields + scenario.optional_fields
    missing_required = [f for f in scenario.required_fields if f not in already_known]
    missing_important = [f for f in scenario.important_fields if f not in already_known]
    missing_optional = [f for f in scenario.optional_fields if f not in already_known]

    # Step 5: Decide whether to ask
    can_answer_blind = scenario.can_answer_blind and confidence >= scenario.min_confidence
    has_enough = len(missing_required) == 0

    # Build the list of questions to actually ask
    questions_to_ask = _prioritize_questions(
        missing_required, missing_important, missing_optional,
        already_known, scenario_name
    )

    # Determine if we should trigger intake
    should_ask = (
        not can_answer_blind
        and len(questions_to_ask) > 0
        and confidence >= 0.3  # Only ask if we're somewhat sure about the scenario
    )

    return InferenceResult(
        scenario=scenario_name,
        confidence=confidence,
        already_known=already_known,
        missing_required=missing_required,
        missing_important=missing_important,
        missing_optional=missing_optional,
        should_ask=should_ask,
        questions_to_ask=questions_to_ask,
        can_answer_blind=can_answer_blind,
    )


def _detect_scenario(query: str) -> tuple[str, float]:
    """Detect the clinical scenario from the query text.

    Returns (scenario_name, confidence).
    """
    scores = {}
    for scenario_name, patterns in _SCENARIO_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 1
        if score > 0:
            scores[scenario_name] = score / len(patterns)

    if not scores:
        return "general_health", 0.5

    # Return the highest-scoring scenario
    best = max(scores, key=scores.get)
    return best, min(scores[best], 1.0)


def _extract_existing_info(query: str) -> dict:
    """Extract patient info that's already in the query string.

    Returns dict of field_name -> value.
    """
    info = {}

    # Age detection
    age_patterns = [
        (r"(\d+)\s*(?:year|yr|y)\b", lambda m: (f"{m.group(1)} years", float(m.group(1)))),
        (r"(\d+)\s*(?:month|mo)\b", lambda m: (f"{m.group(1)} months", float(m.group(1)) / 12)),
        (r"(\d+)\s*(?:day|d)\b", lambda m: (f"{m.group(1)} days", float(m.group(1)) / 365)),
        (r"\b(adult|grown|man|woman)\b", lambda m: ("adult", 30.0)),
        (r"\b(baby|babe|newborn|new born)\b", lambda m: ("newborn", 0.0)),
    ]
    for pattern, extractor in age_patterns:
        m = re.search(pattern, query)
        if m:
            display, years = extractor(m)
            info["age"] = display
            info["age_years"] = years
            break

    # Weight detection
    weight_patterns = [
        (r"(\d+(?:\.\d+)?)\s*(?:kg|kilo)", lambda m: float(m.group(1))),
        (r"(\d+(?:\.\d+)?)\s*(?:lb|pound)", lambda m: float(m.group(1)) * 0.453592),
    ]
    for pattern, extractor in weight_patterns:
        m = re.search(pattern, query)
        if m:
            w = extractor(m)
            if 1 <= w <= 200:
                info["weight_kg"] = w
                break

    # Gender detection
    if re.search(r"\b(?:male|boy|man|he|him)\b", query):
        info["gender"] = "male"
    elif re.search(r"\b(?:female|girl|woman|she|her)\b", query):
        info["gender"] = "female"

    # Temperature detection
    temp_match = re.search(r"(\d{2,3}(?:\.\d+)?)\s*°?\s*([cf])?", query)
    if temp_match:
        info["temperature"] = f"{temp_match.group(1)}°C"

    # Symptom detection (extract the symptom words)
    symptom_words = [
        "fever", "headache", "vomit", "diarrhoea", "diarrhea", "cough",
        "rash", "pain", "swelling", "bleeding", "itching", "convulsion",
        "seizure", "dizzy", "weak", "breath", "sore throat", "ear pain",
        "hot body", "run stomach", "belly pain", "chest pain", "back pain",
    ]
    found_symptoms = [s for s in symptom_words if s in query]
    if found_symptoms:
        info["symptoms"] = ", ".join(found_symptoms)

    # Duration detection
    dur_match = re.search(r"\b(?:for|since|past)\s+(\d+\s*(?:day|week|month|hour|minute)s?)", query)
    if dur_match:
        info["duration"] = dur_match.group(1)

    return info


def _prioritize_questions(missing_required: list, missing_important: list,
                          missing_optional: list, already_known: dict,
                          scenario: str) -> list[str]:
    """Prioritize which questions to ask, keeping the list short.

    Returns an ordered list of field names to ask about.
    """
    questions = []

    # Always ask required fields first
    for field in missing_required:
        questions.append(field)

    # Ask important fields if they significantly change the answer
    # Cap at 3 important questions to avoid fatigue
    for field in missing_important[:3]:
        if field not in questions:
            questions.append(field)

    # Only ask optional fields if we have very few questions so far
    if len(questions) < 3:
        for field in missing_optional[:1]:
            if field not in questions:
                questions.append(field)

    # Age is always first (most critical for dosing)
    if "age" in questions:
        questions.remove("age")
        questions.insert(0, "age")

    # Weight is second (critical for dosing)
    if "weight" in questions:
        questions.remove("weight")
        if "age" in questions:
            questions.insert(1, "weight")
        else:
            questions.insert(0, "weight")

    # Symptoms should come early
    if "symptoms" in questions:
        questions.remove("symptoms")
        pos = min(2, len(questions))
        questions.insert(pos, "symptoms")

    return questions


def build_patient_context_from_query(query: str) -> PatientContext:
    """Build a PatientContext from info already in the query string.

    Used for quick-intake when the user provides a full question.
    """
    info = _extract_existing_info(query.lower())

    ctx = PatientContext()
    if "age" in info:
        ctx.age = info["age"]
    if "age_years" in info:
        ctx.age_years = info["age_years"]
    if "weight_kg" in info:
        ctx.weight_kg = info["weight_kg"]
    if "gender" in info:
        ctx.gender = info["gender"]
    if "temperature" in info:
        ctx.temperature = info["temperature"]
    if "symptoms" in info:
        ctx.symptoms = info["symptoms"]
    else:
        ctx.symptoms = query.strip()

    return ctx


# ---------------------------------------------------------------------------
# Question prompts (Pidgin and English)
# ---------------------------------------------------------------------------

_QUESTION_PROMPTS = {
    "age": {
        "pidgin": "How old is di patient? (e.g. 3 years, 6 months, adult)",
        "english": "What is the patient's age?",
    },
    "weight": {
        "pidgin": "How heavy is di patient? (e.g. 15 kg, 70 kg). Say 'skip' if you no know.",
        "english": "What is the patient's weight? Say 'skip' if unknown.",
    },
    "gender": {
        "pidgin": "Na boy or na girl?",
        "english": "Is the patient male or female?",
    },
    "symptoms": {
        "pidgin": "Wetin dey worry di patient? Describe di symptoms.",
        "english": "What symptoms does the patient have?",
    },
    "duration": {
        "pidgin": "How long e don dey like dis?",
        "english": "How long has the patient had these symptoms?",
    },
    "temperature": {
        "pidgin": "You get thermometer? If yes, wetin e read?",
        "english": "Do you have a thermometer reading?",
    },
    "allergies": {
        "pidgin": "Di patient get any medicine wey e no fit take? Say 'no' if none.",
        "english": "Does the patient have any drug allergies?",
    },
    "pregnant": {
        "pidgin": "She fit dey pregnant?",
        "english": "Could the patient be pregnant?",
    },
    "current_meds": {
        "pidgin": "Di patient dey take any medicine now?",
        "english": "Is the patient currently on any medication?",
    },
    "history": {
        "pidgin": "Di patient get any long-term sickness?",
        "english": "Does the patient have any chronic conditions?",
    },
    "pulse": {
        "pidgin": "You fit feel im pulse? How e dey?",
        "english": "How is the patient's pulse?",
    },
    "respiratory_rate": {
        "pidgin": "How e dey breathe?",
        "english": "How is the patient breathing?",
    },
    "spo2": {
        "pidgin": "You get oxygen meter? If yes, wetin e read?",
        "english": "Do you have a pulse oximeter reading?",
    },
}


def get_question_prompt(field: str, lang: str = "pidgin") -> str:
    """Get the prompt for a specific question field."""
    prompts = _QUESTION_PROMPTS.get(field, {})
    return prompts.get(lang, prompts.get("pidgin", f"Tell me about {field}."))
