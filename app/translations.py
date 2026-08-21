"""Translations for PidginPharma.

Supports 2 languages:
  - pidgin: Nigerian Pidgin English (default)
  - en: Standard English

To add more languages later, see archive/languages/translations_full_6lang.py
which has Hausa, Yoruba, Igbo, and Edo translations ready to restore.
"""

# Intake question prompts (key -> {lang: prompt})
INTAKE_PROMPTS = {
    "intro_pidgin": {
        "pidgin": "  Let me ask you some questions about di patient make I fit help well well.",
        "en": "  Let me ask some questions about the patient to give you the best advice.",
    },
    "intro_skip": {
        "pidgin": "  (You fit say 'skip' or 'i no know' for any question wey you no get answer.)",
        "en": "  (You can say 'skip' or 'i don't know' for any question you can't answer.)",
    },
    "age": {
        "pidgin": "How old is di patient? (e.g. 3 years, 6 months, adult)",
        "en": "What is the patient's age? (e.g. 3 years, 6 months, adult)",
    },
    "weight": {
        "pidgin": "How heavy is di patient? (e.g. 15 kg, 70 kg). If you no know, say 'skip'.",
        "en": "What is the patient's weight? (e.g. 15 kg, 70 kg). Say 'skip' if unknown.",
    },
    "gender": {
        "pidgin": "Na boy or na girl?",
        "en": "Is the patient male or female?",
    },
    "symptoms": {
        "pidgin": "Wetin dey worry di patient? Describe di symptoms (e.g. fever, vomit, run stomach)",
        "en": "What symptoms does the patient have? (e.g. fever, vomiting, diarrhoea)",
    },
    "duration": {
        "pidgin": "How long e don dey like dis? (e.g. 2 days, since yesterday)",
        "en": "How long has the patient had these symptoms? (e.g. 2 days, since yesterday)",
    },
    "temperature": {
        "pidgin": "You get thermometer? If yes, wetin e read? If no, say 'skip'.",
        "en": "Do you have a thermometer reading? If yes, what is it? Say 'skip' if not.",
    },
    "allergies": {
        "pidgin": "Di patient get any medicine wey e no fit take? (allergy). If none, say 'no'.",
        "en": "Does the patient have any drug allergies? Say 'no' if none.",
    },
    "pregnant": {
        "pidgin": "Na woman of childbearing age? If yes, she don born before or she fit dey pregnant?",
        "en": "Is this a woman of childbearing age? Could she be pregnant?",
    },
    "current_meds": {
        "pidgin": "Di patient dey take any medicine now? (e.g. paracetamol, amoxicillin). If none, say 'no'.",
        "en": "Is the patient currently taking any medications? Say 'no' if none.",
    },
    "history": {
        "pidgin": "Di patient get any long-term sickness? (e.g. asthma, diabetes, HIV). If none, say 'no'.",
        "en": "Does the patient have any chronic conditions? (e.g. asthma, diabetes, HIV). Say 'no' if none.",
    },
    "pulse": {
        "pidgin": "You fit feel im pulse? If yes, how e dey? (e.g. fast, normal, 110). If no, say 'skip'.",
        "en": "Can you feel the patient's pulse? How is it? (e.g. fast, normal, 110 bpm). Say 'skip' if unknown.",
    },
    "respiratory_rate": {
        "pidgin": "How e dey breathe? (e.g. normal, fast, hard). If no thermometer, say 'skip'.",
        "en": "How is the patient breathing? (e.g. normal, fast, difficult). Say 'skip' if unknown.",
    },
    "spo2": {
        "pidgin": "You get oxygen meter (oximeter)? If yes, wetin e read? If no, say 'skip'.",
        "en": "Do you have a pulse oximeter? If yes, what does it read? Say 'skip' if not available.",
    },
}

# Summary confirmation
SUMMARY = {
    "pidgin": "  OK, I don hear. Patient info: {summary}",
    "en": "  OK, got it. Patient info: {summary}",
}

# Loading messages (shown while processing)
LOADING_MESSAGES = {
    "pidgin": [
        "Please wait... I dey check the official guidelines for you.",
        "Hold on small... I dey look through the treatment book.",
        "Just a moment... I dey search for the right medicine info.",
        "One second... I dey check the drug interaction table for you.",
        "Hold on... I dey find di best answer from di Nigeria guidelines.",
    ],
    "en": [
        "Please wait... Checking the official guidelines for you.",
        "Hold on... Looking through the treatment guidelines.",
        "Just a moment... Searching for the right medicine information.",
        "One second... Checking the drug interaction database.",
        "Hold on... Finding the best answer from Nigerian clinical guidelines.",
    ],
}

