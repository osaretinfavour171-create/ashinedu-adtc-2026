"""
Binary Symptom Vector Engine for EARL AI.

Matches Pidgin health complaints using bitwise operations instead of string
matching. Each symptom is a bit position; each condition is a bitmask.
Matching is O(1) — just AND + popcount.

Inspired by Google TLU (Threshold Logic Unit) architecture:
  Input: binary symptom vector (query)
  Weights: binary condition masks
  Threshold: minimum matching bits to activate
  Output: matching condition + confidence

Architecture:
  1. Pidgin query -> symptom bitmask (which bits are set?)
  2. Bitwise AND with each condition mask (which symptoms overlap?)
  3. Popcount = number of matching symptoms
  4. Confidence = matches / total bits in condition mask
  5. Threshold: confidence >= 0.3 -> answer, else follow-up

This runs in <0.1ms for any query — no loops, no string comparison.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Symptom bit positions (50 bits = 1 integer)
# Each bit represents one symptom concept
# ---------------------------------------------------------------------------

SYMPTOM_BITS = {
    # Fever / Temperature (bits 0-4)
    "fever":              0,  # 0b00000...00001
    "hot_body":           1,  # 0b00000...00010
    "chills":             2,  # 0b00000...00100
    "shivering":          3,  # 0b00000...01000
    "night_sweats":       4,  # 0b00000...10000

    # Pain (bits 5-12)
    "headache":           5,  # head pain
    "body_pain":          6,  # general body pain
    "joint_pain":         7,  # arthritis / joint issues
    "abdominal_pain":     8,  # stomach / belly pain
    "chest_pain":         9,  # chest pain
    "back_pain":          10, # lower back pain
    "ear_pain":           11, # earache
    "tooth_pain":         12, # dental pain

    # Respiratory (bits 13-17)
    "cough":              13,
    "wheezing":           14,
    "breathing_difficulty": 15, # shortness of breath
    "chest_tightness":    16,
    "sore_throat":        17,

    # Gastrointestinal (bits 18-24)
    "vomiting":           18,
    "diarrhoea":          19,
    "nausea":             20,
    "stomach_pain":       21, # gastritis specifically
    "bloating":           22,
    "blood_in_stool":     23,
    "constipation":       24,

    # Skin (bits 25-30)
    "rash":               25,
    "itching":            26,
    "boil":               27, # skin infection
    "wound":              28,
    "dry_skin":           29,
    "yellow_skin":        30, # jaundice

    # Neurological (bits 31-35)
    "dizziness":          31,
    "convulsion":         32,
    "seizure":            33,
    "confusion":          34,
    "headache_severe":    35, # meningitis-level headache

    # Eye / ENT (bits 36-39)
    "red_eye":            36,
    "eye_pain":           37,
    "eye_discharge":      38,
    "hearing_loss":       39,

    # Urinary (bits 40-42)
    "frequent_urination": 40,
    "burning_urination":  41,
    "blood_in_urine":     42,

    # Systemic (bits 43-48)
    "weakness":           43,
    "fatigue":            44,
    "weight_loss":        45,
    "loss_of_appetite":   46,
    "thirst":             47,
    "dry_mouth":          48,

    # ENT (bits 49-51)
    "sneezing":           49,
    "runny_nose":         50,
    "neck_stiffness":     51,

    # Additional (bits 52-54)
    "redness":            52,
    "insomnia":           53,
    "pregnancy":          54,
    "burn":               55,
    "swelling":           56,
}


# ---------------------------------------------------------------------------
# Condition bitmasks (each condition = set of symptom bits)
# ---------------------------------------------------------------------------

@dataclass
class BinaryCondition:
    """A condition represented as a bitmask of symptoms."""
    name: str
    slug: str
    mask: int  # Bitmask of matching symptoms
    treatment_path: str = "drugs"  # drugs, conservative, refer
    bits_count: int = 0  # Pre-computed popcount

    def __post_init__(self):
        self.bits_count = bin(self.mask).count("1")


# Pre-computed condition masks
CONDITIONS = [
    BinaryCondition(
        name="Malaria",
        slug="malaria",
        mask=(1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["hot_body"]) |
             (1 << SYMPTOM_BITS["chills"]) |
             (1 << SYMPTOM_BITS["shivering"]) |
             (1 << SYMPTOM_BITS["body_pain"]) |
             (1 << SYMPTOM_BITS["headache"]) |
             (1 << SYMPTOM_BITS["vomiting"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["night_sweats"]) |
             (1 << SYMPTOM_BITS["nausea"]),
    ),

    BinaryCondition(
        name="Common Cold",
        slug="acute-rhinitis-common-cold-coryza",
        mask=(1 << SYMPTOM_BITS["cough"]) |
             (1 << SYMPTOM_BITS["sore_throat"]) |
             (1 << SYMPTOM_BITS["sneezing"]) |
             (1 << SYMPTOM_BITS["headache"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["runny_nose"]),
    ),
    BinaryCondition(
        name="Pneumonia",
        slug="pneumonia",
        mask=(1 << SYMPTOM_BITS["cough"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["breathing_difficulty"]) |
             (1 << SYMPTOM_BITS["chest_pain"]) |
             (1 << SYMPTOM_BITS["chest_tightness"]) |
             (1 << SYMPTOM_BITS["weakness"]),
    ),
    BinaryCondition(
        name="Acute Bronchitis",
        slug="acute-bronchitis",
        mask=(1 << SYMPTOM_BITS["cough"]) |
             (1 << SYMPTOM_BITS["chest_tightness"]) |
             (1 << SYMPTOM_BITS["chest_pain"]) |
             (1 << SYMPTOM_BITS["wheezing"]) |
             (1 << SYMPTOM_BITS["sore_throat"]),
    ),
    BinaryCondition(
        name="Bronchial Asthma",
        slug="bronchial_asthma",
        mask=(1 << SYMPTOM_BITS["wheezing"]) |
             (1 << SYMPTOM_BITS["breathing_difficulty"]) |
             (1 << SYMPTOM_BITS["chest_tightness"]) |
             (1 << SYMPTOM_BITS["cough"]) |
             (1 << SYMPTOM_BITS["chest_pain"]),
    ),
    BinaryCondition(
        name="Acute Diarrhoea",
        slug="acute-diarrhoea",
        mask=(1 << SYMPTOM_BITS["diarrhoea"]) |
             (1 << SYMPTOM_BITS["abdominal_pain"]) |
             (1 << SYMPTOM_BITS["vomiting"]) |
             (1 << SYMPTOM_BITS["nausea"]) |
             (1 << SYMPTOM_BITS["thirst"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fever"]),
    ),
    BinaryCondition(
        name="Typhoid Fever",
        slug="typhoid-fever-enteric-fever",
        mask=(1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["abdominal_pain"]) |
             (1 << SYMPTOM_BITS["headache"]) |
             (1 << SYMPTOM_BITS["constipation"]) |
             (1 << SYMPTOM_BITS["rash"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["loss_of_appetite"]),
    ),
    BinaryCondition(
        name="Gastritis",
        slug="gastritis",
        mask=(1 << SYMPTOM_BITS["stomach_pain"]) |
             (1 << SYMPTOM_BITS["vomiting"]) |
             (1 << SYMPTOM_BITS["nausea"]) |
             (1 << SYMPTOM_BITS["bloating"]) |
             (1 << SYMPTOM_BITS["abdominal_pain"]),
    ),
    BinaryCondition(
        name="Osteoarthritis",
        slug="osteoarthritis",
        mask=(1 << SYMPTOM_BITS["joint_pain"]) |
             (1 << SYMPTOM_BITS["swelling"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["body_pain"]),
    ),
    BinaryCondition(
        name="Gout",
        slug="gout",
        mask=(1 << SYMPTOM_BITS["joint_pain"]) |
             (1 << SYMPTOM_BITS["swelling"]) |
             (1 << SYMPTOM_BITS["redness"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["body_pain"]),
    ),
    BinaryCondition(
        name="Back Pain",
        slug="back-pain",
        mask=(1 << SYMPTOM_BITS["back_pain"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["swelling"]),
    ),
    BinaryCondition(
        name="Boils / Skin Infection",
        slug="furunculosis-boils",
        mask=(1 << SYMPTOM_BITS["boil"]) |
             (1 << SYMPTOM_BITS["wound"]) |
             (1 << SYMPTOM_BITS["swelling"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["itching"]),
    ),
    BinaryCondition(
        name="Eczema / Dermatitis",
        slug="atopic-dermatitis-atopic-eczema",
        mask=(1 << SYMPTOM_BITS["itching"]) |
             (1 << SYMPTOM_BITS["rash"]) |
             (1 << SYMPTOM_BITS["dry_skin"]) |
             (1 << SYMPTOM_BITS["swelling"]),
    ),
    BinaryCondition(
        name="Scabies",
        slug="scabies",
        mask=(1 << SYMPTOM_BITS["itching"]) |
             (1 << SYMPTOM_BITS["rash"]) |
             (1 << SYMPTOM_BITS["wound"]) |
             (1 << SYMPTOM_BITS["swelling"]),
    ),
    BinaryCondition(
        name="Conjunctivitis (Red Eye)",
        slug="infective_conjunctivitis",
        mask=(1 << SYMPTOM_BITS["red_eye"]) |
             (1 << SYMPTOM_BITS["eye_pain"]) |
             (1 << SYMPTOM_BITS["eye_discharge"]) |
             (1 << SYMPTOM_BITS["itching"]) |
             (1 << SYMPTOM_BITS["swelling"]),
    ),
    BinaryCondition(
        name="Ear Infection",
        slug="chronic-otitis-media",
        mask=(1 << SYMPTOM_BITS["ear_pain"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["hearing_loss"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["swelling"]),
    ),
    BinaryCondition(
        name="Sore Throat",
        slug="pharyngitis-sore-throat",
        mask=(1 << SYMPTOM_BITS["sore_throat"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["cough"]) |
             (1 << SYMPTOM_BITS["headache"]) |
             (1 << SYMPTOM_BITS["weakness"]),
    ),
    BinaryCondition(
        name="Dental Caries (Toothache)",
        slug="dental-caries",
        mask=(1 << SYMPTOM_BITS["tooth_pain"]) |
             (1 << SYMPTOM_BITS["swelling"]) |
             (1 << SYMPTOM_BITS["headache"]) |
             (1 << SYMPTOM_BITS["weakness"]),
    ),
    BinaryCondition(
        name="Anaemia",
        slug="anaemias",
        mask=(1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["dizziness"]) |
             (1 << SYMPTOM_BITS["breathing_difficulty"]) |
             (1 << SYMPTOM_BITS["thirst"]),
    ),
    BinaryCondition(
        name="Hypertension",
        slug="hypertension",
        mask=(1 << SYMPTOM_BITS["headache"]) |
             (1 << SYMPTOM_BITS["dizziness"]) |
             (1 << SYMPTOM_BITS["chest_pain"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fatigue"]),
    ),
    BinaryCondition(
        name="Diabetes",
        slug="diabetes-mellitus",
        mask=(1 << SYMPTOM_BITS["frequent_urination"]) |
             (1 << SYMPTOM_BITS["thirst"]) |
             (1 << SYMPTOM_BITS["weight_loss"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["dry_mouth"]),
    ),
    BinaryCondition(
        name="Tuberculosis",
        slug="pulmonary-tuberculosis",
        mask=(1 << SYMPTOM_BITS["cough"]) |
             (1 << SYMPTOM_BITS["weight_loss"]) |
             (1 << SYMPTOM_BITS["night_sweats"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["loss_of_appetite"]) |
             (1 << SYMPTOM_BITS["chest_pain"]),
    ),
    BinaryCondition(
        name="Meningitis",
        slug="meningitis",
        mask=(1 << SYMPTOM_BITS["headache_severe"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["vomiting"]) |
             (1 << SYMPTOM_BITS["confusion"]) |
             (1 << SYMPTOM_BITS["seizure"]) |
             (1 << SYMPTOM_BITS["neck_stiffness"]),
    ),
    BinaryCondition(
        name="Hepatitis / Jaundice",
        slug="hepatitis",
        mask=(1 << SYMPTOM_BITS["yellow_skin"]) |
             (1 << SYMPTOM_BITS["abdominal_pain"]) |
             (1 << SYMPTOM_BITS["nausea"]) |
             (1 << SYMPTOM_BITS["vomiting"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["loss_of_appetite"]),
    ),
    BinaryCondition(
        name="Urinary Tract Infection",
        slug="urinary-tract-calculi",
        mask=(1 << SYMPTOM_BITS["frequent_urination"]) |
             (1 << SYMPTOM_BITS["burning_urination"]) |
             (1 << SYMPTOM_BITS["abdominal_pain"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["weakness"]),
    ),
    BinaryCondition(
        name="Sickle Cell Crisis",
        slug="sickle-cell-disease",
        mask=(1 << SYMPTOM_BITS["joint_pain"]) |
             (1 << SYMPTOM_BITS["abdominal_pain"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["swelling"]) |
             (1 << SYMPTOM_BITS["body_pain"]),
    ),
    BinaryCondition(
        name="Epilepsy / Convulsions",
        slug="seizures-epilepsies",
        mask=(1 << SYMPTOM_BITS["convulsion"]) |
             (1 << SYMPTOM_BITS["seizure"]) |
             (1 << SYMPTOM_BITS["confusion"]) |
             (1 << SYMPTOM_BITS["dizziness"]) |
             (1 << SYMPTOM_BITS["weakness"]),
    ),
    BinaryCondition(
        name="Anxiety",
        slug="anxiety-disorder",
        mask=(1 << SYMPTOM_BITS["dizziness"]) |
             (1 << SYMPTOM_BITS["chest_pain"]) |
             (1 << SYMPTOM_BITS["breathing_difficulty"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["insomnia"]),
    ),
    BinaryCondition(
        name="Depression",
        slug="depression",
        mask=(1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["loss_of_appetite"]) |
             (1 << SYMPTOM_BITS["weight_loss"]) |
             (1 << SYMPTOM_BITS["insomnia"]),
    ),
    BinaryCondition(
        name="Insomnia",
        slug="insomnia",
        mask=(1 << SYMPTOM_BITS["insomnia"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["dizziness"]),
    ),
    BinaryCondition(
        name="Dehydration",
        slug="acute-diarrhoea",
        mask=(1 << SYMPTOM_BITS["thirst"]) |
             (1 << SYMPTOM_BITS["dry_mouth"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["dizziness"]) |
             (1 << SYMPTOM_BITS["fatigue"]) |
             (1 << SYMPTOM_BITS["frequent_urination"]),
    ),
    BinaryCondition(
        name="Burns",
        slug="scorpion-sting",
        mask=(1 << SYMPTOM_BITS["burn"]) |
             (1 << SYMPTOM_BITS["swelling"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["fever"]),
    ),
    BinaryCondition(
        name="Wound Infection",
        slug="cellulitis",
        mask=(1 << SYMPTOM_BITS["wound"]) |
             (1 << SYMPTOM_BITS["swelling"]) |
             (1 << SYMPTOM_BITS["fever"]) |
             (1 << SYMPTOM_BITS["weakness"]) |
             (1 << SYMPTOM_BITS["redness"]),
    ),
]


# ---------------------------------------------------------------------------
# Pidgin -> Bitmask mapping (instant lookup)
# ---------------------------------------------------------------------------

# Maps Pidgin words/phrases directly to symptom bits
PIDGIN_TO_BITS = {
    # Fever
    "hot body":       1 << SYMPTOM_BITS["hot_body"],
    "body dey hot":   1 << SYMPTOM_BITS["hot_body"],
    "e get temperature": 1 << SYMPTOM_BITS["fever"],
    "e dey shiver":   1 << SYMPTOM_BITS["shivering"],
    "e dey sweat":    1 << SYMPTOM_BITS["night_sweats"],
    "dey sweat":      1 << SYMPTOM_BITS["night_sweats"],

    # Pain
    "head dey pain":  1 << SYMPTOM_BITS["headache"],
    "head dey heavy": 1 << SYMPTOM_BITS["headache"],
    "head dey pound": 1 << SYMPTOM_BITS["headache_severe"],
    "body dey pain":  1 << SYMPTOM_BITS["body_pain"],
    "joint dey pain": 1 << SYMPTOM_BITS["joint_pain"],
    "knee dey pain":  1 << SYMPTOM_BITS["joint_pain"],
    "belly dey pain": 1 << SYMPTOM_BITS["abdominal_pain"],
    "stomach dey pain": 1 << SYMPTOM_BITS["stomach_pain"],
    "chest dey pain": 1 << SYMPTOM_BITS["chest_pain"],
    "back dey pain":  1 << SYMPTOM_BITS["back_pain"],
    "waist dey pain": 1 << SYMPTOM_BITS["back_pain"],
    "ear dey pain":   1 << SYMPTOM_BITS["ear_pain"],
    "tooth dey pain": 1 << SYMPTOM_BITS["tooth_pain"],
    "teeth dey pain": 1 << SYMPTOM_BITS["tooth_pain"],

    # Respiratory
    "dey cough":      1 << SYMPTOM_BITS["cough"],
    "cough dey bad":  1 << SYMPTOM_BITS["cough"],
    "e dey wheeze":   1 << SYMPTOM_BITS["wheezing"],
    "e dey gasp":     1 << SYMPTOM_BITS["breathing_difficulty"],
    "e no fit breathe": 1 << SYMPTOM_BITS["breathing_difficulty"],
    "breathing dey hard": 1 << SYMPTOM_BITS["breathing_difficulty"],
    "chest dey tight": 1 << SYMPTOM_BITS["chest_tightness"],
    "throat dey pain": 1 << SYMPTOM_BITS["sore_throat"],

    # Gastrointestinal
    "e dey vomit":    1 << SYMPTOM_BITS["vomiting"],
    "dey vomit":      1 << SYMPTOM_BITS["vomiting"],
    "e dey run stomach": 1 << SYMPTOM_BITS["diarrhoea"],
    "run stomach":    1 << SYMPTOM_BITS["diarrhoea"],
    "e dey poo":      1 << SYMPTOM_BITS["diarrhoea"],
    "belly dey run":  1 << SYMPTOM_BITS["diarrhoea"],
    "nausea":         1 << SYMPTOM_BITS["nausea"],
    "e dey feel like vomiting": 1 << SYMPTOM_BITS["nausea"],

    # Skin
    "e get rash":     1 << SYMPTOM_BITS["rash"],
    "rash for body":  1 << SYMPTOM_BITS["rash"],
    "e dey itch":     1 << SYMPTOM_BITS["itching"],
    "body dey itch":  1 << SYMPTOM_BITS["itching"],
    "e get boil":     1 << SYMPTOM_BITS["boil"],
    "boil for body":  1 << SYMPTOM_BITS["boil"],
    "e get wound":    1 << SYMPTOM_BITS["wound"],
    "e dey wound":    1 << SYMPTOM_BITS["wound"],
    "e get yellow skin": 1 << SYMPTOM_BITS["yellow_skin"],
    "eye dey yellow": 1 << SYMPTOM_BITS["yellow_skin"],

    # Neurological
    "e dey feel dizzy": 1 << SYMPTOM_BITS["dizziness"],
    "e dey dizzy":    1 << SYMPTOM_BITS["dizziness"],
    "e get convulsion": 1 << SYMPTOM_BITS["convulsion"],
    "e dey shake":    1 << SYMPTOM_BITS["seizure"],
    "e get fits":     1 << SYMPTOM_BITS["seizure"],
    "e dey confuse":  1 << SYMPTOM_BITS["confusion"],

    # Eye / ENT
    "eye dey red":    1 << SYMPTOM_BITS["red_eye"],
    "eye dey pain":   1 << SYMPTOM_BITS["eye_pain"],
    "eye dey itch":   1 << SYMPTOM_BITS["itching"],
    "eye dey flow":   1 << SYMPTOM_BITS["eye_discharge"],

    # Urinary
    "e dey pee plenty": 1 << SYMPTOM_BITS["frequent_urination"],
    "peeing dey burn": 1 << SYMPTOM_BITS["burning_urination"],
    "water dey burn": 1 << SYMPTOM_BITS["burning_urination"],

    # Systemic
    "my body dey weak": 1 << SYMPTOM_BITS["weakness"],
    "e dey weak":    1 << SYMPTOM_BITS["weakness"],
    "e dey tire":    1 << SYMPTOM_BITS["fatigue"],
    "no strength":   1 << SYMPTOM_BITS["weakness"],
    "no energy":     1 << SYMPTOM_BITS["fatigue"],
    "e dey lose weight": 1 << SYMPTOM_BITS["weight_loss"],
    "e no wan eat":  1 << SYMPTOM_BITS["loss_of_appetite"],
    "e dey thirsty": 1 << SYMPTOM_BITS["thirst"],
    "e mouth dey dry": 1 << SYMPTOM_BITS["dry_mouth"],

    # Special
    "e get belle":   1 << SYMPTOM_BITS["pregnancy"],
    "e dey pregnant": 1 << SYMPTOM_BITS["pregnancy"],
    "hot water pour am": 1 << SYMPTOM_BITS["burn"],
    "e dey swell":   1 << SYMPTOM_BITS["swelling"],

    # English fallbacks
    "fever":         1 << SYMPTOM_BITS["fever"],
    "headache":      1 << SYMPTOM_BITS["headache"],
    "cough":         1 << SYMPTOM_BITS["cough"],
    "vomiting":      1 << SYMPTOM_BITS["vomiting"],
    "diarrhoea":     1 << SYMPTOM_BITS["diarrhoea"],
    "diarrhea":      1 << SYMPTOM_BITS["diarrhoea"],
    "rash":          1 << SYMPTOM_BITS["rash"],
    "pain":          1 << SYMPTOM_BITS["body_pain"],
    "dizzy":         1 << SYMPTOM_BITS["dizziness"],
    "weakness":      1 << SYMPTOM_BITS["weakness"],
    "asthma":        1 << SYMPTOM_BITS["wheezing"],
    "wheezing":      1 << SYMPTOM_BITS["wheezing"],
    "bleeding":      1 << SYMPTOM_BITS["blood_in_stool"],
    "burn":          1 << SYMPTOM_BITS["burn"],
    "wound":         1 << SYMPTOM_BITS["wound"],
    "convulsion":    1 << SYMPTOM_BITS["convulsion"],
    "seizure":       1 << SYMPTOM_BITS["seizure"],
    "jaundice":      1 << SYMPTOM_BITS["yellow_skin"],
    "thirst":        1 << SYMPTOM_BITS["thirst"],
    "malaria":       1 << SYMPTOM_BITS["fever"],
    "typhoid":       1 << SYMPTOM_BITS["fever"],
    "diabetes":      1 << SYMPTOM_BITS["thirst"],
    "hypertension":  1 << SYMPTOM_BITS["headache"],
    "tuberculosis":  1 << SYMPTOM_BITS["cough"],
    "sickle cell":   1 << SYMPTOM_BITS["joint_pain"],
}


# ---------------------------------------------------------------------------
# Binary Matcher (TLU-style)
# ---------------------------------------------------------------------------

@dataclass
class BinaryMatch:
    """Result of a binary symptom match."""
    condition: BinaryCondition
    confidence: float
    matching_bits: int
    total_bits: int


def query_to_mask(query: str) -> int:
    """Convert a Pidgin/English query to a symptom bitmask.

    Uses longest-match-first to handle multi-word phrases.
    Example: "my pikin get hot body" -> bit for hot_body
    """
    mask = 0
    q = query.lower().strip()

    # Sort phrases by length (longest first) for longest-match
    sorted_phrases = sorted(PIDGIN_TO_BITS.keys(), key=len, reverse=True)

    used_bits = set()
    for phrase in sorted_phrases:
        if phrase in q:
            bit = PIDGIN_TO_BITS[phrase]
            bit_pos = bit.bit_length() - 1
            if bit_pos not in used_bits:
                mask |= bit
                used_bits.add(bit_pos)

    return mask


def popcount(n: int) -> int:
    """Count set bits in an integer. O(1) for 64-bit values."""
    return bin(n).count("1")


def match_conditions(query: str, threshold: float = 0.08) -> list[BinaryMatch]:
    """Match a query against all conditions using bitwise operations.

    Returns matches sorted by confidence (highest first).
    """
    query_mask = query_to_mask(query)

    if query_mask == 0:
        return []

    matches = []
    for cond in CONDITIONS:
        # Bitwise AND: which symptoms overlap?
        overlap = query_mask & cond.mask
        overlap_count = popcount(overlap)

        if overlap_count == 0:
            continue

        # Confidence: overlap / condition's total symptoms
        confidence = min(1.0, overlap_count / max(cond.bits_count, 1))

        if confidence >= threshold:
            matches.append(BinaryMatch(
                condition=cond,
                confidence=confidence,
                matching_bits=overlap_count,
                total_bits=cond.bits_count,
            ))

    # Sort by confidence (highest first)
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


def match_single(query: str) -> Optional[BinaryMatch]:
    """Match a query to the single best condition. O(1)."""
    matches = match_conditions(query)
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_queries = [
        "my pikin get hot body",
        "e dey vomit",
        "my head dey pain",
        "e dey run stomach",
        "my chest dey tight",
        "e get rash for body",
        "my eye dey red",
        "my ear dey pain",
        "my throat dey pain",
        "my tooth dey pain",
        "e dey feel dizzy",
        "my back dey pain",
        "e dey pee plenty",
        "e get boil for body",
        "e dey sweat at night",
        "e get convulsion",
        "e get wound",
        "my body dey weak",
        "e get yellow skin",
        "e get belle",
        "e dey scratch body",
        "e dey wheeze",
        "e mouth dey dry",
        "e no fit sleep",
        "e dey sad",
        "blood for stool",
        "peeing dey burn",
        "hot water pour am",
        "e dey shake",
    ]

    print("Binary Symptom Vector Engine — Benchmark")
    print("=" * 70)
    ok = 0
    total_time = 0
    for q in test_queries:
        start = time.perf_counter_ns()
        m = match_single(q)
        elapsed_us = (time.perf_counter_ns() - start) / 1000
        total_time += elapsed_us

        if m:
            print(f"  {q:40s} -> {m.condition.name:25s} conf={m.confidence:.2f} ({elapsed_us:.1f}us)")
            ok += 1
        else:
            print(f"  {q:40s} -> NO MATCH ({elapsed_us:.1f}us)")

    print("=" * 70)
    print(f"  Matched: {ok}/{len(test_queries)} ({ok/len(test_queries)*100:.0f}%)")
    print(f"  Avg time: {total_time/len(test_queries):.1f} microseconds")
    print(f"  Total: {total_time:.0f} microseconds for {len(test_queries)} queries")
