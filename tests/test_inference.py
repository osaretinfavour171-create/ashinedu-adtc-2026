"""Unit tests for the clinical inference engine."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from inference import (
    infer_context, _detect_scenario, _extract_existing_info,
    build_patient_context_from_query, get_question_prompt,
)


class TestScenarioDetection(unittest.TestCase):
    def test_drug_interaction(self):
        name, conf = _detect_scenario("metronidazole and warfarin interaction")
        self.assertEqual(name, "drug_interaction")
        self.assertGreater(conf, 0.3)

    def test_drug_dosing(self):
        name, conf = _detect_scenario("paracetamol dose for child")
        # May match drug_dosing or paediatric_generic depending on pattern scores
        self.assertIn(name, ("drug_dosing", "paediatric_generic"))

    def test_fever_child(self):
        name, conf = _detect_scenario("my pikin get hot body")
        self.assertIn(name, ("fever_child", "paediatric_generic"))

    def test_diarrhoea(self):
        name, conf = _detect_scenario("run stomach for 2 days")
        self.assertEqual(name, "diarrhoea")

    def test_respiratory(self):
        name, conf = _detect_scenario("child dey cough and no fit breathe well")
        self.assertEqual(name, "respiratory")

    def test_pain(self):
        name, conf = _detect_scenario("headache and body pain")
        self.assertEqual(name, "pain")

    def test_general_health(self):
        name, conf = _detect_scenario("what is malaria")
        self.assertEqual(name, "general_health")


class TestInfoExtraction(unittest.TestCase):
    def test_age_years(self):
        info = _extract_existing_info("3 year old pikin get fever")
        self.assertEqual(info["age"], "3 years")

    def test_weight(self):
        info = _extract_existing_info("child 15kg with cough")
        self.assertEqual(info["weight_kg"], 15.0)

    def test_gender_male(self):
        info = _extract_existing_info("boy get fever")
        self.assertEqual(info["gender"], "male")

    def test_gender_female(self):
        info = _extract_existing_info("girl dey vomit")
        self.assertEqual(info["gender"], "female")

    def test_temperature(self):
        info = _extract_existing_info("pikin temperature 38.5")
        self.assertIn("38.5", info["temperature"])

    def test_symptoms(self):
        info = _extract_existing_info("fever and headache and vomiting")
        self.assertIn("fever", info["symptoms"])

    def test_duration(self):
        info = _extract_existing_info("fever for 3 days")
        self.assertIn("3 days", info["duration"])


class TestInference(unittest.TestCase):
    def test_drug_interaction_detected(self):
        result = infer_context("metronidazole and warfarin interaction")
        self.assertEqual(result.scenario, "drug_interaction")

    def test_fever_child_needs_age(self):
        result = infer_context("my pikin get hot body")
        self.assertIn("age", result.missing_required)

    def test_general_health_no_questions(self):
        result = infer_context("what is malaria")
        self.assertFalse(result.should_ask)


class TestQuickContext(unittest.TestCase):
    def test_builds_context(self):
        ctx = build_patient_context_from_query("3 year old 15kg boy get fever")
        self.assertEqual(ctx.age, "3 years")
        self.assertEqual(ctx.weight_kg, 15.0)
        self.assertEqual(ctx.gender, "male")


class TestQuestionPrompts(unittest.TestCase):
    def test_age_pidgin(self):
        prompt = get_question_prompt("age", "pidgin")
        self.assertIn("old", prompt.lower())

    def test_weight_any_lang(self):
        prompt = get_question_prompt("weight", "en")
        self.assertTrue(len(prompt) > 5)


if __name__ == "__main__":
    unittest.main()
