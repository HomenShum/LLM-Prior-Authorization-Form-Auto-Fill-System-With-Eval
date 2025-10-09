# Evaluation Pipeline

This directory contains tools for generating mock test data and evaluating the prior authorization form auto-fill system.

## Files

### Test & Evaluation Files
- **`test_answers.py`**: Pytest test suite for the `/answers` endpoint
- **`generate_mock_data.py`**: Generates mock test cases with ground truth answers based on sample patient data
- **`eval_pipeline.py`**: Runs evaluation against the API and computes F1 score and other metrics (string-based)
- **`eval_pipeline_llm_judge.py`**: ⭐ **Enhanced evaluation using LLM-as-a-Judge** (recommended)
- **`llm_judge.py`**: LLM-based answer validation module

### Data Files
- **`mock_test_data.json`**: Generated mock test data (created by running `generate_mock_data.py`)
- **`eval_results.json`**: Evaluation results (created by running `eval_pipeline.py`)

## Usage

### 1. Generate Mock Test Data

First, generate the mock test data with ground truth answers:

```bash
python -m tests.generate_mock_data
```

This will:
- Load sample patient data from `sample_data/patient_data.json`
- Load questions from `sample_data/zepbound_question_set.json`
- Generate expected answers for each patient based on their visit notes
- Save to `tests/mock_test_data.json`

### 2. Run Unit Tests

Make sure the FastAPI server is running, then run pytest:

```bash
# Run all tests
RUN_LIVE_OPENAI=1 pytest tests/test_answers.py -v

# Run specific test
RUN_LIVE_OPENAI=1 pytest tests/test_answers.py::test_llm_judge_with_validation -v -s
```

### 3. Run Evaluation Pipeline

Make sure the FastAPI server is running:

```bash
uvicorn app.main:app --reload
```

#### Option A: String-Based Evaluation (Fast but less accurate)

```bash
# Basic evaluation (no validation pass)
python -m tests.eval_pipeline

# With validation pass enabled
python -m tests.eval_pipeline --validate

# Custom output file
python -m tests.eval_pipeline --output my_results.json
```

#### Option B: LLM-as-a-Judge Evaluation ⭐ **Recommended**

More accurate evaluation using LLM to judge semantic equivalence:

```bash
# Evaluate without validation
python -m tests.eval_pipeline_llm_judge --mode without_validation

# Evaluate with validation
python -m tests.eval_pipeline_llm_judge --mode with_validation

# Run both modes
python -m tests.eval_pipeline_llm_judge --mode both

# Limit to first N test cases (for testing)
python -m tests.eval_pipeline_llm_judge --mode both --limit 3
```

## Metrics

### String-Based Metrics (eval_pipeline.py)

- **Precision**: Of all predicted positive answers, how many were correct?
- **Recall**: Of all actual positive answers, how many did we predict?
- **F1 Score**: Harmonic mean of precision and recall (main metric)
- **Accuracy**: Overall correctness across all questions

**Scoring Logic:**
- **Boolean questions**: Standard binary classification (exact match)
- **Text questions**:
  - Exact match = 1.0 point
  - Partial match (substring) = 0.5 points
  - No match = 0 points

**Limitations:** Strict string matching, doesn't recognize semantic equivalence

### LLM Judge Metrics (eval_pipeline_llm_judge.py) ⭐

#### Without Validation
- **Accuracy**: Percentage of answers that semantically match expected values
- **High-Confidence Accuracy**: Accuracy for high-confidence judgments only
- **Total Questions**: Number of questions evaluated

#### With Validation
- **Initial Accuracy**: Accuracy before validation pass
- **Final Accuracy**: Accuracy after validation corrections
- **Validation Improvements**: Number of answers corrected from wrong to right
- **Validation Degradations**: Number of answers changed from right to wrong
- **Net Improvement**: Overall improvement percentage
- **Improvement Rate**: Percentage of questions improved by validation

**Advantages:**
- Understands semantic equivalence (e.g., "yes" = "true")
- Recognizes clinical terminology variations
- Provides confidence levels and reasoning for each judgment
- Tracks validation improvements and degradations

