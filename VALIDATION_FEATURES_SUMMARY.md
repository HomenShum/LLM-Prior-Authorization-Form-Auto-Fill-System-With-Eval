# Validation Features Summary

This document summarizes the validation features implemented for the prior authorization system.

## Feature 1: Validation Metadata Fields

### Overview
When validation pass is enabled (`validate=true`), the API now returns detailed metadata about what was changed during validation and why.

### New Fields in Response

Each answer in the response now includes:

```json
{
  "question": {...},
  "value": "original value",
  "rationale": "why this value was chosen",
  "change_needed": true,
  "changed_result": "corrected value",
  "change_rationale": "why the change was made"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `change_needed` | `bool \| null` | Whether validation determined a change was necessary |
| `changed_result` | `str \| bool \| null` | The corrected value if a change was made |
| `change_rationale` | `str \| null` | Explanation of why the change was necessary |

### Example Response

```json
{
  "answers": [
    {
      "question": {
        "type": "text",
        "key": "bmi",
        "content": "What is the patient's BMI?"
      },
      "value": "37.4",
      "rationale": "Extracted from visit notes",
      "change_needed": true,
      "changed_result": "37.4 kg/m²",
      "change_rationale": "Added unit of measurement for completeness and clarity"
    },
    {
      "question": {
        "type": "boolean",
        "key": "has_diabetes",
        "content": "Does the patient have diabetes?"
      },
      "value": true,
      "rationale": "Patient has Type 2 Diabetes per visit notes",
      "change_needed": false,
      "changed_result": null,
      "change_rationale": null
    }
  ]
}
```

### Implementation Details

**Modified Files:**
- `app/models.py`: Added validation fields to `Answer` model
- `app/main.py`: 
  - Added validation fields to `AnswerItem` model
  - Updated validation prompt to instruct LLM to populate these fields
  - Modified `_answers_to_output()` to pass through validation metadata

**Validation Prompt Enhancement:**
```python
system = (
    "You are a clinical QA validator. Re-evaluate the initial answers strictly against the patient context. "
    "Correct any mistakes and ensure each answer is chart-supported. "
    "For each answer, you must indicate whether a change was needed:\n"
    "- If the initial answer was correct, set 'change_needed' to false and keep the original 'value' and 'rationale'.\n"
    "- If the initial answer needs correction, set 'change_needed' to true, provide the corrected value in 'changed_result', "
    "and explain why the change was necessary in 'change_rationale'.\n"
    "Return the same JSON schema with these validation fields populated."
)
```

### Usage

Enable validation in API request:

```python
payload = {
    "patient": patient_data,
    "question_set": questions,
    "validate": True  # Enable validation pass
}

response = requests.post("/answers", json=payload)
data = response.json()

# Check for validation changes
for answer in data["answers"]:
    if answer.get("change_needed"):
        print(f"Question: {answer['question']['key']}")
        print(f"  Original: {answer['value']}")
        print(f"  Corrected: {answer['changed_result']}")
        print(f"  Reason: {answer['change_rationale']}")
```

## Feature 2: LLM-as-a-Judge Evaluation

### Overview
A sophisticated evaluation system that uses an LLM to judge whether predicted answers match expected answers, accounting for semantic equivalence rather than just string matching.

### Why LLM Judge?

**Problems with String Matching:**
- "yes" ≠ "true" (but they mean the same)
- "37.4" ≠ "37.4 kg/m²" (but they're equivalent)
- "Type 2 Diabetes" ≠ "diabetes mellitus type 2" (same condition)

**LLM Judge Advantages:**
- ✅ Semantic understanding
- ✅ Clinical knowledge
- ✅ Context awareness
- ✅ Confidence levels
- ✅ Reasoning provided

### Components

#### 1. Core Module (`tests/llm_judge.py`)

**Key Functions:**
- `judge_answer()`: Judge if predicted answer matches expected answer
- `judge_validation_result()`: Judge both initial and validation-corrected answers
- `compute_llm_judge_metrics()`: Compute accuracy metrics
- `compute_validation_metrics()`: Compute validation-specific metrics

**Structured Output Models:**
```python
class JudgmentResult(BaseModel):
    matches: bool
    confidence: Literal["high", "medium", "low"]
    reasoning: str

class ValidationJudgment(BaseModel):
    question_key: str
    expected_value: str
    initial_value: str
    changed_value: str | None
    change_needed: bool | None
    initial_judgment: JudgmentResult
    changed_judgment: JudgmentResult | None
    validation_improved_result: bool
