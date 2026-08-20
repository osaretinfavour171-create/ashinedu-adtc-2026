"""Symptom detector for PidginPharma.

Determines whether a user's query is:
  1. A SYMPTOM query (needs intake flow for accurate diagnosis)
  2. A DRUG query (direct answer from interaction DB or LLM)
  3. A GENERAL query (general health info, no intake needed)

The detector uses keyword matching + heuristics. No ML required —
just fast, reliable pattern matching for the clinical domain.
"""

import re


# ---------------------------------------------------------------------------
# Keyword sets
# ---------------------------------------------------------------------------

# Symptoms the user might describe (English + Pidgin)
SYMPTOM_KEYWORDS = {
    # English
    "fever", "headache", "vomiting", "vomit", "diarrhoea", "diarrhea",
    "cough", "cold", "rash", "pain", "stomach ache", "stomach pain",
    "chest pain", "back pain", "joint pain", "muscle pain",
    "dizziness", "dizzy", "fainting", "weakness", "fatigue",
    "swelling", "bleeding", "bruising", "itching",
    "difficulty breathing", "shortness of breath", "wheezing",
    "loss of appetite", "weight loss", "night sweats",
    "burning urination", "frequent urination",
    "sore throat", "ear pain", "eye pain", "eye redness",
    "constipation", "bloating", "nausea",
    "convulsions", "seizure", "confusion",
    "wound", "infection", "abscess", "ulcer",
    "anaemia", "anemia", "jaundice",
    "swollen", "swelling",
    # Pidgin
    "hot body", "head dey pain", "dey vomit", "run stomach",
    "dey cough", "dey sneeze", "body dey pain", "belly dey pain",
    "chest dey pain", "back dey pain", "leg dey pain", "arm dey pain",
    "dey feel dizzy", "dey faint", "body dey weak", "no get strength",
    "skin dey itch", "body dey swell", "dey bleed",
    "no fit breathe well", "breathing dey hard",
    "no want chop", "body dey hot",
    "dey shake", "dey confuse", "eye dey pain", "throat dey pain",
    "wound dey pain", "cut dey pain",
}

# Drug/interaction keywords (direct answer, no intake needed)
DRUG_KEYWORDS = {
    "drug", "interaction", "combine", "mix", "together",
    "warfarin", "metronidazole", "aspirin", "ibuprofen",
    "paracetamol", "amoxicillin", "ciprofloxacin", "doxycycline",
    "artemether", "lumefantrine", "quinine", "chloroquine",
    "rifampicin", "isoniazid", "gentamicin", "ceftriaxone",
    "cotrimoxazole", "erythromycin", "azithromycin",
    "tramadol", "morphine", "diazepam",
    "lisinopril", "enalapril", "amlodipine", "nifedipine",
    "furosemide", "hydrochlorothiazide", "spironolactone",
    "prednisolone", "dexamethasone",
    "safe", "contraindication", "contraindicated",
    "dose", "dosage", "how much", "how many",
    "frequency", "how often",
    "plus", "and", "with",
    # Pidgin drug terms
    "medicine", "drug", "tablet", "injection",
    "e dey safe", "e go work", "e go harm",
}

# General health queries (no intake needed)
GENERAL_KEYWORDS = {
    "what is", "definition", "explain", "tell me about",
    "how does", "why does", "when to",
    "prevention", "prevent", "avoid",
    "symptom of", "sign of", "cause of",
    "nutrition", "diet", "food", "feeding",
    "hygiene", "sanitation", "clean",
    "vaccination", "immunization", "vaccine",
    "referral", "hospital", "when to go",
    "emergency", "first aid",
    # Pidgin
    "wetin be", "wetin na", "wetin dey cause",
    "how I go take", "wetin I fit do",
    "prevention", "avoid am",
}

# Reflex questions (direct answer, no intake)
REFLEX_KEYWORDS = {
    "thank", "thanks", "ok", "okay", "alright",
    "help", "what can you do", "how to use",
    "status", "stats", "exit", "quit",
}


def classify_query(query: str) -> str:
    """Classify a normalized query into a type.

    Returns:
        "symptom" — needs intake flow (user is describing a patient problem)
        "drug"    — direct answer (drug interaction/dosing question)
        "general" — general health info (no intake needed)
        "reflex"  — system command or chat (no intake needed)
    """
    q = query.lower().strip()
    if not q:
        return "reflex"

    # Reflex check
    for kw in REFLEX_KEYWORDS:
        if q.startswith(kw) or q == kw:
            return "reflex"

    # Drug query — mentions a specific drug or interaction term
    drug_score = sum(1 for kw in DRUG_KEYWORDS if kw in q)
    if drug_score >= 2:
        return "drug"

    # Symptom query — mentions symptoms
    symptom_score = sum(1 for kw in SYMPTOM_KEYWORDS if kw in q)
    if symptom_score >= 1:
        # But if it's also a drug question, prefer drug
        if drug_score >= 1:
            return "drug"
        return "symptom"

    # General query — starts with question words
    question_starters = ("what", "how", "why", "when", "where", "which", "can",
                         "wetin", "how I", "how to")
    if any(q.startswith(s) for s in question_starters):
        # Check if it's asking about a specific symptom (needs intake)
        if any(kw in q for kw in ("treatment", "management", "diagnosis", "drug")):
            # Asking about treatment for a symptom — needs intake
            if symptom_score >= 1:
                return "symptom"
            return "general"
        return "general"

    # Default: if it looks like a description of a problem, treat as symptom
    # Heuristics: contains "dey" (Pidgin for "is"), multiple symptoms mentioned
    if "dey" in q or symptom_score >= 1:
        return "symptom"

    return "general"


def extract_initial_symptoms(query: str) -> str:
    """Extract the symptom description from a query for pre-filling intake."""
    # Remove common Pidgin fillers
    fillers = ["my", "di", "the", "patient", "get", "don", "dey",
               "e", "she", "he", "wey", "and", "plus", "also"]
    words = query.lower().split()
    kept = [w for w in words if w not in fillers and len(w) > 1]
    return " ".join(kept)
