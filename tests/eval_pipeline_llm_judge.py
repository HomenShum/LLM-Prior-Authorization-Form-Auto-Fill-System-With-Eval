"""
Enhanced evaluation pipeline using LLM-as-a-Judge for answer validation.

This pipeline evaluates both initial and validation-corrected answers using
an LLM to judge semantic equivalence rather than simple string matching.
"""

import json
from pathlib import Path

import requests
from llm_judge import (
    AnswerJudgment,
    compute_llm_judge_metrics,
    compute_validation_metrics,
    judge_answer,
    judge_validation_result,
)
from openai import OpenAI

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


def evaluate_without_validation(test_cases: list[dict], client: OpenAI) -> dict:
    """
    Evaluate answers without validation pass using LLM judge.

    Args:
        test_cases: List of test case dictionaries
        client: OpenAI client for LLM judging

    Returns:
        Dictionary with results and metrics
    """
    print("\n" + "=" * 70)
    print("EVALUATION WITHOUT VALIDATION PASS (LLM Judge)")
    print("=" * 70)

    all_judgments = []
    results = []

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
            "validate": False,
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
                    }
                )
                continue

            # Parse response
            data = response.json()
            case_judgments = []

            for ans in data.get("answers", []):
                q = ans.get("question", {})
                key = q.get("key")
                question_text = q.get("content", "")
                predicted_value = ans.get("value")

                # Get expected value
                expected_entry = expected_answers.get(key, {})
                expected_value = expected_entry.get("value", "unknown")

                # Judge the answer
                judgment_result = judge_answer(
                    question_key=key,
                    question_text=question_text,
                    expected_value=str(expected_value),
                    predicted_value=str(predicted_value),
                    client=client,
                )

                judgment = AnswerJudgment(
                    question_key=key,
                    question_text=question_text,
                    expected_value=str(expected_value),
                    predicted_value=str(predicted_value),
                    judgment=judgment_result,
                )

                case_judgments.append(judgment)
                all_judgments.append(judgment)

            # Compute metrics for this case
            case_metrics = compute_llm_judge_metrics(case_judgments)
            print(
                f"  ✓ Accuracy: {case_metrics['accuracy']:.1%} "
                f"({case_metrics['matches']}/{case_metrics['total_questions']} correct)"
            )

            results.append(
                {
                    "patient": patient_name,
                    "judgments": [j.model_dump() for j in case_judgments],
                    "metrics": case_metrics,
                }
            )

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"patient": patient_name, "error": str(e)})

    # Compute overall metrics
    overall_metrics = compute_llm_judge_metrics(all_judgments)

    print("\n" + "-" * 70)
    print("OVERALL METRICS (Without Validation)")
    print("-" * 70)
    print(f"Total Questions: {overall_metrics['total_questions']}")
    print(f"Correct Answers: {overall_metrics['matches']}")
    print(f"Accuracy: {overall_metrics['accuracy']:.1%}")
    print(
        f"High-Confidence Accuracy: {overall_metrics['high_confidence_accuracy']:.1%} "
        f"({overall_metrics['high_confidence_matches']}/{overall_metrics['high_confidence_total']})"
    )
    print("=" * 70)

    return {
        "mode": "without_validation",
        "overall_metrics": overall_metrics,
        "results": results,
    }


