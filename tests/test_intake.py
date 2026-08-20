"""Unit tests for the clinical intake flow and symptom detector."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from intake import (
    PatientContext, _parse_age, _parse_weight, _parse_gender,
    _parse_temperature, _parse_yes_no, quick_intake, run_intake,
)
from symptom_detector import classify_query, extract_initial_symptoms


class TestAgeParsing(unittest.TestCase):
    def test_years(self):
        display, years = _parse_age("3 years")
        self.assertEqual(display, "3 years")
        self.assertEqual(years, 3.0)

    def test_months(self):
        display, years = _parse_age("6 months")
        self.assertEqual(display, "6 months")
        self.assertAlmostEqual(years, 0.5)

    def test_days(self):
        display, years = _parse_age("10 days")
        self.assertEqual(display, "10 days")

    def test_bare_number(self):
        display, years = _parse_age("25")
        self.assertEqual(display, "25 years")
        self.assertEqual(years, 25.0)

    def test_adult(self):
        display, years = _parse_age("adult")
        self.assertEqual(display, "adult")
        self.assertEqual(years, 30.0)

    def test_baby(self):
        display, years = _parse_age("baby")
        self.assertEqual(display, "newborn")

    def test_pidgin_pikin(self):
        display, years = _parse_age("pikin")
        self.assertIsNotNone(display)

    def test_skip(self):
        display, years = _parse_age("skip")
        self.assertIsNone(display)
        self.assertIsNone(years)

    def test_empty(self):
        display, years = _parse_age("")
        self.assertIsNone(display)


class TestWeightParsing(unittest.TestCase):
    def test_kg(self):
        kg, display = _parse_weight("30 kg")
        self.assertEqual(kg, 30.0)
        self.assertIn("kg", display)

    def test_kilos(self):
        kg, display = _parse_weight("45 kilos")
        self.assertEqual(kg, 45.0)

    def test_pounds(self):
        kg, display = _parse_weight("66 lbs")
        self.assertAlmostEqual(kg, 29.9, places=1)

    def test_bare_number(self):
        kg, display = _parse_weight("20")
        self.assertEqual(kg, 20.0)

    def test_skip(self):
        kg, display = _parse_weight("skip")
        self.assertIsNone(kg)

    def test_out_of_range(self):
        kg, display = _parse_weight("500")
        self.assertIsNone(kg)


class TestGenderParsing(unittest.TestCase):
    def test_male(self):
        self.assertEqual(_parse_gender("male"), "male")
        self.assertEqual(_parse_gender("boy"), "male")

    def test_female(self):
        self.assertEqual(_parse_gender("female"), "female")
        self.assertEqual(_parse_gender("girl"), "female")

    def test_skip(self):
        self.assertIsNone(_parse_gender("skip"))


class TestTemperatureParsing(unittest.TestCase):
    def test_celsius(self):
        self.assertIn("38.5", _parse_temperature("38.5"))

    def test_with_unit(self):
        result = _parse_temperature("39.2C")
        self.assertIn("39.2", result)

    def test_fahrenheit(self):
        result = _parse_temperature("101.3F")
        self.assertIn("38.5", result)

    def test_qualitative_hot(self):
        result = _parse_temperature("very hot")
        self.assertIsNotNone(result)

    def test_skip(self):
        self.assertIsNone(_parse_temperature("skip"))


class TestYesNoParsing(unittest.TestCase):
    def test_yes(self):
        self.assertTrue(_parse_yes_no("yes"))
        self.assertTrue(_parse_yes_no("yeah"))

    def test_no(self):
        self.assertFalse(_parse_yes_no("no"))
        self.assertFalse(_parse_yes_no("nah"))

    def test_skip(self):
        self.assertIsNone(_parse_yes_no("skip"))


class TestPatientContext(unittest.TestCase):
    def test_to_prompt_block(self):
        ctx = PatientContext(
            age="3 years", age_years=3.0, weight_kg=15.0,
            gender="male", symptoms="fever, vomiting",
        )
        block = ctx.to_prompt_block()
        self.assertIn("Age: 3 years", block)
        self.assertIn("Weight: 15.0 kg", block)
        self.assertIn("Gender: male", block)
        self.assertIn("Symptoms: fever, vomiting", block)

    def test_is_complete(self):
        ctx = PatientContext(age="5 years", symptoms="fever")
        self.assertTrue(ctx.is_complete())
        ctx2 = PatientContext(age="5 years")
        self.assertFalse(ctx2.is_complete())

    def test_summary_line(self):
        ctx = PatientContext(age="3 years", gender="male", symptoms="fever")
        summary = ctx.summary_line()
        self.assertIn("3 years", summary)
        self.assertIn("fever", summary)


class TestQuickIntake(unittest.TestCase):
    def test_extracts_age(self):
        ctx = quick_intake("3 year old pikin get fever")
        self.assertEqual(ctx.age, "3 years")

    def test_extracts_weight(self):
        ctx = quick_intake("child 15kg with cough")
        self.assertEqual(ctx.weight_kg, 15.0)

    def test_full_query_as_symptoms(self):
        ctx = quick_intake("my pikin get hot body and dey vomit since yesterday")
        self.assertTrue("hot body" in ctx.symptoms.lower() or "fever" in ctx.symptoms.lower())


class TestSymptomDetector(unittest.TestCase):
    def test_symptom_query(self):
        self.assertEqual(classify_query("my pikin get hot body"), "symptom")
        self.assertIn(classify_query("fever and vomiting"), ("symptom", "drug"))
        self.assertEqual(classify_query("diarrhoea treatment"), "symptom")

    def test_drug_query(self):
        self.assertEqual(classify_query("metronidazole and warfarin interaction"), "drug")
        self.assertEqual(classify_query("paracetamol dose for child"), "drug")

    def test_general_query(self):
        self.assertEqual(classify_query("what is malaria"), "general")
        self.assertEqual(classify_query("how does paracetamol work"), "general")

    def test_reflex_query(self):
        self.assertEqual(classify_query("help"), "reflex")
        self.assertEqual(classify_query("exit"), "reflex")

    def test_pidgin_symptom(self):
        self.assertEqual(classify_query("head dey pain"), "symptom")
        self.assertEqual(classify_query("body dey hot"), "symptom")


class TestExtractSymptoms(unittest.TestCase):
    def test_removes_fillers(self):
        result = extract_initial_symptoms("my pikin get hot body and dey vomit")
        self.assertNotIn("my", result.split())
        self.assertNotIn("di", result.split())


if __name__ == "__main__":
    unittest.main()
