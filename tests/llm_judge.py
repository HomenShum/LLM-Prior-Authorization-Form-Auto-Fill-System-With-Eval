"""
LLM-as-a-Judge evaluation module for validating answer quality.

Uses an LLM to judge whether predicted answers match expected answers,
providing more nuanced evaluation than simple string matching.
"""

import os
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel


class JudgmentResult(BaseModel):
    """Result of LLM judgment for a single answer."""

    matches: bool
    confidence: Literal["high", "medium", "low"]
    reasoning: str


class AnswerJudgment(BaseModel):
    """Complete judgment for comparing predicted vs expected answer."""

    question_key: str
    question_text: str
    expected_value: str
    predicted_value: str
    judgment: JudgmentResult


class ValidationJudgment(BaseModel):
    """Judgment for validation pass - comparing initial vs changed result."""

    question_key: str
    question_text: str
    expected_value: str
    initial_value: str
    changed_value: str | None
    change_needed: bool | None
    change_rationale: str | None
    initial_judgment: JudgmentResult
    changed_judgment: JudgmentResult | None
    validation_improved_result: bool


def judge_answer(
    question_key: str,
    question_text: str,
    expected_value: str,
    predicted_value: str,
    client: OpenAI | None = None,
) -> JudgmentResult:
    """
    Use LLM to judge if predicted answer matches expected answer.

    Args:
        question_key: The question identifier
        question_text: The full question text
        expected_value: The expected/ground truth answer
        predicted_value: The predicted answer from the model
        client: OpenAI client (creates new one if None)

    Returns:
        JudgmentResult with match status, confidence, and reasoning
    """
    if client is None:
        client = OpenAI()

    system_prompt = """You are an expert medical records evaluator. Your task is to determine if a predicted answer matches an expected answer for a prior authorization question.

Consider the following when judging:
1. Semantic equivalence (e.g., "yes" = "true", "no" = "false")
2. Numerical equivalence (e.g., "37.4" = "37.4 kg/m²")
3. Reasonable variations in phrasing (e.g., "Type 2 Diabetes" = "diabetes mellitus type 2")
4. Clinical accuracy and completeness
5. Whether the answer would be acceptable for prior authorization purposes

Be strict but fair. Minor formatting differences are acceptable, but substantive differences in meaning are not."""

    user_prompt = f"""Question: {question_text}
Question Key: {question_key}

Expected Answer: {expected_value}
Predicted Answer: {predicted_value}

Does the predicted answer match the expected answer? Consider semantic equivalence, clinical accuracy, and whether both answers would lead to the same prior authorization decision.

Provide your judgment with:
- matches: true/false
- confidence: high/medium/low
- reasoning: brief explanation of your decision"""

    try:
        completion = client.beta.chat.completions.parse(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=JudgmentResult,
        )

        result = completion.choices[0].message.parsed
        return result

    except Exception as e:
        # Fallback to simple string comparison if LLM fails
        return JudgmentResult(
            matches=str(expected_value).strip().lower()
            == str(predicted_value).strip().lower(),
            confidence="low",
            reasoning=f"LLM judgment failed ({str(e)}), using simple string comparison",
        )


def judge_validation_result(
    question_key: str,
    question_text: str,
    expected_value: str,
    initial_value: str,
    changed_value: str | None,
    change_needed: bool | None,
    change_rationale: str | None,
    client: OpenAI | None = None,
) -> ValidationJudgment:
    """
    Judge both initial and validation-corrected results.

    Args:
        question_key: The question identifier
        question_text: The full question text
        expected_value: The expected/ground truth answer
        initial_value: The initial answer before validation
        changed_value: The corrected answer after validation (if changed)
        change_needed: Whether validation determined a change was needed
        change_rationale: Explanation for the change
        client: OpenAI client (creates new one if None)

    Returns:
        ValidationJudgment with judgments for both initial and changed results
    """
    if client is None:
        client = OpenAI()

    # Judge initial result
    initial_judgment = judge_answer(
        question_key, question_text, expected_value, initial_value, client
    )

    # Judge changed result if it exists
    changed_judgment = None
    validation_improved = False

    if change_needed and changed_value is not None:
        changed_judgment = judge_answer(
            question_key, question_text, expected_value, changed_value, client
        )

        # Determine if validation improved the result
        # Improvement means: initial was wrong, changed is correct
        validation_improved = (
            not initial_judgment.matches
        ) and changed_judgment.matches

    return ValidationJudgment(
        question_key=question_key,
        question_text=question_text,
        expected_value=expected_value,
        initial_value=initial_value,
        changed_value=changed_value,
        change_needed=change_needed,
        change_rationale=change_rationale,
        initial_judgment=initial_judgment,
        changed_judgment=changed_judgment,
        validation_improved_result=validation_improved,
    )


def compute_llm_judge_metrics(judgments: list[AnswerJudgment]) -> dict:
    """
    Compute metrics based on LLM judgments.

    Args:
        judgments: List of AnswerJudgment objects

    Returns:
        Dictionary with accuracy, high-confidence accuracy, and other metrics
    """
    if not judgments:
        return {
            "total_questions": 0,
            "matches": 0,
            "accuracy": 0.0,
            "high_confidence_matches": 0,
            "high_confidence_total": 0,
            "high_confidence_accuracy": 0.0,
        }

    total = len(judgments)
    matches = sum(1 for j in judgments if j.judgment.matches)
    high_conf_judgments = [j for j in judgments if j.judgment.confidence == "high"]
    high_conf_matches = sum(1 for j in high_conf_judgments if j.judgment.matches)

    return {
        "total_questions": total,
        "matches": matches,
        "accuracy": matches / total if total > 0 else 0.0,
        "high_confidence_matches": high_conf_matches,
        "high_confidence_total": len(high_conf_judgments),
        "high_confidence_accuracy": (
            high_conf_matches / len(high_conf_judgments) if high_conf_judgments else 0.0
        ),
    }


def compute_validation_metrics(judgments: list[ValidationJudgment]) -> dict:
    """
    Compute metrics for validation pass evaluation.

    Args:
        judgments: List of ValidationJudgment objects

    Returns:
        Dictionary with validation-specific metrics
    """
    if not judgments:
        return {
            "total_questions": 0,
            "initial_accuracy": 0.0,
            "final_accuracy": 0.0,
            "validation_improvements": 0,
            "validation_degradations": 0,
            "net_improvement": 0.0,
        }

    total = len(judgments)
    initial_correct = sum(1 for j in judgments if j.initial_judgment.matches)

    # Final accuracy uses changed result if available, otherwise initial
    final_correct = 0
    for j in judgments:
        if j.changed_judgment is not None:
            if j.changed_judgment.matches:
                final_correct += 1
        elif j.initial_judgment.matches:
            final_correct += 1

    # Count improvements and degradations
    improvements = sum(1 for j in judgments if j.validation_improved_result)
    degradations = sum(
        1
        for j in judgments
        if j.changed_judgment is not None
        and j.initial_judgment.matches
        and not j.changed_judgment.matches
    )

    return {
        "total_questions": total,
        "initial_correct": initial_correct,
        "initial_accuracy": initial_correct / total if total > 0 else 0.0,
        "final_correct": final_correct,
        "final_accuracy": final_correct / total if total > 0 else 0.0,
        "validation_improvements": improvements,
        "validation_degradations": degradations,
        "net_improvement": (final_correct - initial_correct) / total
        if total > 0
        else 0.0,
        "improvement_rate": improvements / total if total > 0 else 0.0,
    }
