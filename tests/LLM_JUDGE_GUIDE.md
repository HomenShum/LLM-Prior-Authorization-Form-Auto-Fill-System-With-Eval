# LLM-as-a-Judge Evaluation Guide

## Overview

The LLM-as-a-Judge evaluation system provides a more sophisticated way to validate answer quality compared to simple string matching. It uses an LLM to determine if predicted answers semantically match expected answers, accounting for variations in phrasing, clinical terminology, and formatting.

## Why Use LLM Judge?

### Problems with String-Based Comparison

Traditional string matching fails in many cases:

| Expected Answer | Predicted Answer | String Match | Should Match? |
|----------------|------------------|--------------|---------------|
| "yes" | "true" | ❌ | ✅ |
| "37.4" | "37.4 kg/m²" | ❌ | ✅ |
| "Type 2 Diabetes" | "diabetes mellitus type 2" | ❌ | ✅ |
| "hypertension" | "high blood pressure" | ❌ | ✅ |
| "55" | "55 years" | ❌ | ✅ |

### LLM Judge Advantages

✅ **Semantic Understanding**: Recognizes equivalent meanings  
✅ **Clinical Knowledge**: Understands medical terminology  
✅ **Context Awareness**: Considers prior authorization context  
✅ **Confidence Levels**: Provides high/medium/low confidence  
✅ **Reasoning**: Explains each judgment decision  
✅ **Validation Tracking**: Tracks improvements from validation pass  

## Quick Start

### 1. Run Evaluation Without Validation

```bash
python -m tests.eval_pipeline_llm_judge --mode without_validation --limit 3
```

This evaluates the initial LLM responses against expected answers.

### 2. Run Evaluation With Validation

```bash
python -m tests.eval_pipeline_llm_judge --mode with_validation --limit 3
```

This evaluates both initial and validation-corrected responses, showing:
- Which answers were improved by validation
- Which answers were degraded (validation made them worse)
- Net improvement from validation pass

### 3. Run Both Modes

```bash
python -m tests.eval_pipeline_llm_judge --mode both
```

Runs both evaluations and saves separate result files.

## Understanding the Output

### Without Validation Output

```
EVALUATION WITHOUT VALIDATION PASS (LLM Judge)
======================================================================

[1/3] Testing patient: Isaiah Reed
  ✓ Accuracy: 78.3% (18/23 correct)

[2/3] Testing patient: Elizabeth Munoz
  ✓ Accuracy: 82.6% (19/23 correct)

----------------------------------------------------------------------
OVERALL METRICS (Without Validation)
----------------------------------------------------------------------
Total Questions: 69
Correct Answers: 55
Accuracy: 79.7%
High-Confidence Accuracy: 85.4% (35/41)
======================================================================
```

**Key Metrics:**
- **Accuracy**: Overall percentage of correct answers
- **High-Confidence Accuracy**: Accuracy when LLM is highly confident (more reliable)

### With Validation Output

```
EVALUATION WITH VALIDATION PASS (LLM Judge)
======================================================================

[1/3] Testing patient: Isaiah Reed
  ✓ Validation improved 'bmi'
    Initial: 37.4 (wrong)
    Changed: 37.4 kg/m² (correct)
  ✓ Initial: 78.3% | Final: 82.6% | Improvements: 1

----------------------------------------------------------------------
OVERALL METRICS (With Validation)
----------------------------------------------------------------------
Total Questions: 69
Initial Accuracy: 79.7%
Final Accuracy: 84.1%
Validation Improvements: 3
Validation Degradations: 0
Net Improvement: +4.4%
Improvement Rate: 4.3%
======================================================================
```

**Key Metrics:**
- **Initial Accuracy**: Before validation pass
- **Final Accuracy**: After validation corrections
- **Validation Improvements**: Answers corrected from wrong to right
- **Validation Degradations**: Answers changed from right to wrong
- **Net Improvement**: Overall improvement percentage
- **Improvement Rate**: Percentage of questions improved

## Interpreting Results

### Good Validation Performance

```
Initial Accuracy: 75.0%
Final Accuracy: 85.0%
Validation Improvements: 10
Validation Degradations: 0
Net Improvement: +10.0%
```

✅ Validation is working well - improving accuracy without degrading correct answers

### Problematic Validation

```
Initial Accuracy: 80.0%
Final Accuracy: 78.0%
Validation Improvements: 2
Validation Degradations: 4
Net Improvement: -2.0%
```

⚠️ Validation is making things worse - need to investigate validation prompt or logic

