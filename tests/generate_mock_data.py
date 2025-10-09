"""
Generate mock test data based on sample patient data.
Creates ground truth answers for evaluation by calling the API.

NOTE: This uses the actual API to generate expected answers, which provides
a baseline for comparison. For production use, you should have human-validated
ground truth answers.
"""

import json
from pathlib import Path

import requests

# Configuration
API_URL = "http://localhost:8000/answers"

# Load sample data
sample_dir = Path(__file__).parent.parent / "sample_data"
with open(sample_dir / "patient_data.json", encoding="utf-8") as f:
    patients = json.load(f)

with open(sample_dir / "zepbound_question_set.json", encoding="utf-8") as f:
    questions = json.load(f)

print(f"Loaded {len(patients)} patients and {len(questions)} questions")
print("\nGenerating expected answers by calling API...")
print("=" * 70)

# Generate ground truth answers for each patient by calling the API
mock_test_cases = []

for idx, patient in enumerate(patients, 1):
    patient_name = f"{patient['first_name']} {patient['last_name']}"
    print(f"\n[{idx}/{len(patients)}] Processing patient: {patient_name}")

    # Call API to get answers (without validation for baseline)
    payload = {
        "patient": patient,
        "question_set": {
            "name": "Zepbound Prior Authorization",
            "questions": questions,
        },
        "validate": False,  # Use initial answers as baseline
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=120)

        if response.status_code != 200:
            print(f"  ❌ API error {response.status_code}: {response.text}")
            continue

        data = response.json()
        expected_answers = {}

        # Extract answers from API response
        for ans in data.get("answers", []):
            q = ans.get("question", {})
            key = q.get("key")
            value = ans.get("value")
            rationale = ans.get("rationale", "")

            expected_answers[key] = {"value": value, "rationale": rationale}

        print(f"  ✓ Generated {len(expected_answers)} expected answers")

        test_case = {
            "patient": patient,
            "question_set": {
                "name": "Zepbound Prior Authorization",
                "questions": questions,
            },
            "expected_answers": expected_answers,
        }

        mock_test_cases.append(test_case)

    except Exception as e:
        print(f"  ❌ Error: {e}")
        continue

# Save mock test data
output_path = Path(__file__).parent / "mock_test_data.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(mock_test_cases, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 70)
print(f"✅ Generated {len(mock_test_cases)} mock test cases")
print(f"📁 Saved to: {output_path}")
print("\n⚠️  NOTE: These are API-generated answers, not human-validated ground truth.")
print("   For production use, have clinical experts review and validate these answers.")