```

#### 2. Evaluation Pipeline (`tests/eval_pipeline_llm_judge.py`)

**Features:**
- Evaluates answers with and without validation
- Tracks validation improvements and degradations
- Provides detailed metrics and reasoning
- Saves results to JSON

**Usage:**
```bash
# Evaluate without validation
python -m tests.eval_pipeline_llm_judge --mode without_validation

# Evaluate with validation
python -m tests.eval_pipeline_llm_judge --mode with_validation

# Run both modes
python -m tests.eval_pipeline_llm_judge --mode both

# Limit test cases
python -m tests.eval_pipeline_llm_judge --mode both --limit 3
```

### Metrics

#### Without Validation
- **Accuracy**: Overall percentage of correct answers
- **High-Confidence Accuracy**: Accuracy for high-confidence judgments
- **Total Questions**: Number evaluated

#### With Validation
- **Initial Accuracy**: Before validation
- **Final Accuracy**: After validation
- **Validation Improvements**: Answers corrected (wrong → right)
- **Validation Degradations**: Answers worsened (right → wrong)
- **Net Improvement**: Overall improvement percentage
- **Improvement Rate**: Percentage of questions improved

### Example Output

```
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

### Integration with Tests

New pytest tests in `tests/test_answers.py`:

```python
@pytest.mark.skipif(not RUN_LIVE, reason="...")
def test_llm_judge_with_validation(mock_test_data):
    """Test LLM-as-a-judge evaluation with validation pass."""
    # Evaluates both initial and changed results
    # Tracks improvements and degradations
    # Asserts validation doesn't degrade results
```

## Benefits

### 1. Transparency
- See exactly what validation changed
- Understand why changes were made
- Track validation effectiveness

### 2. Quality Assurance
- Semantic evaluation vs. string matching
- Confidence levels for each judgment
- Detailed reasoning for decisions

### 3. Continuous Improvement
- Identify patterns in validation changes
- Measure validation pass effectiveness
- Find areas for prompt improvement

### 4. Debugging
- Understand why answers are marked incorrect
- See LLM's reasoning for judgments
- Track validation improvements over time

## Files Modified/Created

### Modified Files
1. `app/models.py` - Added validation fields to Answer model
2. `app/main.py` - Added validation fields and enhanced prompt
3. `tests/test_answers.py` - Added LLM judge tests
4. `tests/README.md` - Updated documentation
5. `DESIGN_SPECS.md` - Documented new features

### New Files
1. `tests/llm_judge.py` - Core LLM judging module
2. `tests/eval_pipeline_llm_judge.py` - Enhanced evaluation pipeline
3. `tests/LLM_JUDGE_GUIDE.md` - Comprehensive usage guide
4. `VALIDATION_FEATURES_SUMMARY.md` - This file

## Quick Start Guide

### 1. Generate Test Data

**IMPORTANT:** The test data must be generated with the API running to ensure question keys match.

```bash
# Start server
uvicorn app.main:app --reload

# In another terminal, generate test data
python -m tests.generate_mock_data
```

This creates API-generated baseline answers for consistency testing.

### 2. Test Validation Metadata

```bash
# Run validation metadata test
RUN_LIVE_OPENAI=1 pytest tests/test_answers.py::test_validation_metadata_fields -v -s
```

### 3. Run LLM Judge Evaluation

```bash
# Run evaluation with LLM judge
python -m tests.eval_pipeline_llm_judge --mode both --limit 3
```

### 4. Review Results

Check the generated JSON files:
- `tests/eval_results_no_validation_llm_judge.json`
- `tests/eval_results_with_validation_llm_judge.json`

**Expected Results:**
- **Consistency Accuracy:** ~90-95% (model agrees with itself)
- **Validation Improvements:** Varies based on test cases

**Note:** These measure consistency, not absolute clinical accuracy. For production, use human-validated ground truth.

## Best Practices

1. **Always use LLM judge for final evaluation** - More accurate than string matching
2. **Monitor validation improvements** - Track net improvement percentage
3. **Investigate degradations** - Any validation degradation needs review
4. **Check confidence levels** - Low confidence judgments may need manual review
5. **Read reasoning** - LLM explanations provide valuable insights

## Future Enhancements

Potential improvements:
- Add validation metadata to streaming endpoint
- Implement validation confidence scores
- Add validation suggestion mode (suggest but don't apply changes)
- Create validation analytics dashboard
- Add human-in-the-loop validation review

## Conclusion

These validation features provide:
- ✅ Full transparency into validation changes
- ✅ Sophisticated semantic evaluation
- ✅ Detailed metrics and insights
- ✅ Continuous improvement tracking

Use them to ensure high-quality prior authorization form completion and continuously improve system performance.

