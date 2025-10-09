"""
Evaluation pipeline for prior authorization form auto-fill.
Computes F1 score and other metrics.
"""

import json
from collections import defaultdict
from pathlib import Path

import requests

# Configuration
API_BASE = "http://localhost:8000"
ANSWERS_URL = f"{API_BASE}/answers"


def load_test_data() -> list[dict]:
    """Load mock test data."""
    test_data_path = Path(__file__).parent / "mock_test_data.json"
    if not test_data_path.exists():
        raise FileNotFoundError(
            f"Mock test data not found at {test_data_path}. "
            "Run generate_mock_data.py first."
        )

    with open(test_data_path) as f:
        return json.load(f)


def normalize_value(value) -> str:
    """Normalize answer values for comparison."""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value).strip().lower()


def compute_metrics(
    predicted: dict[str, any], expected: dict[str, dict]
) -> dict[str, float]:
    """
    Compute precision, recall, and F1 score.

    For boolean questions: standard binary classification metrics
    For text questions: exact match or partial match
    """
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0

    all_keys = set(predicted.keys()) | set(expected.keys())

    for key in all_keys:
        pred_val = normalize_value(predicted.get(key, "unknown"))
        exp_val = normalize_value(expected.get(key, {}).get("value", "unknown"))

        # For boolean-like values
        if pred_val in ("true", "false") and exp_val in ("true", "false"):
            if pred_val == "true" and exp_val == "true":
                true_positives += 1
            elif pred_val == "true" and exp_val == "false":
                false_positives += 1
            elif pred_val == "false" and exp_val == "true":
                false_negatives += 1
            else:
                true_negatives += 1
        # For text values - exact match
        elif pred_val == exp_val:
            true_positives += 1
        # Partial match for text (if expected is substring of predicted or vice versa)
        elif pred_val in exp_val or exp_val in pred_val:
            true_positives += 0.5  # Partial credit
            false_positives += 0.5
        else:
            false_positives += 1
            if exp_val != "unknown":
                false_negatives += 1

    # Compute metrics
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0
    )
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )
    accuracy = (true_positives + true_negatives) / len(all_keys) if all_keys else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
    }


def run_evaluation(validate: bool = False) -> dict[str, any]:
    """
    Run evaluation on all test cases.

    Args:
        validate: Whether to enable validation pass

    Returns:
        Dictionary with aggregate metrics and per-case results
    """
    test_cases = load_test_data()
    results = []
    aggregate_metrics = defaultdict(float)

    print(f"Running evaluation on {len(test_cases)} test cases...")
    print(f"Validation pass: {'enabled' if validate else 'disabled'}")
    print("-" * 60)

    for idx, test_case in enumerate(test_cases, 1):
        patient = test_case["patient"]
        question_set = test_case["question_set"]
        expected_answers = test_case["expected_answers"]

        patient_name = f"{patient['first_name']} {patient['last_name']}"
        print(f"\n[{idx}/{len(test_cases)}] Testing patient: {patient_name}")

        # Build API payload
        payload = {
            "patient": patient,
            "question_set": question_set,
            "validate": validate,
        }

        try:
            # Call API
            response = requests.post(ANSWERS_URL, json=payload, timeout=90)

            if response.status_code != 200:
                print(f"  ❌ API error {response.status_code}: {response.text}")
                results.append(
                    {
                        "patient": patient_name,
                        "error": f"API error {response.status_code}",
                        "metrics": None,
                    }
                )
                continue

            # Parse response
            data = response.json()
            predicted_answers = {}

            for ans in data.get("answers", []):
                q = ans.get("question", {})
                key = q.get("key")
                value = ans.get("value")
                predicted_answers[key] = value

            # Compute metrics
            metrics = compute_metrics(predicted_answers, expected_answers)

            print(
                f"  ✓ F1: {metrics['f1']:.3f} | Precision: {metrics['precision']:.3f} | Recall: {metrics['recall']:.3f}"
            )

            # Aggregate
            for metric_name, metric_value in metrics.items():
                aggregate_metrics[metric_name] += metric_value

            results.append(
                {
                    "patient": patient_name,
                    "predicted": predicted_answers,
                    "expected": {k: v["value"] for k, v in expected_answers.items()},
                    "metrics": metrics,
                }
            )

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"patient": patient_name, "error": str(e), "metrics": None})

    # Compute averages
    num_successful = sum(1 for r in results if r.get("metrics") is not None)
    avg_metrics = {
        k: v / num_successful if num_successful > 0 else 0
        for k, v in aggregate_metrics.items()
    }

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total test cases: {len(test_cases)}")
    print(f"Successful: {num_successful}")
    print(f"Failed: {len(test_cases) - num_successful}")
    print("\nAverage Metrics:")
    print(f"  F1 Score:  {avg_metrics['f1']:.3f}")
    print(f"  Precision: {avg_metrics['precision']:.3f}")
    print(f"  Recall:    {avg_metrics['recall']:.3f}")
    print(f"  Accuracy:  {avg_metrics['accuracy']:.3f}")
    print("=" * 60)

    return {
        "summary": avg_metrics,
        "results": results,
        "num_cases": len(test_cases),
        "num_successful": num_successful,
    }


def save_results(results: dict, output_path: str = "eval_results.json"):
    """Save evaluation results to file."""
    output_file = Path(__file__).parent / output_path
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run evaluation pipeline")
    parser.add_argument(
        "--validate", action="store_true", help="Enable validation pass"
    )
    parser.add_argument(
        "--output", default="eval_results.json", help="Output file for results"
    )

    args = parser.parse_args()

    # Run evaluation
    results = run_evaluation(validate=args.validate)

    # Save results
    save_results(results, args.output)