def evaluate_with_validation(test_cases: list[dict], client: OpenAI) -> dict:
    """
    Evaluate answers with validation pass using LLM judge.

    Compares both initial and validation-corrected answers.

    Args:
        test_cases: List of test case dictionaries
        client: OpenAI client for LLM judging

    Returns:
        Dictionary with results and metrics
    """
    print("\n" + "=" * 70)
    print("EVALUATION WITH VALIDATION PASS (LLM Judge)")
    print("=" * 70)

    all_judgments = []
    results = []

    for idx, test_case in enumerate(test_cases, 1):
        patient = test_case["patient"]
        question_set = test_case["question_set"]
        expected_answers = test_case["expected_answers"]

        patient_name = f"{patient['first_name']} {patient['last_name']}"
        print(f"\n[{idx}/{len(test_cases)}] Testing patient: {patient_name}")

        # Build API payload with validation enabled
        payload = {
            "patient": patient,
            "question_set": question_set,
            "validate": True,
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
                    }
                )
                continue

            # Parse response
            data = response.json()
            case_judgments = []

            for ans in data.get("answers", []):
                q = ans.get("question", {})
                key = q.get("key")
                question_text = q.get("content", "")
                initial_value = ans.get("value")
                changed_value = ans.get("changed_result")
                change_needed = ans.get("change_needed")
                change_rationale = ans.get("change_rationale")

                # Get expected value
                expected_entry = expected_answers.get(key, {})
                expected_value = expected_entry.get("value", "unknown")

                # Judge both initial and changed results
                judgment = judge_validation_result(
                    question_key=key,
                    question_text=question_text,
                    expected_value=str(expected_value),
                    initial_value=str(initial_value),
                    changed_value=str(changed_value)
                    if changed_value is not None
                    else None,
                    change_needed=change_needed,
                    change_rationale=change_rationale,
                    client=client,
                )

                case_judgments.append(judgment)
                all_judgments.append(judgment)

            # Compute metrics for this case
            case_metrics = compute_validation_metrics(case_judgments)
            print(
                f"  ✓ Initial: {case_metrics['initial_accuracy']:.1%} | "
                f"Final: {case_metrics['final_accuracy']:.1%} | "
                f"Improvements: {case_metrics['validation_improvements']}"
            )

            results.append(
                {
                    "patient": patient_name,
                    "judgments": [j.model_dump() for j in case_judgments],
                    "metrics": case_metrics,
                }
            )

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"patient": patient_name, "error": str(e)})

    # Compute overall metrics
    overall_metrics = compute_validation_metrics(all_judgments)

    print("\n" + "-" * 70)
    print("OVERALL METRICS (With Validation)")
    print("-" * 70)
    print(f"Total Questions: {overall_metrics['total_questions']}")
    print(f"Initial Accuracy: {overall_metrics['initial_accuracy']:.1%}")
    print(f"Final Accuracy: {overall_metrics['final_accuracy']:.1%}")
    print(f"Validation Improvements: {overall_metrics['validation_improvements']}")
    print(f"Validation Degradations: {overall_metrics['validation_degradations']}")
    print(f"Net Improvement: {overall_metrics['net_improvement']:+.1%}")
    print(f"Improvement Rate: {overall_metrics['improvement_rate']:.1%}")
    print("=" * 70)

    return {
        "mode": "with_validation",
        "overall_metrics": overall_metrics,
        "results": results,
    }


def save_results(results: dict, output_path: str):
    """Save evaluation results to file."""
    output_file = Path(__file__).parent / output_path
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run evaluation pipeline with LLM-as-a-Judge"
    )
    parser.add_argument(
        "--mode",
        choices=["without_validation", "with_validation", "both"],
        default="both",
        help="Evaluation mode",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of test cases (for testing)",
    )

    args = parser.parse_args()

    # Load test data
    test_cases = load_test_data()
    if args.limit:
        test_cases = test_cases[: args.limit]
        print(f"Limited to {args.limit} test cases")

    # Initialize OpenAI client
    client = OpenAI()

    # Run evaluations
    if args.mode in ["without_validation", "both"]:
        results_no_val = evaluate_without_validation(test_cases, client)
        save_results(
            results_no_val,
            f"{args.output_dir}/eval_results_no_validation_llm_judge.json",
        )

    if args.mode in ["with_validation", "both"]:
        results_with_val = evaluate_with_validation(test_cases, client)
        save_results(
            results_with_val,
            f"{args.output_dir}/eval_results_with_validation_llm_judge.json",
        )

    print("\n✅ Evaluation complete!")