# Common clinical responses
RESPONSES = {
    "no_services": {
        "pidgin": (
            "Sorry - the offline model and data server no dey reachable now. "
            "Run `start.ps1` or `bash start.sh` make dem start.\n\n"
            "If e be emergency, send di patient go hospital now now."
        ),
        "en": (
            "Sorry - the offline model and data server are not reachable now. "
            "Run `start.ps1` or `bash start.sh` to start them.\n\n"
            "If this is an emergency, refer the patient to hospital immediately."
        ),
    },
    "emergency_referral": {
        "pidgin": "WARNING: Send di patient go hospital NOW NOW. This one no fit wait.",
        "en": "WARNING: Refer the patient to hospital IMMEDIATELY. This cannot wait.",
    },
    "iv_fluid_needed": {
        "pidgin": "DRIP NEEDED: Di patient need IV fluid. Make sure say you get Normal Saline or Ringer Lactate. Give as prescribed.",
        "en": "IV FLUIDS NEEDED: The patient requires intravenous fluids. Ensure Normal Saline or Ringer Lactate is available.",
    },
    "symptom_detected": {
        "pidgin": "I see say this na patient problem. Make I ask some questions first.",
        "en": "I see this is a patient problem. Let me ask some questions first.",
    },
}

# Red flag messages
RED_FLAGS = {
    "fever_infant": {
        "pidgin": "RED FLAG: Hot body for pikin wey no pass 3 months - SEND HOSPITAL NOW",
        "en": "RED FLAG: Fever in infant (<3 months) - REFER IMMEDIATELY",
    },
    "spo2_low": {
        "pidgin": "RED FLAG: Oxygen don low well well (SpO2 <90%) - SEND HOSPITAL NOW",
        "en": "RED FLAG: Severe hypoxia (SpO2 <90%) - REFER IMMEDIATELY",
    },
    "fast_breathing_child": {
        "pidgin": "RED FLAG: Pikin dey breathe fast (fit be pneumonia) - SEND HOSPITAL",
        "en": "RED FLAG: Fast breathing in child (possible pneumonia) - REFER",
    },
    "dehydration_severe": {
        "pidgin": "RED FLAG: Severe dehydration - Patient need DRIP (IV fluid) NOW",
        "en": "RED FLAG: Severe dehydration - Patient needs IV fluids IMMEDIATELY",
    },
}

# IV Fluid guidance
IV_GUIDANCE = {
    "pidgin": {
        "normal_saline": "Normal Saline (0.9% NaCl): Give 20-30 ml/kg over 1 hour for dehydration. Can repeat.",
        "ringer_lactate": "Ringer Lactate: Give 20-30 ml/kg over 1 hour. Good for all ages.",
        "ors_drip": "ORS by nasogastric tube: If patient no fit drink, give ORS through thin tube for nose.",
        "maintenance": "Maintenance IV: 60 ml/kg/day for first 10kg + 30 ml/kg/day for next 10kg + 20 ml/kg/day thereafter.",
    },
    "en": {
        "normal_saline": "Normal Saline (0.9% NaCl): 20-30 ml/kg over 1 hour for dehydration. May repeat.",
        "ringer_lactate": "Ringer Lactate: 20-30 ml/kg over 1 hour. Suitable for all ages.",
        "ors_drip": "ORS by nasogastric tube: If patient cannot drink, administer ORS via NG tube.",
        "maintenance": "Maintenance IV: 60 ml/kg/day for first 10kg + 30 ml/kg/day for next 10kg + 20 ml/kg/day thereafter.",
    },
}


def get_intake_prompt(key: str, lang: str = "pidgin") -> str:
    """Get an intake question prompt in the requested language."""
    prompts = INTAKE_PROMPTS.get(key, {})
    return prompts.get(lang, prompts.get("pidgin", key))


def get_loading_messages(lang: str = "pidgin") -> list:
    """Get loading messages in the requested language."""
    return LOADING_MESSAGES.get(lang, LOADING_MESSAGES["pidgin"])


def get_response(key: str, lang: str = "pidgin") -> str:
    """Get a clinical response in the requested language."""
    msgs = RESPONSES.get(key, {})
    return msgs.get(lang, msgs.get("pidgin", key))


def get_red_flag(key: str, lang: str = "pidgin") -> str:
    """Get a red flag message in the requested language."""
    flags = RED_FLAGS.get(key, {})
    return flags.get(lang, flags.get("pidgin", key))


def get_summary(lang: str = "pidgin") -> str:
    """Get the summary confirmation template."""
    template = SUMMARY.get(lang, SUMMARY["pidgin"])
    return template


def get_iv_guidance(key: str, lang: str = "pidgin") -> str:
    """Get IV fluid guidance in the requested language."""
    guides = IV_GUIDANCE.get(lang, IV_GUIDANCE["pidgin"])
    return guides.get(key, key)
