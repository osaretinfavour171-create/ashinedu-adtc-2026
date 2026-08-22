"""Clinical reasoning engine for musculoskeletal conditions.

Decides WHEN to recommend:
  - Rest / hot compress / ice
  - Massage / topical rub (diclofenac gel, capsaicin cream)
  - Oral drugs (paracetamol, ibuprofen, colchicine)
  - Referral to hospital

Based on NSTG 2022 protocols and Nigeria Essential Medicines List 2020.

Decision logic:
  1. Detect the likely condition from age + gender + symptom pattern
  2. Apply severity assessment (acute vs chronic, mild vs severe)
  3. Check for red flags (septic arthritis, fever + joint swelling)
  4. Generate a structured treatment plan with phased approach

Key principle: NON-DRUG TREATMENT FIRST, then add drugs as needed.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Condition detection patterns
# ---------------------------------------------------------------------------

# Maps keyword clusters to likely conditions
_CONDITION_PATTERNS = {
    "osteoarthritis": [
        r"\b(?:osteoarthritis|oa|degenerative|wear and tear)\b",
        r"\b(?:crepitus|creaky|stiffness)\b.*\b(?:morning|knee|hip)\b",
        r"\b(?:bouchard|heberden|genu varus|genu valgum)\b",
    ],
    "gout": [
        r"\b(?:gout|podagra|uric acid|urate)\b",
        r"\b(?:big toe|great toe|first mcp)\b.*\b(?:pain|swelling|red|hot)\b",
        r"\b(?:joint)\b.*\b(?:sudden|acute|severe)\b.*\b(?:pain|swelling)\b",
        r"\b(?:alcohol|beer|offal|seafood)\b.*\b(?:joint|pain|swelling)\b",
    ],
    "rheumatoid_arthritis": [
        r"\b(?:rheumatoid|ra|autoimmune)\b",
        r"\b(?:joint)\b.*\b(?:symmetric|both sides|bilateral)\b",
        r"\b(?:morning stiffness)\b.*\b(?:hour|long|persistent)\b",
        r"\b(?:swollen)\b.*\b(?:fingers|hands|wrists)\b.*\b(?:both|symmetric)\b",
    ],
    "septic_arthritis": [
        r"\b(?:septic|infected)\b.*\b(?:joint|arthritis)\b",
        r"\b(?:joint)\b.*\b(?:fever|hot|red|swollen)\b",
        r"\b(?:fever)\b.*\b(?:joint|knee|hip|shoulder)\b.*\b(?:pain|swelling)\b",
        r"\b(?:joint)\b.*\b(?:pus|discharge)\b",
    ],
    "mechanical_pain": [
        r"\b(?:sprain|strain|twist|fall|injury|trauma)\b",
        r"\b(?:back pain|lower back|lumbago)\b",
        r"\b(?:neck pain|cervical)\b",
        r"\b(?:shoulder pain|frozen shoulder)\b",
    ],
    "muscle_pain": [
        r"\b(?:muscle pain|myalgia|body ache|body pain)\b",
        r"\b(?:cramp|spasm|stiff)\b.*\b(?:back|neck|leg|arm)\b",
        r"\b(?:exercise|work|carry|lift)\b.*\b(?:pain|ache|sore)\b",
    ],
}


# ---------------------------------------------------------------------------
# Severity assessment
# ---------------------------------------------------------------------------

@dataclass
class SeverityAssessment:
    """Assessment of how severe a musculoskeletal problem is."""
    level: str = "mild"       # "mild", "moderate", "severe", "emergency"
    acute: bool = False       # Sudden onset vs chronic
    duration_weeks: float = 0
    has_fever: bool = False
    has_swelling: bool = False
    has_redness: bool = False
    multiple_joints: bool = False
    functional_impairment: bool = False


def _assess_severity(symptoms: str, age_years: Optional[float],
                     temperature: Optional[str] = None) -> SeverityAssessment:
    """Assess severity from symptoms and vitals."""
    s = symptoms.lower()
    assess = SeverityAssessment()

    # Duration detection
    dur_match = re.search(r"(\d+)\s*(day|week|month|hour|minute)", s)
    if dur_match:
        val = int(dur_match.group(1))
        unit = dur_match.group(2)
        if unit == "week":
            assess.duration_weeks = val
        elif unit == "month":
            assess.duration_weeks = val * 4
        elif unit == "day":
            assess.duration_weeks = val / 7
        elif unit == "hour":
            assess.duration_weeks = val / 168
            assess.acute = True
    else:
        # Check for acute indicators
        if any(w in s for w in ("sudden", "acute", "just started", "today", "yesterday")):
            assess.acute = True

    # Fever detection
    if temperature:
        m = re.search(r"(\d{2,3}(?:\.\d+)?)", temperature)
        if m and float(m.group(1)) >= 37.5:
            assess.has_fever = True
    if any(w in s for w in ("fever", "hot body", "temperature", "febrile")):
        assess.has_fever = True

    # Swelling
    if any(w in s for w in ("swelling", "swollen", "swell", "puffy", "inflamed")):
        assess.has_swelling = True

    # Redness
    if any(w in s for w in ("red", "redness", "inflamed", "angry")):
        assess.has_redness = True

    # Multiple joints
    if any(w in s for w in ("joints", "both", "bilateral", "symmetric",
                             "multiple", "all over")):
        assess.multiple_joints = True

    # Functional impairment
    if any(w in s for w in ("can't walk", "cant walk", "can't move", "cant move",
                             "difficulty walking", "limping", "stiff",
                             "can't bend", "cant bend")):
        assess.functional_impairment = True

    # Determine severity level
    if assess.has_fever and assess.has_swelling:
        assess.level = "emergency"  # Possible septic arthritis
    elif assess.functional_impairment and assess.has_swelling:
        assess.level = "severe"
    elif assess.has_swelling or (assess.acute and assess.has_redness):
        assess.level = "moderate"
    else:
        assess.level = "mild"

    return assess


# ---------------------------------------------------------------------------
# Treatment recommendation
# ---------------------------------------------------------------------------

@dataclass
class TreatmentAdvice:
    """Structured treatment recommendation for a musculoskeletal condition."""
    condition: str               # Likely condition name
    confidence: float            # How confident we are (0-1)
    severity: str                # "mild", "moderate", "severe", "emergency"
    condition_name_en: str       # English name for display
    condition_name_pidgin: str   # Pidgin name for display

    # Non-drug treatments (always recommended first)
    rest_advice: str = ""
    compress_advice: str = ""    # Hot or ice
    exercise_advice: str = ""
    lifestyle_advice: str = ""

    # Topical treatments
    topical_drugs: list = field(default_factory=list)  # [(drug, instructions)]

    # Oral drugs
    oral_drugs: list = field(default_factory=list)     # [(drug, dose_info)]

    # Red flags
    red_flags: list = field(default_factory=list)      # [flag_description]

    # Referral
    refer: bool = False
    referral_reason: str = ""

    def format_pidgin(self) -> str:
        """Format advice in Nigerian Pidgin."""
        return self._format("pidgin")

    def format_english(self) -> str:
        """Format advice in standard English."""
        return self._format("en")

    def _format(self, lang: str) -> str:
        lines = []

        # Header
        if lang == "pidgin":
            lines.append(f"ASSESSMENT: {self.condition_name_pidgin}")
            if self.severity:
                sev_map = {"mild": "Mild (no too serious)",
                           "moderate": "Moderate (need treatment)",
                           "severe": "Severe (need strong treatment)",
                           "emergency": "EMERGENCY (send to hospital NOW)"}
                lines.append(f"Severity: {sev_map.get(self.severity, self.severity)}")
        else:
            lines.append(f"ASSESSMENT: {self.condition_name_en}")
            if self.severity:
                lines.append(f"Severity: {self.severity.upper()}")

        lines.append("")

        # Red flags first
        if self.red_flags:
            if lang == "pidgin":
                lines.append("RED FLAGS:")
            else:
                lines.append("RED FLAGS:")
            for flag in self.red_flags:
                lines.append(f"  - {flag}")
            lines.append("")

        # Referral
        if self.refer:
            if lang == "pidgin":
                lines.append(f"REFER TO HOSPITAL: {self.referral_reason}")
            else:
                lines.append(f"REFER TO HOSPITAL: {self.referral_reason}")
            lines.append("")

        # Non-drug treatment
        if self.rest_advice or self.compress_advice or self.exercise_advice or self.lifestyle_advice:
            if lang == "pidgin":
                lines.append("NON-DRUG TREATMENT (try this first):")
            else:
                lines.append("NON-PHARMACOLOGICAL MANAGEMENT:")
            if self.rest_advice:
                lines.append(f"  Rest: {self.rest_advice}")
            if self.compress_advice:
                lines.append(f"  Compress: {self.compress_advice}")
            if self.exercise_advice:
                lines.append(f"  Exercise: {self.exercise_advice}")
            if self.lifestyle_advice:
                lines.append(f"  Lifestyle: {self.lifestyle_advice}")
            lines.append("")

        # Topical drugs
        if self.topical_drugs:
            if lang == "pidgin":
                lines.append("TOPICAL (rub/cream for di joint):")
            else:
                lines.append("TOPICAL TREATMENT:")
            for drug, instructions in self.topical_drugs:
                lines.append(f"  - {drug}: {instructions}")
            lines.append("")

        # Oral drugs
        if self.oral_drugs:
            if lang == "pidgin":
                lines.append("ORAL MEDICINE:")
            else:
                lines.append("ORAL MEDICATION:")
            for drug, dose_info in self.oral_drugs:
                lines.append(f"  - {drug}: {dose_info}")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main clinical reasoning function
# ---------------------------------------------------------------------------

def assess_musculoskeletal(
    symptoms: str,
    age_years: Optional[float] = None,
    weight_kg: Optional[float] = None,
    gender: Optional[str] = None,
    temperature: Optional[str] = None,
    duration: Optional[str] = None,
    history: Optional[str] = None,
    lang: str = "pidgin",
) -> TreatmentAdvice:
    """Main entry point: assess a musculoskeletal complaint and return treatment advice.

    Args:
        symptoms: Description of the patient's symptoms.
        age_years: Patient age in years.
        weight_kg: Patient weight in kg.
        gender: "male" or "female".
        temperature: Temperature string like "38.5°C".
        duration: Duration string like "3 days".
        history: Medical history string.
        lang: "pidgin" or "en" for output language.

    Returns:
        TreatmentAdvice with structured recommendations.
    """
    age = age_years if age_years is not None else 30.0
    symptoms_lower = symptoms.lower()
    full_text = f"{symptoms} {duration or ''} {temperature or ''}".lower()

    # Step 1: Detect likely condition
    condition, confidence = _detect_condition(full_text, age, temperature)

    # Step 2: Assess severity
    severity = _assess_severity(symptoms, age, temperature)

    # Step 3: Generate treatment plan
    advice = _generate_treatment(
        condition, confidence, severity, age, weight_kg, gender,
        symptoms_lower, history, lang
    )

    return advice


def _detect_condition(text: str, age: float = 30.0,
                     temperature: Optional[str] = None) -> tuple[str, float]:
    """Detect the likely musculoskeletal condition from symptoms + patient context."""
    scores = {}
    for condition, patterns in _CONDITION_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1
        if score > 0:
            scores[condition] = score / len(patterns)

    # Age-based boosts: elderly + joint pain = likely OA
    joint_words = ["joint", "knee", "hip", "ankle", "shoulder", "elbow", "wrist"]
    pain_words = ["pain", "ache", "dey pain", "dey ache", "hurt", "sore", "stiff"]
    age_words = ["old", "elderly", "aging", "aged", "years"]
    has_joint = any(w in text for w in joint_words)
    has_pain = any(w in text for w in pain_words)
    has_age = any(w in text for w in age_words)
    # Nigerian context: "mama/papa" + "knee/hip" = likely elderly OA
    has_mama_papa = any(w in text for w in ("mama", "papa", "mama leg", "papa leg",
                                             "mama knee", "papa knee", "old woman", "old man"))
    if age >= 55 and has_joint and has_pain:
        scores["osteoarthritis"] = scores.get("osteoarthritis", 0) + 0.3
    if age >= 55 and has_joint and has_pain and (has_age or has_mama_papa):
        scores["osteoarthritis"] = scores.get("osteoarthritis", 0) + 0.2

    # Male 40+ with acute joint pain = likely gout
    if age >= 40 and any(kw in text for kw in ("sudden", "acute", "big toe", "toe")):
        scores["gout"] = scores.get("gout", 0) + 0.2

    # Fever + joint swelling = septic arthritis (override)
    has_fever = False
    if temperature:
        m = re.search(r"(\d{2,3}(?:\.\d+)?)", temperature)
        if m and float(m.group(1)) >= 37.5:
            has_fever = True
    if any(w in text for w in ("fever", "hot body", "temperature")):
        has_fever = True
    if has_fever and any(w in text for w in ("swollen", "swelling", "hot", "red")):
        scores["septic_arthritis"] = max(scores.get("septic_arthritis", 0), 0.8)

    if not scores:
        return "mechanical_pain", 0.3  # Default to generic musculoskeletal

    best = max(scores, key=scores.get)
    return best, min(scores[best], 1.0)


def _generate_treatment(
    condition: str,
    confidence: float,
    severity: SeverityAssessment,
    age: float,
    weight_kg: Optional[float],
    gender: Optional[str],
    symptoms: str,
    history: Optional[str],
    lang: str,
) -> TreatmentAdvice:
    """Generate a structured treatment plan based on condition and severity."""

    # Condition display names
    CONDITION_NAMES = {
        "osteoarthritis": ("Osteoarthritis", "Knee/hip pain from old age (wear and tear)"),
        "gout": ("Gout", "Gout (crystal in di joint)"),
        "rheumatoid_arthritis": ("Rheumatoid Arthritis", "Joint pain from body fighting itself (RA)"),
        "septic_arthritis": ("Septic Arthritis", "INFECTED JOINT (very dangerous)"),
        "mechanical_pain": ("Mechanical/Musculoskeletal Pain", "Body pain from strain or injury"),
        "muscle_pain": ("Muscle Pain", "Muscle pain (myalgia)"),
    }

    cond_en, cond_pid = CONDITION_NAMES.get(condition, ("Musculoskeletal Pain", "Body pain"))
    advice = TreatmentAdvice(
        condition=condition,
        confidence=confidence,
        severity=severity.level,
        condition_name_en=cond_en,
        condition_name_pidgin=cond_pid,
    )

    # ---- RED FLAGS: Septic arthritis or emergency ----
    if condition == "septic_arthritis" or severity.level == "emergency":
        advice.refer = True
        advice.referral_reason = ("Fever + joint swelling = possible septic arthritis. "
                                  "REFER TO HOSPITAL IMMEDIATELY for joint aspiration and IV antibiotics.")
        advice.red_flags.append(
            "Fever with swollen, hot joint may indicate infection inside the joint."
        )
        advice.rest_advice = "Keep the joint at rest. Do not move it unnecessarily."
        advice.oral_drugs.append(
            ("Paracetamol", "For pain relief while waiting for hospital referral.")
        )
        return advice

    # ---- GOUT ----
    if condition == "gout":
        advice.rest_advice = "Rest the affected joint completely. Do not put weight on it."
        if severity.acute:
            advice.compress_advice = "Apply ICE (cold compress) for 15-20 minutes every hour. Do NOT use heat."
        else:
            advice.compress_advice = "Apply ice during flares. Warm compress between flares."

        # Dietary advice
        advice.lifestyle_advice = (
            "Avoid alcohol (especially beer), red meat, offal, seafood, and sugary drinks. "
            "Drink plenty of water (2-3 litres daily)."
        )

        if severity.level in ("moderate", "severe"):
            advice.topical_drugs.append(
                ("Diclofenac gel", "Apply thin layer to affected joint 3-4 times daily.")
            )
            if age >= 18:
                advice.oral_drugs.append(
                    ("Ibuprofen 400mg", "Take 400mg every 8 hours with food. Max 1200mg/day OTC.")
                )
                if severity.level == "severe":
                    advice.oral_drugs.append(
                        ("Colchicine", "0.5mg every 1-2 hours until pain eases (max 6mg on day 1). "
                         "Then 0.5mg BID for 1-2 weeks.")
                    )
            else:
                advice.oral_drugs.append(
                    ("Paracetamol", "10-15 mg/kg every 4-6 hours. Max 60 mg/kg/day.")
                )
                advice.red_flags.append(
                    "Gout in a young person is unusual - consider REFER for further investigation."
                )

        elif severity.level == "mild":
            advice.topical_drugs.append(
                ("Menthol rub or Diclofenac gel", "Apply to painful area for relief.")
            )
            advice.oral_drugs.append(
                ("Paracetamol", "10-15 mg/kg every 4-6 hours for pain relief.")
            )

        # Chronic gout management
        if age >= 18 and severity.duration_weeks > 4:
            advice.lifestyle_advice += " For long-term management, Allopurinol (100mg daily) can reduce uric acid. Start after flare settles."
            advice.red_flags.append(
                "Chronic gout needs specialist review for urate-lowering therapy."
            )

        return advice

    # ---- OSTEOARTHRITIS ----
    if condition == "osteoarthritis":
        advice.rest_advice = (
            "Avoid prolonged standing, climbing stairs, or heavy lifting. "
            "Use a walking stick or cane if needed."
        )
        advice.compress_advice = (
            "Hot compress for stiffness (especially morning). "
            "Ice for acute flare-ups with swelling."
        )
        advice.exercise_advice = (
            "Gentle exercise: walking, swimming, or cycling. "
            "Strengthen quadriceps muscles. Avoid jogging if knee is affected."
        )
        advice.lifestyle_advice = (
            "Weight loss if overweight - even 5kg reduction eases knee pain significantly."
        )

        if severity.level == "mild":
            advice.topical_drugs.append(
                ("Diclofenac gel", "Apply thin layer to affected joint 3-4 times daily.")
            )
            advice.topical_drugs.append(
                ("Menthol rub", "Apply for temporary pain relief.")
            )
            advice.oral_drugs.append(
                ("Paracetamol", "10-15 mg/kg every 4-6 hours (max 4g/day for adults). "
                 "First-line for OA pain.")
            )

        elif severity.level == "moderate":
            advice.topical_drugs.append(
                ("Diclofenac gel", "Apply thin layer to affected joint 3-4 times daily.")
            )
            advice.topical_drugs.append(
                ("Capsaicin cream", "Apply to affected joint 3-4 times daily. "
                 "Takes 1-2 weeks for full effect.")
            )
            advice.oral_drugs.append(
                ("Paracetamol", "10-15 mg/kg every 4-6 hours. Max 4g/day.")
            )
            if age >= 12 and age < 65:
                advice.oral_drugs.append(
                    ("Ibuprofen", "Take with food. Max 1200mg/day OTC. "
                     "Avoid if history of stomach ulcer.")
                )

        elif severity.level == "severe":
            advice.topical_drugs.append(
                ("Diclofenac gel", "Apply 4-5 times daily to affected joint.")
            )
            advice.oral_drugs.append(
                ("Paracetamol", "10-15 mg/kg every 4-6 hours. Max 4g/day.")
            )
            if age >= 12 and age < 65:
                advice.oral_drugs.append(
                    ("Ibuprofen", "Take with food. Use with caution if stomach issues.")
                )
            advice.red_flags.append(
                "Severe OA with functional impairment - REFER for orthopaedic review. "
                "Surgery (joint replacement) may be needed."
            )

        # Elderly-specific advice
        if age >= 60:
            advice.red_flags.append(
                "Elderly patient: Monitor for NSAID side effects (stomach bleeding, kidney issues). "
                "Paracetamol is safest first choice."
            )

        return advice

    # ---- RHEUMATOID ARTHRITIS ----
    if condition == "rheumatoid_arthritis":
        advice.rest_advice = (
            "During flares: rest affected joints. "
            "Between flares: gentle range-of-motion exercises to prevent stiffness."
        )
        advice.compress_advice = "Warm compress for stiffness. Ice for acute swelling."
        advice.exercise_advice = (
            "Gentle exercises: hand exercises, range-of-motion, light walking. "
            "Occupational therapy for hand function."
        )
        advice.lifestyle_advice = (
            "RA needs specialist management (rheumatologist). "
            "Disease-modifying drugs (DMARDs) are essential but must be prescribed by a specialist."
        )

        advice.topical_drugs.append(
            ("Diclofenac gel", "Apply to swollen joints for local relief.")
        )
        advice.oral_drugs.append(
            ("Paracetamol", "For pain relief. 10-15 mg/kg every 4-6 hours.")
        )
        advice.red_flags.append(
            "RA requires specialist care. REFER to rheumatologist for DMARD therapy "
            "(Methotrexate, Sulfasalazine, Hydroxychloroquine)."
        )
        advice.refer = True
        advice.referral_reason = (
            "RA is a systemic autoimmune disease requiring specialist management "
            "with DMARDs. Refer for rheumatology review."
        )
        return advice

    # ---- MECHANICAL / MUSCLE PAIN (default) ----
    advice.rest_advice = (
        "Rest the affected area. Avoid activities that worsen the pain."
    )
    advice.compress_advice = (
        "Ice for the first 48 hours (15-20 min every 2-3 hours). "
        "After 48 hours, switch to warm compress."
    )
    advice.lifestyle_advice = (
        "Gentle stretching. Maintain good posture. "
        "Avoid sitting in one position for too long."
    )

    if severity.level in ("mild", "moderate"):
        advice.topical_drugs.append(
            ("Menthol rub or Diclofenac gel", "Apply to painful area for relief.")
        )
        if severity.level == "moderate":
            advice.topical_drugs.append(
                ("Capsaicin cream", "Apply to affected area for deeper pain relief.")
            )
        advice.oral_drugs.append(
            ("Paracetamol", "10-15 mg/kg every 4-6 hours. Max 4g/day for adults.")
        )
        if age >= 12 and age < 65 and severity.level == "moderate":
            advice.oral_drugs.append(
                ("Ibuprofen", "Take with food. Max 1200mg/day OTC.")
            )

    elif severity.level == "severe":
        advice.topical_drugs.append(
            ("Diclofenac gel", "Apply liberally 4-5 times daily.")
        )
        advice.oral_drugs.append(
            ("Paracetamol", "10-15 mg/kg every 4-6 hours.")
        )
        if age >= 12 and age < 65:
            advice.oral_drugs.append(
                ("Ibuprofen", "400mg every 8 hours with food. Max 1200mg/day.")
            )
        advice.red_flags.append(
            "Severe pain not responding to treatment - REFER for further assessment."
        )

    # Muscle pain specific
    if condition == "muscle_pain":
        advice.lifestyle_advice = (
            "Gentle stretching. Warm bath. "
            "Avoid strenuous activity until pain settles. "
            "Dehydration can worsen muscle cramps - ensure adequate fluid intake."
        )

    return advice


def is_musculoskeletal_query(query: str) -> bool:
    """Quick check if a query is about musculoskeletal/joint issues."""
    q = query.lower()
    ms_keywords = [
        "joint", "arthritis", "knee", "hip", "shoulder", "elbow", "wrist",
        "ankle", "back pain", "neck pain", "muscle", "sprain", "strain",
        "stiff", "crepitus", "gout", "rheumatoid", "osteoarthritis",
        "bone", "spine", "lumbar", "cervical", "frozen shoulder",
        "body pain", "body ache", "dey pain", "pain dey",
        "rub", "massage", "compress", "cream for pain",
    ]
    return any(kw in q for kw in ms_keywords)