## Example Output

```
Running evaluation on 3 test cases...
Validation pass: disabled
------------------------------------------------------------

[1/3] Testing patient: John Doe
  ✓ F1: 0.857 | Precision: 0.900 | Recall: 0.818

[2/3] Testing patient: Jane Smith
  ✓ F1: 0.923 | Precision: 0.950 | Recall: 0.900

[3/3] Testing patient: Bob Johnson
  ✓ F1: 0.800 | Precision: 0.850 | Recall: 0.760

============================================================
EVALUATION SUMMARY
============================================================
Total test cases: 3
Successful: 3
Failed: 0

Average Metrics:
  F1 Score:  0.860
  Precision: 0.900
  Recall:    0.826
  Accuracy:  0.867
============================================================

Results saved to: tests/eval_results.json
```

## Generating Test Data

**IMPORTANT:** The API server must be running before generating test data.

```bash
# Start the API server first
uvicorn app.main:app --reload

# In another terminal, generate test data
python -m tests.generate_mock_data
```

This will:
- Call the API with each of the 10 sample patients
- Generate 30 expected answers per patient (300 total)
- Save to `mock_test_data.json` as baseline for consistency testing

**Output:**
```
Loaded 10 patients and 30 questions
Generating expected answers by calling API...
======================================================================
[1/10] Processing patient: Isaiah Reed
  ✓ Generated 30 expected answers
...
======================================================================
✅ Generated 10 mock test cases
📁 Saved to: tests/mock_test_data.json
```

**Note:** These are API-generated answers (model comparing against itself), not human-validated ground truth. For production use, have clinical experts review and validate the answers.

## Evaluation Results

### Test Results Summary

**Without Validation Pass:**
```bash
$env:RUN_LIVE_OPENAI="1"; pytest tests/test_answers.py::test_llm_judge_without_validation -v -s
```

Results:
```
Total Questions: 60
Correct Answers: 60
Accuracy: 100.0%
High-Confidence Accuracy: 100.0%
```

**With Validation Pass:**
```bash
$env:RUN_LIVE_OPENAI="1"; pytest tests/test_answers.py::test_llm_judge_with_validation -v -s
```

Results:
```
Total Questions: 60
Initial Accuracy: 93.3%
Final Accuracy: 93.3%
Validation Improvements: 0
Net Improvement: +0.0%
```

### Analysis

The results show that:

1. **Form filling WITHOUT validation:** 100% accuracy
   - Model is highly consistent with itself
   - Produces identical answers when given same input

2. **Form filling WITH validation:** 93.3% accuracy
   - Validation pass introduces some variance
   - 0 improvements suggests validation is not effectively correcting errors

### Likely Causes

The validation pass showing lower accuracy is likely due to:

1. **Prompt not optimized for validation:** The validation prompt may be confusing the LLM with additional context from reading the `{initial_answer}` field

2. **Model limitations:** Using `gpt-5-mini` which may not have sufficient reasoning capacity for complex validation tasks

3. **Lack of few-shot examples:** No examples provided for edge cases or validation scenarios

### Recommended Optimizations

1. **Improve validation prompt design:**
   - Simplify the validation instructions
   - Remove confusing context
   - Add clear decision criteria

2. **Use larger reasoning model:**
   - Switch to `gpt-5` for validation pass
   - Better reasoning capabilities for complex clinical validation

3. **Add few-shot examples:**
   - Provide examples of correct validations
   - Show edge cases and how to handle them
   - Demonstrate when to change vs. keep answers

4. **Separate validation concerns:**
   - Clinical accuracy validation
   - Completeness validation
   - Format/unit validation

## Extending the Evaluation

To add more test cases:

1. Add more patients to `sample_data/patient_data.json`
2. Re-run `python -m tests.generate_mock_data`
3. Run evaluation tests

To customize metrics:

1. Edit the `compute_metrics()` function in `eval_pipeline.py`
2. Add custom scoring logic for specific question types
3. Add new metric calculations as needed

For detailed analysis of the evaluation findings, see `tests/EVALUATION_FINDINGS.md`.