### Neutral Validation

```
Initial Accuracy: 82.0%
Final Accuracy: 82.0%
Validation Improvements: 0
Validation Degradations: 0
Net Improvement: 0.0%
```

ℹ️ Validation isn't changing anything - either initial answers are very good or validation is too conservative

## Detailed Results

Results are saved to JSON files with full details:

```json
{
  "mode": "with_validation",
  "overall_metrics": {
    "total_questions": 69,
    "initial_accuracy": 0.797,
    "final_accuracy": 0.841,
    "validation_improvements": 3,
    "validation_degradations": 0,
    "net_improvement": 0.044
  },
  "results": [
    {
      "patient": "Isaiah Reed",
      "judgments": [
        {
          "question_key": "bmi",
          "question_text": "What is the patient's BMI?",
          "expected_value": "37.4 kg/m²",
          "initial_value": "37.4",
          "changed_value": "37.4 kg/m²",
          "change_needed": true,
          "change_rationale": "Added unit for completeness",
          "initial_judgment": {
            "matches": false,
            "confidence": "medium",
            "reasoning": "Missing unit of measurement"
          },
          "changed_judgment": {
            "matches": true,
            "confidence": "high",
            "reasoning": "Exact match with proper units"
          },
          "validation_improved_result": true
        }
      ]
    }
  ]
}
```

## Use Cases

### 1. Evaluating Model Performance

Compare different models or prompts:

```bash
# Test with gpt-4o-mini
OPENAI_MODEL=gpt-4o-mini python -m tests.eval_pipeline_llm_judge --mode both

# Test with gpt-4o
OPENAI_MODEL=gpt-4o python -m tests.eval_pipeline_llm_judge --mode both
```

### 2. Validating Validation Pass

Check if validation pass improves results:

```bash
python -m tests.eval_pipeline_llm_judge --mode both
```

Look for positive net improvement and low degradation count.

### 3. Identifying Problem Areas

Review the detailed JSON output to find:
- Questions with low confidence judgments
- Questions where validation degraded results
- Patterns in incorrect answers

### 4. Testing Prompt Changes

After modifying prompts in `app/main.py`:

```bash
# Restart server
uvicorn app.main:app --reload

# Re-run evaluation
python -m tests.eval_pipeline_llm_judge --mode both
```

Compare metrics before and after the change.

## Best Practices

1. **Start Small**: Use `--limit 3` for quick testing
2. **Run Both Modes**: Always compare with and without validation
3. **Check Confidence**: Pay attention to high-confidence accuracy
4. **Review Degradations**: Investigate any validation degradations
5. **Examine Reasoning**: Read the LLM's reasoning for mismatches
6. **Iterate**: Use insights to improve prompts and validation logic

## Troubleshooting

### Low Accuracy (<50%)

Possible causes:
- Poor quality expected answers (ground truth)
- Model not understanding questions
- Prompt needs improvement
- Wrong model being used

### High Degradation Rate

Possible causes:
- Validation prompt is too aggressive
- Validation is second-guessing correct answers
- Need to adjust validation instructions

### LLM Judge Errors

If LLM judge fails, it falls back to simple string comparison with low confidence. Check:
- OpenAI API key is set
- API quota is not exceeded
- Network connectivity

## Advanced Usage

### Custom Evaluation

You can use the `llm_judge` module directly in your own scripts:

```python
from tests.llm_judge import judge_answer, judge_validation_result
from openai import OpenAI

client = OpenAI()

# Judge a single answer
result = judge_answer(
    question_key="age",
    question_text="What is the patient's age?",
    expected_value="55 years",
    predicted_value="55",
    client=client
)

print(f"Matches: {result.matches}")
print(f"Confidence: {result.confidence}")
print(f"Reasoning: {result.reasoning}")
```

### Batch Processing

Process multiple test cases programmatically:

```python
from tests.eval_pipeline_llm_judge import load_test_data, evaluate_with_validation
from openai import OpenAI

test_cases = load_test_data()
client = OpenAI()

results = evaluate_with_validation(test_cases[:5], client)
print(f"Final Accuracy: {results['overall_metrics']['final_accuracy']:.1%}")
```

## Summary

The LLM-as-a-Judge evaluation system provides:
- ✅ More accurate evaluation than string matching
- ✅ Insights into validation pass effectiveness
- ✅ Confidence levels and reasoning for each judgment
- ✅ Detailed tracking of improvements and degradations

Use it to validate your prior authorization system's accuracy and continuously improve its performance.

