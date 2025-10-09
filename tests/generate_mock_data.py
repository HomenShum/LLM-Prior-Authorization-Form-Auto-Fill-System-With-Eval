"""
Generate mock test data based on sample patient data.
Creates ground truth answers for evaluation.
"""

import json
from pathlib import Path

# Load sample data
sample_dir = Path(__file__).parent.parent / "sample_data"
with open(sample_dir / "patient_data.json", encoding="utf-8") as f:
    patients = json.load(f)

with open(sample_dir / "zepbound_question_set.json", encoding="utf-8") as f:
    questions = json.load(f)

# Generate ground truth answers for each patient
mock_test_cases = []

for patient in patients:
    # Create expected answers based on patient data
    expected_answers = {}

    # Extract info from visit notes
    notes_text = " ".join(patient.get("visit_notes", [])).lower()

    # Question: has_obesity_diagnosis
    expected_answers["has_obesity_diagnosis"] = {
        "value": "obesity" in notes_text or "bmi" in notes_text,
        "rationale": "Based on visit notes mentioning obesity or BMI",
    }

    # Question: bmi_value
    # Try to extract BMI from notes
    bmi_found = False
    for note in patient.get("visit_notes", []):
        if "bmi" in note.lower():
            # Simple extraction - in real case would use regex
            expected_answers["bmi_value"] = {
                "value": "30+" if "obesity" in note.lower() else "unknown",
                "rationale": "Extracted from visit notes",
            }
            bmi_found = True
            break
    if not bmi_found:
        expected_answers["bmi_value"] = {
            "value": "unknown",
            "rationale": "BMI not documented in visit notes",
        }

    # Question: has_diabetes
    expected_answers["has_diabetes"] = {
        "value": "diabetes" in notes_text
        or "t2dm" in notes_text
        or "type 2" in notes_text,
        "rationale": "Based on visit notes mentioning diabetes",
    }

    # Question: has_cardiovascular_disease
    expected_answers["has_cardiovascular_disease"] = {
        "value": "cardiovascular" in notes_text
        or "heart" in notes_text
        or "cvd" in notes_text,
        "rationale": "Based on visit notes mentioning cardiovascular conditions",
    }

    # Question: previous_weight_loss_attempts
    expected_answers["previous_weight_loss_attempts"] = {
        "value": "diet" in notes_text
        or "exercise" in notes_text
        or "weight loss" in notes_text,
        "rationale": "Based on documented weight loss attempts in notes",
    }

    # Question: contraindications_present
    expected_answers["contraindications_present"] = {
        "value": "contraindication" in notes_text or "allergy" in notes_text,
        "rationale": "Based on documented contraindications or allergies",
    }

    # Question: current_medications
    rx = patient.get("prescription", {})
    expected_answers["current_medications"] = {
        "value": f"{rx.get('medication', 'unknown')} {rx.get('dosage', '')}".strip(),
        "rationale": "From current prescription record",
    }

    # Question: insurance_prior_auth_required
    expected_answers["insurance_prior_auth_required"] = {
        "value": True,  # Assume always required for this medication
        "rationale": "Zepbound typically requires prior authorization",
    }

    # Question: patient_tried_lifestyle_modifications
    expected_answers["patient_tried_lifestyle_modifications"] = {
        "value": "lifestyle" in notes_text
        or "diet" in notes_text
        or "exercise" in notes_text,
        "rationale": "Based on documented lifestyle modification attempts",
    }

    # Question: duration_of_obesity
    expected_answers["duration_of_obesity"] = {
        "value": "chronic" if "chronic" in notes_text else "unknown",
        "rationale": "Based on visit note documentation",
    }

    test_case = {
        "patient": patient,
        "question_set": {
            "name": "Zepbound Prior Authorization",
            "questions": questions,
        },
        "expected_answers": expected_answers,
    }

    mock_test_cases.append(test_case)

# Save mock test data
output_path = Path(__file__).parent / "mock_test_data.json"
with open(output_path, "w") as f:
    json.dump(mock_test_cases, f, indent=2)

print(f"Generated {len(mock_test_cases)} mock test cases")
print(f"Saved to: {output_path}")
