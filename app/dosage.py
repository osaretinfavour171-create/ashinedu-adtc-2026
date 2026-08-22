"""Dosage calculator for PidginPharma.

Uses patient age + weight to compute exact mg/kg doses from the
Nigeria Essential Medicines List (EML 2020). This is the authoritative
source for drug dosing in Nigerian primary healthcare.

All dose ranges are per the Nigeria EML / NSTG 2022. The calculator
returns the recommended dose range and frequency for a given drug,
age, and weight combination.

WARNING: This is a clinical decision SUPPORT tool. The CHEW must
verify doses against the patient's clinical condition and the official
guidelines before prescribing.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DoseInfo:
    """Structured dose recommendation for a drug."""
    drug: str
    dose_min_mg: float
    dose_max_mg: float
    frequency: str
    route: str
    duration: str
    notes: str
    max_daily_mg: Optional[float] = None

    def format_pidgin(self) -> str:
        """Format dose info in Pidgin for the user."""
        lines = [f"\U0001f48a {self.drug}:"]
        lines.append(f"   Dose: {self.dose_min_mg:.0f} - {self.dose_max_mg:.0f} mg")
        lines.append(f"   How: {self.frequency}")
        lines.append(f"   Route: {self.route}")
        if self.duration != "as needed":
            lines.append(f"   Time: {self.duration}")
        if self.max_daily_mg:
            lines.append(f"   Max per day: {self.max_daily_mg:.0f} mg")
        if self.notes:
            lines.append(f"   Note: {self.notes}")
        return "\n".join(lines)

    def format_english(self) -> str:
        """Format dose info in plain English."""
        lines = [f"{self.drug}:"]
        lines.append(f"   Dose: {self.dose_min_mg:.0f} - {self.dose_max_mg:.0f} mg")
        lines.append(f"   Frequency: {self.frequency}")
        lines.append(f"   Route: {self.route}")
        if self.duration != "as needed":
            lines.append(f"   Duration: {self.duration}")
        if self.max_daily_mg:
            lines.append(f"   Max daily: {self.max_daily_mg:.0f} mg")
        if self.notes:
            lines.append(f"   Note: {self.notes}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Drug dose database (Nigeria EML 2020 + NSTG 2022)
# ---------------------------------------------------------------------------
# Each entry: drug -> list of (age_min, age_max, dose_per_kg, dose_unit,
#                             freq, route, duration, notes, max_daily)
# All doses in mg/kg unless noted.

_DRUG_DATABASE = {
    # === ANALGESICS / ANTIPYRETICS ===
    "paracetamol": [
        (0.0, 0.25, 10, "mg", "every 4-6 hours", "oral", "as needed",
         "Max 4 doses/day. For neonates use IV under supervision.", 60),
        (0.25, 12, 10, "mg", "every 4-6 hours", "oral", "as needed",
         "Max 60 mg/kg/day. Use calibrated syringe.", 60),
        (12, 100, 500, "mg_flat", "every 4-6 hours", "oral", "as needed",
         "Max 4g/day. Reduce in liver disease.", 4000),
    ],
    "ibuprofen": [
        (3/12, 12, 5, "mg", "every 8 hours", "oral", "after food",
         "Max 20 mg/kg/day. Avoid in dehydration. Not for <3 months.", 30),
        (12, 100, 200, "mg_flat", "every 8 hours", "oral", "after food",
         "Max 1200mg/day OTC. Take with food.", 1200),
    ],
    "aspirin": [
        (12, 100, 10, "mg", "every 4-6 hours", "oral", "after food",
         "NOT for children under 12 (Reye syndrome risk). Max 4g/day.", 4000),
    ],

    # === ANTIMALARIALS ===
    "artemether lumefantrine": [
        (0, 0.25, 0, "mg", "N/A", "N/A", "N/A",
         "Neonates <5kg: NOT recommended. Use rectal artesunate.", 0),
        (0.25, 5, 20, "mg_al", "as per weight band", "oral", "3 days",
         "5-14kg: 1 tablet (20mg AL) twice daily x3 days.", 0),
        (5, 15, 40, "mg_al", "as per weight band", "oral", "3 days",
         "15-25kg: 2 tablets twice daily x3 days. Take with fatty food.", 0),
        (15, 25, 60, "mg_al", "as per weight band", "oral", "3 days",
         "25-35kg: 3 tablets twice daily x3 days.", 0),
        (25, 100, 80, "mg_al", "as per weight band", "oral", "3 days",
         ">35kg: 4 tablets twice daily x3 days. Take with fatty food.", 0),
    ],
    "artesunate": [
        (0, 0.25, 0, "mg", "N/A", "rectal", "N/A",
         "Pre-referral: 10mg rectal stat for severe malaria in children.", 0),
        (0.25, 20, 10, "mg", "once daily", "rectal", "until oral can be given",
         "Pre-referral rectal artesunate for severe malaria.", 0),
        (20, 100, 2.4, "mg", "at 0h, 12h, 24h, then daily", "IV/IM", "until oral",
         "Severe malaria: 2.4 mg/kg IV/IM. Refer immediately.", 0),
    ],
    "sulfadoxine pyrimethamine": [
        (0, 12, 25, "mg_SP", "single dose", "oral", "single dose",
         "IPTp-SP: 3 doses from 13 weeks in pregnancy. Not for treatment.", 0),
        (12, 100, 75, "mg_SP", "single dose", "oral", "single dose",
         "Pregnancy: 3 tablets (500/25mg) as IPTp.", 0),
    ],

    # === ANTIBIOTICS ===
    "amoxicillin": [
        (0.5, 12, 25, "mg", "every 8 hours", "oral", "5-7 days",
         "Dose by weight. 125mg/5ml suspension.", 80),
        (12, 100, 500, "mg_flat", "every 8 hours", "oral", "5-7 days",
         "500mg capsules. Max 3g/day.", 3000),
    ],
    "metronidazole": [
        (0, 12, 7.5, "mg", "every 8 hours", "oral", "5-7 days",
         "Trichomoniasis: 15mg/kg single dose. Giardia: 5 days.", 40),
        (12, 100, 400, "mg_flat", "every 8 hours", "oral", "5-7 days",
         "400mg tablets. Avoid alcohol during and 48h after.", 2400),
    ],
    "ciprofloxacin": [
        (0, 18, 0, "mg", "N/A", "N/A", "N/A",
         "CONTRAINDICATED in children <18 (cartilage damage risk).", 0),
        (18, 100, 500, "mg_flat", "every 12 hours", "oral", "5-14 days",
         "Take 2h before or 6h after antacids/iron.", 1500),
    ],
    "doxycycline": [
        (0, 8, 0, "mg", "N/A", "N/A", "N/A",
         "CONTRAINDICATED in children <8 years (teeth staining).", 0),
        (8, 45, 2.2, "mg", "every 12 hours", "oral", "5-7 days",
         "Malaria prophylaxis: 100mg daily.", 200),
        (45, 100, 100, "mg_flat", "every 12 hours", "oral", "5-7 days",
         "100mg capsules. Take with full glass of water.", 200),
    ],
    "azithromycin": [
        (6/12, 12, 10, "mg", "day 1, then 5mg/day x4 days", "oral", "5 days",
         "Day 1: 10mg/kg. Days 2-5: 5mg/kg.", 500),
        (12, 100, 500, "mg_flat", "day 1, then 250mg x4 days", "oral", "5 days",
         "Day 1: 500mg. Days 2-5: 250mg.", 500),
    ],
    "erythromycin": [
        (0, 12, 10, "mg", "every 8 hours", "oral", "5-10 days",
         "Suspension 125mg/5ml. Max 50mg/kg/day.", 50),
        (12, 100, 500, "mg_flat", "every 8 hours", "oral", "5-10 days",
         "250-500mg per dose. Max 4g/day.", 4000),
    ],

    # === ORAL REHYDRATION ===
    "ors": [
        (0, 100, 0, "ml", "after each loose stool", "oral", "until diarrhoea stops",
         "Mild: 50ml/kg over 4h. Moderate: 100ml/kg over 4h. Use ORS sachet in 1L water.", 0),
    ],
    "zinc": [
        (0, 6, 10, "mg", "once daily", "oral", "10-14 days",
         "Children <6 months: 10mg/day for 10-14 days.", 10),
        (6, 100, 20, "mg", "once daily", "oral", "10-14 days",
         "Children >=6 months: 20mg/day for 10-14 days.", 20),
    ],

    # === ANTIHYPERTENSIVES ===
    "amlodipine": [
        (6, 18, 0.06, "mg", "once daily", "oral", "ongoing",
         "Paediatric: 0.06-0.3 mg/kg/day. Start low.", 5),
        (18, 100, 5, "mg_flat", "once daily", "oral", "ongoing",
         "Start 5mg, max 10mg. Takes 1-2 weeks for full effect.", 10),
    ],
    "enalapril": [
        (0, 12, 0.08, "mg", "once daily", "oral", "ongoing",
         "Paediatric: 0.08 mg/kg/day. Start low.", 0.6),
        (12, 100, 5, "mg_flat", "once daily", "oral", "ongoing",
         "Start 5mg, max 40mg. Monitor renal function.", 40),
    ],
    "hydrochlorothiazide": [
        (0, 12, 1, "mg", "once daily", "oral", "ongoing",
         "Paediatric: 1-2 mg/kg/day.", 0),
        (12, 100, 25, "mg_flat", "once daily", "oral", "ongoing",
         "Start 12.5-25mg. Max 50mg.", 50),
    ],

    # === ANTI-EPILEPTICS ===
    "diazepam": [
        (0, 100, 0.2, "mg", "single dose for seizure", "rectal", "single dose",
         "Status epilepticus: 0.2-0.5 mg/kg rectal. Max 10mg.", 10),
        (0, 100, 0.1, "mg", "every 8 hours", "oral", "short course",
         "Anxiety/spasm: 0.1-0.2 mg/kg/day divided.", 10),
    ],
    "phenobarbitone": [
        (0, 100, 15, "mg", "once daily (loading: 20mg/kg)", "oral/IV", "ongoing",
         "Neonatal seizure: 20mg/kg IV loading. Maintenance: 3-5mg/kg/day.", 0),
    ],
    # === ANTHELMINTICS ===
    "albendazole": [(1, 2, 200, "mg_flat", "single dose", "oral", "single dose", "1-2y: 200mg. >2y: 400mg.", 400),],
    "mebendazole": [(2, 100, 500, "mg_flat", "single dose", "oral", "single dose", ">2y: 500mg.", 500),],
    # === ANTIEMETICS ===
    "metoclopramide": [(1, 12, 0.1, "mg", "every 8h", "oral", "short", "0.1mg/kg. Max 0.5mg/kg/day.", 0.5),(12, 100, 10, "mg_flat", "every 8h", "oral", "short", "10mg. Max 30mg/day.", 30),],
    "domperidone": [(0, 12, 0.25, "mg", "every 8h", "oral", "short", "0.25mg/kg.", 1.0),(12, 100, 10, "mg_flat", "every 8h", "oral", "short", "10mg. Max 30mg/day.", 30),],
    "ondansetron": [(0, 12, 0.15, "mg", "every 8h", "oral", "short", "0.15mg/kg.", 4),(12, 100, 4, "mg_flat", "every 8h", "oral", "short", "4mg. Max 16mg/day.", 16),],
    # === ANTIHISTAMINES ===
    "cetirizine": [(6, 100, 10, "mg_flat", "once daily", "oral", "as needed", "10mg once daily.", 10),],
    "chlorpheniramine": [(0, 12, 0.1, "mg", "every 8h", "oral", "as needed", "0.1mg/kg.", 0.4),(12, 100, 4, "mg_flat", "every 8h", "oral", "as needed", "4mg.", 12),],
    # === BRONCHODILATORS ===
    "salbutamol": [(0, 100, 0, "mg", "2-4 puffs every 4-6h", "inhaled", "as needed", "2 puffs via spacer.", 0),],
    # === CARDIOVASCULAR ===
    "nifedipine": [(12, 100, 10, "mg_flat", "every 8h", "oral", "ongoing", "10mg TID or ER 30mg daily.", 60),],
    "methyldopa": [(12, 100, 250, "mg_flat", "every 8h", "oral", "ongoing", "250mg TID. Max 3g/day.", 3000),],
    # === CORTICOSTEROIDS ===
    "prednisolone": [(0, 12, 1, "mg", "once daily", "oral", "5-7d", "1-2mg/kg/day.", 0),(12, 100, 20, "mg_flat", "once daily", "oral", "5-7d", "20-40mg/day.", 40),],
    "dexamethasone": [(0, 100, 0.15, "mg", "every 6h", "oral", "short", "Croup: 0.15mg/kg.", 0),],
    # === ANTIFUNGALS ===
    "nystatin": [(0, 100, 100000, "units", "4x daily", "oral", "7-14d", "Oral thrush.", 400000),],
    # === ANTI-SEIZURE ===
    "carbamazepine": [(0, 12, 5, "mg", "every 12h", "oral", "ongoing", "5mg/kg/day BID.", 0),(12, 100, 200, "mg_flat", "every 12h", "oral", "ongoing", "200mg BID. Max 1200mg/day.", 1200),],
    "valproate": [(0, 12, 10, "mg", "every 12h", "oral", "ongoing", "CONTRAINDICATED in pregnancy.", 0),(12, 100, 300, "mg_flat", "every 12h", "oral", "ongoing", "300mg BID. Max 2.4g/day.", 2400),],
    "midazolam": [(0, 100, 0.2, "mg", "single dose", "buccal/IM", "single", "0.2mg/kg buccal (max 10mg).", 10),],
    # === DIABETES ===
    "metformin": [(10, 100, 500, "mg_flat", "twice daily with food", "oral", "ongoing", "500mg BID with meals. Max 2g/day.", 2000),],
    "insulin": [(0, 100, 0.5, "units", "per kg per day", "SC injection", "ongoing", "MUST refer for initiation.", 0),],
    # === DERMATOLOGY ===
    "permethrin": [(0, 100, 0, "mg", "applied to skin", "topical", "single", "5% cream for scabies.", 0),],
    # === MUSCULOSKELETAL / TOPICAL ===
    "diclofenac gel": [
        (12, 100, 0, "mg", "apply 3-4 times daily", "topical", "ongoing",
         "Apply thin layer to affected joint 3-4 times daily. Avoid broken skin. Max 4g/day.", 0),
        (0, 12, 0, "mg", "apply 2-3 times daily", "topical", "short course",
         "Children >12: apply thin layer to affected area 2-3 times daily.", 0),
    ],
    "capsaicin cream": [
        (12, 100, 0, "mg", "apply 3-4 times daily", "topical", "ongoing",
         "Apply to affected joint 3-4 times daily. Wash hands after. Avoid eyes/mucous membranes. Takes 1-2 weeks for full effect.", 0),
        (0, 12, 0, "mg", "apply with caution", "topical", "N/A",
         "Not recommended for young children. Use only in older children with supervision.", 0),
    ],
    "menthol rub": [
        (0, 100, 0, "mg", "apply as needed", "topical", "as needed",
         "Apply to painful area for temporary relief. Do not apply to broken skin or wounds.", 0),
    ],
    "colchicine": [
        (0, 18, 0, "mg", "N/A", "N/A", "N/A",
         "Colchicine: NOT recommended for children. REFER for gout in children.", 0),
        (18, 100, 0.5, "mg", "every 1-2 hours until pain eases", "oral", "1-2 weeks",
         "Gout: 0.5mg every 1-2h until pain eases (max 6mg). Then 0.5mg BID x1-2wks. Max dose with renal impairment.", 6),
    ],
    "allopurinol": [
        (0, 18, 0, "mg", "N/A", "N/A", "N/A",
         "NOT for children. REFER for gout in children.", 0),
        (18, 100, 100, "mg_flat", "once daily", "oral", "ongoing",
         "Start 100mg daily, increase by 100mg every 2-4 weeks. Max 600mg/day. Monitor renal function.", 600),
    ],
    # === TB ===
    "ethambutol": [(0, 100, 15, "mg", "once daily", "oral", "2 months", "Refer to DOTS.", 0),],
    "pyrazinamide": [(0, 100, 25, "mg", "once daily", "oral", "2 months", "Refer to DOTS.", 0),],
    # === IV FLUIDS / INFUSIONS ===
    "normal saline": [
        (0, 100, 20, "ml/kg", "over 1-2 hours", "IV infusion", "repeat as needed",
         "Dehydration: 20-30 ml/kg over 1-2h. Can repeat x2. Monitor urine output.", 0),
    ],
    "ringer lactate": [
        (0, 100, 20, "ml/kg", "over 1-2 hours", "IV infusion", "repeat as needed",
         "Dehydration: 20-30 ml/kg over 1-2h. Preferred for burns and trauma.", 0),
    ],
    "iv paracetamol": [
        (0, 12, 15, "mg", "every 6 hours", "IV infusion", "as needed",
         "IV paracetamol: 15mg/kg over 15 min. For patients who cannot take oral.", 60),
        (12, 100, 1000, "mg_flat", "every 6 hours", "IV infusion", "as needed",
         "1g over 15 min. Max 4g/day. For severe pain/fever when oral not possible.", 4000),
    ],
    "iv amoxicillin": [
        (0, 12, 25, "mg", "every 8 hours", "IV infusion", "5-7 days",
         "Severe infection: 25mg/kg IV q8h. For severe pneumonia or sepsis.", 80),
        (12, 100, 500, "mg_flat", "every 8 hours", "IV infusion", "5-7 days",
         "500mg IV q8h. Max 3g/day.", 3000),
    ],
    "iv metronidazole": [
        (0, 12, 7.5, "mg", "every 8 hours", "IV infusion", "5-7 days",
         "Severe infection: 7.5mg/kg IV q8h. For severe abdominal infections.", 40),
        (12, 100, 500, "mg_flat", "every 8 hours", "IV infusion", "5-7 days",
         "500mg IV q8h over 1h. Max 3g/day.", 3000),
    ],
    "iv artesunate": [
        (0, 100, 2.4, "mg", "at 0h, 12h, 24h, then daily", "IV/IM", "until oral",
         "SEVERE MALARIA: 2.4 mg/kg IV/IM. Must refer to hospital.", 0),
    ],
    "iv diazepam": [
        (0, 100, 0.2, "mg", "single dose for seizure", "IV slow push", "single dose",
         "Status epilepticus: 0.2-0.5 mg/kg IV slow push over 3-5 min. Max 10mg.", 10),
    ],
    "iv normal saline maintenance": [
        (0, 10, 60, "ml/kg", "per day", "IV infusion", "ongoing",
         "Maintenance: 60 ml/kg/day for first 10kg.", 0),
        (10, 20, 30, "ml/kg", "per day (above 10kg)", "IV infusion", "ongoing",
         "Maintenance: +30 ml/kg/day for next 10kg.", 0),
        (20, 100, 20, "ml/kg", "per day (above 20kg)", "IV infusion", "ongoing",
         "Maintenance: +20 ml/kg/day for weight above 20kg.", 0),
    ],

}


def calculate_dose(drug: str, age_years: Optional[float],
                   weight_kg: Optional[float]) -> Optional[DoseInfo]:
    """Calculate the recommended dose for a drug given patient age and weight.

    Args:
        drug: Drug name (will be normalized to lowercase).
        age_years: Patient age in years.
        weight_kg: Patient weight in kg.

    Returns:
        DoseInfo with dose range, or None if drug not found / contraindicated.
    """
    drug_lower = drug.lower().strip()

    # Normalize common name variants
    aliases = {
        "paracetamol": "paracetamol",
        "acetaminophen": "paracetamol",
        "tylenol": "paracetamol",
        "panadol": "paracetamol",
        "ibu": "ibuprofen",
        "ibuprofen": "ibuprofen",
        "advil": "ibuprofen",
        "motrin": "ibuprofen",
        "amox": "amoxicillin",
        "amoxicillin": "amoxicillin",
        "amoxil": "amoxicillin",
        "metro": "metronidazole",
        "metronidazole": "metronidazole",
        "flagyl": "metronidazole",
        "cipro": "ciprofloxacin",
        "ciprofloxacin": "ciprofloxacin",
        "doxy": "doxycycline",
        "doxycycline": "doxycycline",
        "azithro": "azithromycin",
        "azithromycin": "azithromycin",
        "z-pack": "azithromycin",
        "zithromax": "azithromycin",
        "erythro": "erythromycin",
        "erythromycin": "erythromycin",
        "al": "artemether lumefantrine",
        "artemether lumefantrine": "artemether lumefantrine",
        "coartem": "artemether lumefantrine",
        "artesunate": "artesunate",
        "sp": "sulfadoxine pyrimethamine",
        "sulfadoxine pyrimethamine": "sulfadoxine pyrimethamine",
        "fansidar": "sulfadoxine pyrimethamine",
        "ors": "ors",
        "oral rehydration": "ors",
        "zinc": "zinc",
        "amlodipine": "amlodipine",
        "norvasc": "amlodipine",
        "enalapril": "enalapril",
        "renitec": "enalapril",
        "hctz": "hydrochlorothiazide",
        "hydrochlorothiazide": "hydrochlorothiazide",
        "diazepam": "diazepam",
        "valium": "diazepam",
        "phenobarbitone": "phenobarbitone",
        "phenobarbital": "phenobarbitone",
        "alben": "albendazole",
        "vermox": "mebendazole",
        "ventolin": "salbutamol",
        "prednisone": "prednisolone",
        "glucophage": "metformin",
        "tegretol": "carbamazepine",
        "epilim": "valproate",
        "zofran": "ondansetron",
        "voltaren gel": "diclofenac gel",
        "diclofenac gel": "diclofenac gel",
        "diclofenac cream": "diclofenac gel",
        "capesin": "capsaicin cream",
        "capsaicin": "capsaicin cream",
        "capsaicin cream": "capsaicin cream",
        "dencorub": "menthol rub",
        "menthol rub": "menthol rub",
        "menthol": "menthol rub",
        "deep heat": "menthol rub",
        "cola": "menthol rub",
        "colchicine": "colchicine",
        "allopurinol": "allopurinol",
        "zyloric": "allopurinol",
        "drip": "normal saline",
        "ns": "normal saline",
        "normal saline": "normal saline",
        "rl": "ringer lactate",
        "ringer": "ringer lactate",
        "ringer lactate": "ringer lactate",
        "iv paracetamol": "iv paracetamol",
        "iv amoxicillin": "iv amoxicillin",
        "iv metronidazole": "iv metronidazole",
        "iv artesunate": "iv artesunate",
        "iv diazepam": "iv diazepam",
        "canesten": "clotrimazole",
        "aldomet": "methyldopa",
        "adalat": "nifedipine",
        "domperidone": "domperidone",
        "motilium": "domperidone",
        "nystatin": "nystatin",
        "salbutamol": "salbutamol",
        "prednisolone": "prednisolone",
        "dexamethasone": "dexamethasone",
        "carbamazepine": "carbamazepine",
        "valproate": "valproate",
        "metformin": "metformin",
        "insulin": "insulin",
        "midazolam": "midazolam",
        "permethrin": "permethrin",
        "ondansetron": "ondansetron",
        "chlorpheniramine": "chlorpheniramine",
        "cetirizine": "cetirizine",
        "ORS": "ORS",
        "oral rehydration": "ORS",
    }

    normalized = aliases.get(drug_lower, drug_lower)
    entries = _DRUG_DATABASE.get(normalized)
    if not entries:
        return None

    age = age_years if age_years is not None else 25.0  # default adult
    weight = weight_kg if weight_kg is not None else 60.0  # default adult

    # Find the matching dose range for this age
    for (age_min, age_max, dose_val, dose_unit, freq, route, duration, notes, max_daily) in entries:
        if age_min <= age < age_max or (age_max == 100 and age >= age_min):
            if dose_unit == "mg_flat":
                # Fixed dose (not weight-based)
                dose = dose_val
            else:
                # Weight-based dosing
                dose = dose_val * weight

            # Cap at drug maximum
            if max_daily and dose > max_daily:
                dose = max_daily

            return DoseInfo(
                drug=drug.title(),
                dose_min_mg=round(dose * 0.8, 1) if dose > 0 else 0,
                dose_max_mg=round(dose, 1) if dose > 0 else 0,
                frequency=freq,
                route=route,
                duration=duration,
                notes=notes,
                max_daily_mg=max_daily if max_daily else None,
            )

    return None


def get_red_flags(age_years: Optional[float], weight_kg: Optional[float],
                  temperature: Optional[str] = None,
                  pulse: Optional[str] = None,
                  respiratory_rate: Optional[str] = None,
                  spo2: Optional[str] = None) -> list[str]:
    """Check vitals against red flag thresholds for the patient's age group.

    Returns a list of red flag descriptions. Empty list = no red flags.
    """
    flags = []
    age = age_years if age_years is not None else 25.0

    # Parse temperature
    if temperature:
        import re
        m = re.search(r"(\d{2,3}(?:\.\d+)?)", temperature)
        if m:
            temp = float(m.group(1))
            if age < 3 and temp >= 38.0:
                flags.append("\u26a0\ufe0f RED FLAG: Fever in infant (<3 months) - REFER IMMEDIATELY")
            elif temp >= 40.0:
                flags.append("\u26a0\ufe0f RED FLAG: Very high fever (>=40C) - needs urgent care")

    # Parse pulse
    if pulse:
        import re
        m = re.search(r"(\d{2,3})", pulse)
        if m:
            bpm = int(m.group(1))
            if age < 1 and bpm > 160:
                flags.append("\u26a0\ufe0f RED FLAG: Very fast heart rate in infant - REFER")
            elif 1 <= age < 3 and bpm > 140:
                flags.append("\u26a0\ufe0f RED FLAG: Fast heart rate in toddler - REFER")
            elif age >= 3 and bpm > 120:
                flags.append("\u26a0\ufe0f RED FLAG: Fast heart rate (tachycardia)")
            elif bpm < 50:
                flags.append("\u26a0\ufe0f RED FLAG: Very slow heart rate (bradycardia) - REFER")

    # Parse respiratory rate
    if respiratory_rate:
        import re
        m = re.search(r"(\d{1,2})", respiratory_rate)
        if m:
            rr = int(m.group(1))
            if age < 1 and rr > 50:
                flags.append("\u26a0\ufe0f RED FLAG: Very fast breathing in infant - REFER")
            elif 1 <= age < 5 and rr > 40:
                flags.append("\u26a0\ufe0f RED FLAG: Fast breathing in child (possible pneumonia) - REFER")
            elif age >= 5 and rr > 30:
                flags.append("\u26a0\ufe0f RED FLAG: Fast breathing (tachypnoea)")

    # Parse SpO2
    # Parse SpO2
    if spo2:
        import re
        m = re.search(r"(\d{2,3})\s*%?", spo2)
        if m:
            s = int(m.group(1))
            if s < 90:
                flags.append("⚠️ RED FLAG: Severe hypoxia (SpO2 <90%) - REFER IMMEDIATELY")
            elif s < 94:
                flags.append("⚠️ RED FLAG: Low oxygen (SpO2 <94%) - needs assessment")

    return flags



def needs_iv_fluids(age_years, weight_kg, symptoms=None,
                     temperature=None, spo2=None,
                     respiratory_rate=None) -> list[str]:
    """Determine if the patient needs IV fluids and why.

    Returns a list of reasons why IV fluids are needed.
    Empty list = no IV fluids needed at this time.
    """
    reasons = []
    age = age_years if age_years is not None else 25.0
    weight = weight_kg if weight_kg is not None else 60.0

    if symptoms:
        s = symptoms.lower()
        # Severe dehydration signs
        if any(w in s for w in ("dehydration", "dehydrated", "dry mouth", "no urine",
                                 "sunken eyes", "skin pinch", "not drinking")):
            reasons.append("Severe dehydration - IV fluids required")

        # Severe vomiting unable to take oral
        if any(w in s for w in ("vomiting", "vomit")) and any(w in s for w in ("cannot drink", "not drinking", "refusing", "unable")):
            reasons.append("Unable to take oral fluids - IV/NG tube needed")

        # Severe malaria (needs IV artesunate)
        if any(w in s for w in ("severe malaria", "cerebral malaria", "black urine", "very high fever")):
            reasons.append("Suspected severe malaria - IV artesunate required")

        # Sepsis signs
        if any(w in s for w in ("sepsis", "septic", "very cold", "cold hands", "mottled skin")):
            reasons.append("Suspected sepsis - IV antibiotics + fluids required")

        # Shock
        if any(w in s for w in ("shock", "very low blood pressure", "weak pulse", "collapsed")):
            reasons.append("Suspected shock - aggressive IV fluid resuscitation required")

    # Check SpO2 for severe hypoxia (may need IV medications)
    if spo2:
        import re
        m = re.search(r"(\d{2,3})", spo2)
        if m:
            s_val = int(m.group(1))
            if s_val < 90:
                reasons.append("Severe hypoxia - may need IV medications")

    # Infant with fever (<3 months) - may need IV antibiotics
    if age < 0.25:  # <3 months
        if temperature:
            import re
            m = re.search(r"(\d{2,3}(?:\.\d+)?)", temperature)
            if m:
                temp = float(m.group(1))
                if temp >= 38.0:
                    reasons.append("Fever in neonate (<3 months) - IV antibiotics likely needed")

    return reasons


def format_iv_recommendation(reasons, weight_kg=60.0, lang="pidgin"):
    "Format IV fluid recommendation based on clinical reasons."
    if not reasons:
        return ""

    weight = weight_kg if weight_kg else 60.0
    lines = []

    if lang == "pidgin":
        lines.append("IV FLUID RECOMMENDATION:")
        lines.append("  Di patient need drip (IV fluid) for these reasons:")
    else:
        lines.append("IV FLUID RECOMMENDATION:")
        lines.append("  The patient needs IV fluids for these reasons:")

    for i, reason in enumerate(reasons, 1):
        lines.append("  " + str(i) + ". " + reason)

    # Calculate fluid bolus
    bolus_ml = round(weight * 20)  # 20 ml/kg initial bolus
    if lang == "pidgin":
        lines.append("  Start with: " + str(bolus_ml) + " ml Normal Saline or Ringer Lactate over 1-2 hours.")
        lines.append("  Can repeat once if no improvement.")
        lines.append("  Monitor urine output - e must dey come out.")
        lines.append("  REFER TO HOSPITAL if: no improvement after 2 boluses, or patient dey worse.")
    else:
        lines.append("  Start with: " + str(bolus_ml) + " ml Normal Saline or Ringer Lactate over 1-2 hours.")
        lines.append("  Can repeat once if no improvement.")
        lines.append("  Monitor urine output - it must be produced.")
        lines.append("  REFER TO HOSPITAL if: no improvement after 2 boluses, or patient deteriorates.")

    return chr(10).join(lines)
