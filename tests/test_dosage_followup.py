"""Unit tests for dosage calculator and follow-up tracker."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from dosage import calculate_dose, get_red_flags, DoseInfo
from followup import FollowUpTracker, ConsultationRecord


class TestDosageCalculator(unittest.TestCase):
    def test_paracetamol_child(self):
        dose = calculate_dose("paracetamol", 3.0, 15.0)
        self.assertIsNotNone(dose)
        self.assertIn("paracetamol", dose.drug.lower())
        self.assertGreater(dose.dose_max_mg, 0)

    def test_paracetamol_adult(self):
        dose = calculate_dose("paracetamol", 30.0, 70.0)
        self.assertIsNotNone(dose)
        self.assertEqual(dose.dose_max_mg, 500)

    def test_ibuprofen_child(self):
        dose = calculate_dose("ibuprofen", 5.0, 20.0)
        self.assertIsNotNone(dose)
        self.assertIn("after food", dose.duration)

    def test_amoxicillin_child(self):
        dose = calculate_dose("amoxicillin", 2.0, 10.0)
        self.assertIsNotNone(dose)
        self.assertIn("every 8 hours", dose.frequency)

    def test_ciprofloxacin_contraindicated(self):
        """Ciprofloxacin is contraindicated in children <18."""
        dose = calculate_dose("ciprofloxacin", 10.0, 30.0)
        self.assertIsNotNone(dose)
        self.assertIn("CONTRAINDICATED", dose.notes)

    def test_doxycycline_contraindicated(self):
        """Doxycycline is contraindicated in children <8."""
        dose = calculate_dose("doxycycline", 5.0, 20.0)
        self.assertIsNotNone(dose)
        self.assertIn("CONTRAINDICATED", dose.notes)

    def test_unknown_drug(self):
        dose = calculate_dose("xyznonexistent", 30.0, 70.0)
        self.assertIsNone(dose)

    def test_alias_panadol(self):
        dose = calculate_dose("panadol", 5.0, 18.0)
        self.assertIsNotNone(dose)

    def test_alias_flagyl(self):
        dose = calculate_dose("flagyl", 30.0, 70.0)
        self.assertIsNotNone(dose)

    def test_zinc_child(self):
        dose = calculate_dose("zinc", 2.0, 10.0)
        self.assertIsNotNone(dose)
        self.assertIn("10-14 days", dose.duration)

    def test_ors(self):
        dose = calculate_dose("ors", 1.0, 8.0)
        self.assertIsNotNone(dose)

    def test_format_pidgin(self):
        dose = calculate_dose("paracetamol", 3.0, 15.0)
        text = dose.format_pidgin()
        self.assertIn("paracetamol", text.lower())
        self.assertIn("mg", text)

    def test_format_english(self):
        dose = calculate_dose("paracetamol", 3.0, 15.0)
        text = dose.format_english()
        self.assertIn("Dose:", text)


class TestRedFlags(unittest.TestCase):
    def test_fever_in_infant(self):
        flags = get_red_flags(0.1, 5.0, temperature="38.5")
        self.assertTrue(any("REFER" in f for f in flags))

    def test_high_fever(self):
        flags = get_red_flags(5.0, 20.0, temperature="41.0")
        self.assertTrue(len(flags) > 0)

    def test_fast_breathing_child(self):
        flags = get_red_flags(3.0, 14.0, respiratory_rate="45")
        self.assertTrue(len(flags) > 0)

    def test_low_spo2(self):
        flags = get_red_flags(10.0, 30.0, spo2="85")
        self.assertTrue(any("REFER" in f for f in flags))

    def test_no_flags_normal(self):
        flags = get_red_flags(5.0, 20.0, temperature="37.0", spo2="98")
        self.assertEqual(len(flags), 0)


class TestFollowUpTracker(unittest.TestCase):
    def test_record_consultation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import followup
            followup._HISTORY_DIR = tmpdir
            tracker = FollowUpTracker()
            tracker.record_consultation(
                "3 years, male, fever",
                "malaria",
                "ACT 3 days",
            )
            self.assertEqual(len(tracker._history), 1)

    def test_pending_followup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import followup
            old_dir = followup._HISTORY_DIR
            followup._HISTORY_DIR = tmpdir
            tracker = FollowUpTracker()
            # Record with old timestamp (3 days ago)
            rec = ConsultationRecord(
                timestamp=1000000,
                patient_summary="test patient",
                diagnosis="test",
                treatment_given="test meds",
            )
            tracker._history.append(rec)
            tracker._save_history()
            # Reload
            tracker2 = FollowUpTracker()
            self.assertTrue(tracker2.has_pending_followup())
            followup._HISTORY_DIR = old_dir


if __name__ == "__main__":
    unittest.main()
