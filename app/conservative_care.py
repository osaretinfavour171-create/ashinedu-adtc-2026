"""Conservative care engine for simple, self-limiting conditions.

The RIGHT answer for many conditions is NOT drugs — it's:
  - Rest
  - Drink water / ORS
  - Monitor for red flags
  - Time (the body heals itself)

This module detects when conservative management is appropriate and
generates structured non-drug advice. It catches conditions like:
  - Common cold / upper respiratory infection
  - Mild dehydration
  - Stress / tension
  - Fatigue / tiredness
  - Heat exhaustion
  - Mild stomach upset
  - Simple headache (non-specific)
  - Body aches from overwork
  - Mild allergic reaction (no anaphylaxis)

Key principle: DO NO HARM. When drugs are not needed, don't prescribe them.
Every drug has side effects — if rest and water will fix it, that's better.

Decision logic:
  1. Detect if this is a conservative-care condition
  2. Check for red flags that would escalate to drug treatment or referral
  3. Generate specific, actionable non-drug advice
  4. Add paracetamol ONLY if fever is present
  5. Add ORS ONLY if dehydration signs are present
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Condition detection
# ---------------------------------------------------------------------------

# Pattern clusters for conditions that usually DON'T need drugs
_CONSERVATIVE_PATTERNS = {
    "common_cold": {
        "patterns": [
            r"\b(?:cold|coryza|runny nose|sneez|sniffle|stuffy nose|blocked nose)\b",
            r"\b(?:sore throat|scratchy throat|mild cough)\b",
            r"\b(?:mild fever|low grade|temperature)\b.*\b(?:cold|sneez|runny)\b",
        ],
        "pidgin_names": ["cold", "catarrh", "running nose", "sneezing"],
        "en_names": ["common cold", "upper respiratory infection", "coryza"],
    },
    "stress_tension": {
        "patterns": [
            r"\b(?:stress|tired|exhaust|burnout|overwork|too much work)\b",
            r"\b(?:tension|anxiety|worried|worry|pressure)\b",
            r"\b(?:headache|head dey pain)\b.*\b(?:stress|tired|work|pressure)\b",
            r"\b(?:no sleep|sleepless|insomnia|can't sleep|no fit sleep)\b",
        ],
        "pidgin_names": ["stress", "tiredness", "body dey tired", "no get strength"],
        "en_names": ["stress", "tension", "fatigue", "burnout"],
    },
    "mild_dehydration": {
        "patterns": [
            r"\b(?:thirsty|dehydrat|dry mouth|no drink|not drink)\b",
            r"\b(?:dark urine| concentrated urine|no urine)\b",
            r"\b(?:mild dehydration|small dehydration)\b",
            r"\b(?:diarrhoea|vomit)\b.*\b(?:mild|small|little)\b",
        ],
        "pidgin_names": ["thirsty", "body dey dry", "no drink water"],
        "en_names": ["mild dehydration", "thirst"],
    },
    "heat_exhaustion": {
        "patterns": [
            r"\b(?:heat|sun|hot weather|sunstroke|heat stroke)\b",
            r"\b(?:dizzy|dizziness|faint|weak)\b.*\b(?:sun|heat|hot)\b",
            r"\b(?:sweating|sweat)\b.*\b(?:hot|sun|heat)\b",
            r"\b(?:exposed|working)\b.*\b(?:sun|heat|hot)\b.*\b(?:dizzy|weak|faint)\b",
        ],
        "pidgin_names": ["sun dey beat me", "hot sun", "heat"],
        "en_names": ["heat exhaustion", "heat stress", "sun exposure"],
    },
    "mild_stomach_upset": {
        "patterns": [
            r"\b(?:stomach|belly|tummy)\b.*\b(?:upset|mild|small|little)\b",
            r"\b(?:bloating|bloat|gas|flatulence)\b",
            r"\b(?:heartburn|acid|reflux)\b",
            r"\b(?:overeat|eat too much|chop too much)\b",
        ],
        "pidgin_names": ["belly dey upset", "stomach dey run small", "gas"],
        "en_names": ["mild gastritis", "indigestion", "bloating"],
    },
    "simple_headache": {
        "patterns": [
            r"\b(?:headache|head dey pain|mild headache)\b",
            r"\b(?:head)\b.*\b(?:pain|ache|hurt)\b",
        ],
        "pidgin_names": ["head dey pain", "headache"],
        "en_names": ["headache", "cephalalgia"],
        # Only conservative if NO red flags (see red flag check below)
    },
    "muscle_soreness": {
        "patterns": [
            r"\b(?:sore|aching|stiff)\b.*\b(?:muscle|body)\b",
            r"\b(?:exercise|workout|carry|lift|labour|work)\b.*\b(?:sore|pain|ache|stiff)\b",
            r"\b(?:body dey pain|body dey stiff)\b",
        ],
        "pidgin_names": ["body dey pain", "muscle dey pain", "body dey stiff"],
        "en_names": ["muscle soreness", "myalgia", "delayed onset muscle soreness"],
    },
    "fatigue_weakness": {
        "patterns": [
            r"\b(?:tired|weak|no strength|exhaust|fatigue|lethargic)\b",
            r"\b(?:no get strength|body dey weak|dey tire)\b",
            r"\b(?:sleepy|drowsy|no energy)\b",
        ],
        "pidgin_names": ["body dey weak", "no get strength", "dey tire"],
        "en_names": ["fatigue", "weakness", "malaise"],
    },
    "minor_allergy": {
        "patterns": [
            r"\b(?:allerg|itchy|itch|rash|sneez)\b",
            r"\b(?:skin dey itch|body dey itch)\b",
            r"\b(?:hay fever|seasonal allergy|dust)\b",
        ],
        "pidgin_names": ["body dey itch", "skin dey itch", "allergy"],
        "en_names": ["allergic rhinitis", "urticaria", "mild allergy"],
    },
}


# ---------------------------------------------------------------------------
# Red flag detection (escalates conservative care to drug treatment/referral)
# ---------------------------------------------------------------------------

# Symptoms that mean this is NOT a simple condition
_RED_FLAGS = {
    "fever_high": {
        "patterns": [r"\b(?:fever|temperature|hot body)\b.*\b(?:high|severe|very)\b",
                     r"\b(?:4[0-9](?:\.\d+)?)\b"],  # temp >= 40
        "message_pidgin": "High fever (>39C) - this no be ordinary cold. Give paracetamol and monitor.",
        "message_en": "High fever (>39°C) - not a simple cold. Give paracetamol and monitor closely.",
        "action": "add_paracetamol",
    },
    "difficulty_breathing": {
        "patterns": [r"\b(?:difficulty breathing|can't breathe|breathing hard|short of breath|wheeze|asthma)\b",
                     r"\b(?:no fit breathe|breathing dey hard)\b"],
        "message_pidgin": "Difficulty breathing - REFER to hospital. This may be pneumonia or asthma attack.",
        "message_en": "Difficulty breathing - REFER to hospital. Possible pneumonia or asthma exacerbation.",
        "action": "refer",
    },
    "persistent_vomiting": {
        "patterns": [r"\b(?:vomit)\b.*\b(?:blood|bloody|red|dark|coffee)\b",
                     r"\b(?:persistent|continuous|constant)\b.*\b(?:vomit)\b",
                     r"\b(?:can't keep|cannot keep|no fit keep)\b.*\b(?:water|food|anything)\b"],
        "message_pidgin": "Bloody vomit or can't keep anything down - REFER IMMEDIATELY.",
        "message_en": "Haematemesis or intractable vomiting - REFER IMMEDIATELY.",
        "action": "refer",
    },
    "severe_pain": {
        "patterns": [r"\b(?:severe|terrible|worst|unbearable)\b.*\b(?:pain|ache|headache)\b",
                     r"\b(?:pain)\b.*\b(?:severe|worst)\b"],
        "message_pidgin": "Severe pain - may need proper examination. Give paracetamol and refer if no improve.",
        "message_en": "Severe pain - requires clinical examination. Give paracetamol and refer if no improvement.",
        "action": "add_paracetamol_and_monitor",
    },
    "neck_stiffness": {
        "patterns": [r"\b(?:stiff neck|neck stiffness|can't move neck|neck dey stiff)\b"],
        "message_pidgin": "Stiff neck with headache = possible meningitis. REFER IMMEDIATELY.",
        "message_en": "Neck stiffness with headache = possible meningitis. REFER IMMEDIATELY.",
        "action": "refer",
    },
    "confusion": {
        "patterns": [r"\b(?:confus|disorient|not making sense|talking nonsense)\b",
                     r"\b(?:dey confuse|no dey know wetin e dey talk)\b"],
        "message_pidgin": "Confusion - REFER to hospital. Could be many serious things.",
        "message_en": "Confusion - REFER to hospital. Requires urgent evaluation.",
        "action": "refer",
    },
    "rash_spreading": {
        "patterns": [r"\b(?:rash)\b.*\b(?:spreading|all over|everywhere|worse)\b",
                     r"\b(?:purple|dark)\b.*\b(?:spots|rash|bruise)\b"],
        "message_pidgin": "Spreading rash or purple spots - REFER IMMEDIATELY (could be meningitis).",
        "message_en": "Spreading purpuric rash - REFER IMMEDIATELY (possible meningococcal disease).",
        "action": "refer",
    },
    "children_under_5_fever": {
        "patterns": [r"\b(?:child|baby|pikin|infant|toddler)\b"],
        "message_pidgin": "Fever in a young child needs careful monitoring. Give paracetamol. If child is lethargic or not eating, REFER.",
        "message_en": "Fever in a young child requires careful monitoring. Give paracetamol. Refer if lethargic or not feeding.",
        "action": "add_paracetamol_and_monitor",
        "age_max": 5,  # Only applies to children under 5
    },
    "elderly_fall": {
        "patterns": [r"\b(?:fall|fell|tripped|collapsed)\b"],
        "message_pidgin": "Elderly person who fell - REFER for X-ray (possible fracture).",
        "message_en": "Fall in elderly patient - REFER for imaging (possible fracture).",
        "action": "refer",
        "age_min": 65,
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ConservativeAdvice:
    """Advice for a condition that doesn't need drugs."""
    condition: str               # Detected condition name
    condition_name_en: str
    condition_name_pidgin: str
    confidence: float

    # Core non-drug advice
    rest_advice: str = ""
    fluid_advice: str = ""
    diet_advice: str = ""
    environment_advice: str = ""
    monitoring_advice: str = ""

    # Optional additions (only if red flags trigger them)
    add_paracetamol: bool = False
    add_ors: bool = False
    add_antihistamine: bool = False  # for allergies

    # Red flags detected
    red_flags: list = field(default_factory=list)
    refer: bool = False
    referral_reason: str = ""

    def format_pidgin(self) -> str:
        return self._format("pidgin")

    def format_english(self) -> str:
        return self._format("en")

    def _format(self, lang: str) -> str:
        lines = []

        # Header
        if lang == "pidgin":
            lines.append(f"ASSESSMENT: {self.condition_name_pidgin}")
            lines.append("(This one no need strong medicine. Body fit handle am with rest and water.)")
        else:
            lines.append(f"ASSESSMENT: {self.condition_name_en}")
            lines.append("(This condition typically resolves without medication.)")

        lines.append("")

        # Red flags first
        if self.red_flags:
            lines.append("WATCH OUT FOR:")
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

        # Non-drug advice
        if lang == "pidgin":
            lines.append("WHAT TO DO:")
        else:
            lines.append("MANAGEMENT:")

        if self.rest_advice:
            lines.append(f"  Rest: {self.rest_advice}")
        if self.fluid_advice:
            lines.append(f"  Fluids: {self.fluid_advice}")
        if self.diet_advice:
            lines.append(f"  Food: {self.diet_advice}")
        if self.environment_advice:
            lines.append(f"  Environment: {self.environment_advice}")
        if self.monitoring_advice:
            lines.append(f"  Watch for: {self.monitoring_advice}")

        lines.append("")

        # Drug additions (only if triggered by red flags)
        if self.add_paracetamol:
            if lang == "pidgin":
                lines.append("MEDICINE (only if e dey pain or body dey hot):")
                lines.append("  Paracetamol: 10-15 mg/kg every 4-6 hours. Max 4g/day for adults.")
            else:
                lines.append("MEDICATION (only if painful or febrile):")
                lines.append("  Paracetamol: 10-15 mg/kg every 4-6 hours. Max 4g/day for adults.")
            lines.append("")

        if self.add_ors:
            if lang == "pidgin":
                lines.append("HYDRATION:")
                lines.append("  Mix 1 ORS sachet in 1 litre clean water. Drink small small throughout di day.")
            else:
                lines.append("HYDRATION:")
                lines.append("  Mix 1 ORS sachet in 1 litre clean water. Sip throughout the day.")
            lines.append("")

        if self.add_antihistamine:
            if lang == "pidgin":
                lines.append("ALLERGY MEDICINE:")
                lines.append("  Cetirizine 10mg once daily OR Chlorpheniramine 4mg every 8 hours.")
            else:
                lines.append("ANTIHISTAMINE:")
                lines.append("  Cetirizine 10mg once daily OR Chlorpheniramine 4mg every 8 hours.")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def assess_conservative(
    symptoms: str,
    age_years: Optional[float] = None,
    temperature: Optional[str] = None,
    duration: Optional[str] = None,
    lang: str = "pidgin",
) -> Optional[ConservativeAdvice]:
    """Assess if a condition can be managed conservatively (no drugs needed).

    Returns ConservativeAdvice if this is a conservative-care condition,
    or None if the condition needs drugs/ referral (let clinical_engine handle it).
    """
    age = age_years if age_years is not None else 30.0
    text = f"{symptoms} {duration or ''} {temperature or ''}".lower()

    # Step 1: Detect condition
    condition, confidence, cond_info = _detect_condition(text)

    if condition is None:
        return None  # Not a conservative-care condition

    # Step 2: Check for red flags
    red_flags, actions = _check_red_flags(text, age)

    # Step 3: Generate advice
    advice = _build_advice(condition, cond_info, confidence, red_flags, actions, age, lang)

    return advice


def is_conservative_condition(symptoms: str) -> bool:
    """Quick check: is this a condition where rest/water is usually enough?"""
    text = symptoms.lower()
    for cond_key, cond_info in _CONSERVATIVE_PATTERNS.items():
        for pattern in cond_info["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return True
    return False


# ---------------------------------------------------------------------------
# Internal functions
# ---------------------------------------------------------------------------

def _detect_condition(text: str) -> tuple[Optional[str], float, dict]:
    """Detect the likely conservative-care condition."""
    scores = {}
    for cond_key, cond_info in _CONSERVATIVE_PATTERNS.items():
        score = 0
        for pattern in cond_info["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1
        if score > 0:
            scores[cond_key] = score / len(cond_info["patterns"])

    if not scores:
        return None, 0.0, {}

    best = max(scores, key=scores.get)
    return best, min(scores[best], 1.0), _CONSERVATIVE_PATTERNS[best]


def _check_red_flags(text: str, age: float) -> tuple[list, dict]:
    """Check for red flags that would escalate conservative care."""
    flags = []
    actions = {}

    for flag_key, flag_info in _RED_FLAGS.items():
        # Check age constraints
        if "age_max" in flag_info and age >= flag_info["age_max"]:
            continue
        if "age_min" in flag_info and age < flag_info["age_min"]:
            continue

        for pattern in flag_info["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(flag_info["message_pidgin"])  # Always Pidgin for now
                actions[flag_info["action"]] = True
                break

    return flags, actions


def _build_advice(
    condition: str,
    cond_info: dict,
    confidence: float,
    red_flags: list,
    actions: dict,
    age: float,
    lang: str,
) -> ConservativeAdvice:
    """Build structured conservative care advice."""

    # Get condition names
    pidgin_name = cond_info.get("pidgin_names", ["condition"])[0]
    en_name = cond_info.get("en_names", ["condition"])[0]

    advice = ConservativeAdvice(
        condition=condition,
        condition_name_en=en_name,
        condition_name_pidgin=pidgin_name,
        confidence=confidence,
    )

    advice.red_flags = red_flags

    # Check if we need to refer
    if actions.get("refer"):
        advice.refer = True
        advice.referral_reason = red_flags[-1] if red_flags else "Condition requires hospital evaluation."

    # Condition-specific advice
    if condition == "common_cold":
        advice.rest_advice = (
            "Rest for 2-3 days. Your body is fighting the virus. "
            "Sleep well and avoid strenuous activity."
        ) if lang == "en" else (
            "Rest for 2-3 days. Your body dey fight di virus. "
            "Sleep well and avoid heavy work."
        )
        advice.fluid_advice = (
            "Drink plenty of warm water, warm lemon with honey, or herbal tea. "
            "At least 8 glasses daily."
        ) if lang == "en" else (
            "Drink plenty warm water, warm lemon with honey, or herbal tea. "
            "At least 8 cups for di day."
        )
        advice.diet_advice = "Light food: pap, garri, fruits, vegetables. Avoid cold drinks."
        advice.environment_advice = "Keep the room warm. Avoid cold breeze and air conditioning."
        advice.monitoring_advice = (
            "If fever persists >3 days, or difficulty breathing develops, see a doctor."
        )

    elif condition == "stress_tension":
        advice.rest_advice = (
            "Take a break from work. Sit down, close your eyes, breathe deeply. "
            "Sleep 7-8 hours tonight."
        ) if lang == "en" else (
            "Rest from work. Sit down, close your eye, breathe well well. "
            "Sleep 7-8 hours for di night."
        )
        advice.fluid_advice = "Drink water regularly. Avoid excessive caffeine (coffee, energy drinks)."
        advice.diet_advice = "Eat regular meals. Don't skip food — hunger worsens stress."
        advice.environment_advice = "Reduce screen time. Step outside for fresh air if possible."
        advice.monitoring_advice = (
            "If stress persists >2 weeks, or you feel hopeless/suicidal, seek help immediately."
        )

    elif condition == "mild_dehydration":
        advice.rest_advice = "Stop physical activity. Sit in a cool place."
        advice.fluid_advice = (
            "ORS is best: mix 1 sachet in 1 litre water, sip every 15 minutes. "
            "If no ORS, clean water with a pinch of salt and sugar."
        )
        advice.diet_advice = "Eat water-rich foods: watermelon, cucumber, oranges, soup."
        advice.environment_advice = "Stay in a cool, shaded area. Avoid sun exposure."
        advice.monitoring_advice = (
            "If no urine for 6 hours, or very dark urine, or dizziness worsens, go to hospital."
        )
        advice.add_ors = True

    elif condition == "heat_exhaustion":
        advice.rest_advice = "STOP all activity immediately. Lie down in a cool place."
        advice.fluid_advice = (
            "Drink cool water slowly (not ice cold). "
            "ORS if available. At least 1 litre over 1-2 hours."
        )
        advice.environment_advice = (
            "Move to shade or air-conditioned room. "
            "Apply cool wet cloth to forehead, neck, armpits. "
            "Fan the patient."
        )
        advice.monitoring_advice = (
            "If patient becomes confused, stops sweating, or体温 rises above 40°C, "
            "this is heat stroke — REFER IMMEDIATELY."
        )

    elif condition == "mild_stomach_upset":
        advice.rest_advice = "Rest the stomach. Don't eat for a few hours, then start with small amounts."
        advice.fluid_advice = "Small sips of water or ORS. Don't drink large amounts at once."
        advice.diet_advice = (
            "Start with: pap, boiled rice, banana, toast. "
            "Avoid: oil, pepper, fried food, dairy, carbonated drinks. "
            "Eat small, frequent meals."
        )
        advice.monitoring_advice = (
            "If pain is severe, or blood in stool/vomit, or can't keep water down, go to hospital."
        )

    elif condition == "simple_headache":
        advice.rest_advice = (
            "Lie down in a quiet, dark room for 30 minutes. "
            "Rest your eyes from screens (phone, TV, computer)."
        ) if lang == "en" else (
            "Lie down for quiet place, no light for 30 minutes. "
            "No look phone, TV, or computer."
        )
        advice.fluid_advice = "Drink 2-3 glasses of water. Dehydration is the most common cause of headache."
        advice.environment_advice = "Dim the lights. Reduce noise. Apply cool cloth to forehead."
        advice.monitoring_advice = (
            "If headache is worst ever, or with fever + stiff neck, or with vomiting, "
            "REFER IMMEDIATELY (could be meningitis)."
        )
        # Add paracetamol only if severe or with fever
        if "severe" in f"{_detect_condition.__code__.co_varnames}" or True:
            advice.add_paracetamol = True  # Safe to add for headache

    elif condition == "muscle_soreness":
        advice.rest_advice = (
            "Rest the sore muscles. Don't exercise the same muscles for 1-2 days. "
            "Gentle stretching is OK."
        )
        advice.fluid_advice = "Drink plenty of water. Dehydration worsens muscle cramps."
        advice.environment_advice = (
            "Warm bath or warm compress on sore areas. "
            "Gentle massage can help (but not deep massage on inflamed muscles)."
        )
        advice.monitoring_advice = (
            "If urine becomes dark (cola-colored), this could be rhabdomyolysis — go to hospital."
        )

    elif condition == "fatigue_weakness":
        advice.rest_advice = (
            "Get 7-9 hours of sleep tonight. "
            "Reduce your workload this week if possible."
        )
        advice.fluid_advice = "Drink water regularly. Dehydration causes fatigue."
        advice.diet_advice = (
            "Eat iron-rich foods: beans, spinach, red meat, eggs. "
            "Low iron (anaemia) is a common cause of tiredness in Nigeria."
        )
        advice.environment_advice = "Take short breaks during work. 5 minutes rest every hour."
        advice.monitoring_advice = (
            "If fatigue persists >2 weeks, or with weight loss, night sweats, or fever, "
            "see a doctor (could be TB, HIV, malaria, or anaemia)."
        )

    elif condition == "minor_allergy":
        advice.rest_advice = "Avoid the thing that caused the allergy (dust, food, etc.)."
        advice.fluid_advice = "Drink plenty of water to help flush the allergen."
        advice.environment_advice = "Keep the area clean and cool. Don't scratch the skin."
        advice.monitoring_advice = (
            "If swelling of face/tongue, difficulty breathing, or widespread hives, "
            "this is anaphylaxis — REFER IMMEDIATELY."
        )
        advice.add_antihistamine = True

    # Check if fever is present — add paracetamol
    if actions.get("add_paracetamol"):
        advice.add_paracetamol = True
    if actions.get("add_paracetamol_and_monitor"):
        advice.add_paracetamol = True

    return advice
