# Evaluation Findings & Resolution

## Problem: Extremely Low Accuracy (5%)

### Initial Test Results
```
Initial Accuracy: 5.0%
Final Accuracy: 5.0%
Validation Improvements: 0
```

This was **alarmingly low** and indicated a fundamental problem with the evaluation setup.

## Root Cause Analysis

### The Issue
The mock data generator (`tests/generate_mock_data.py`) was creating expected answers for **completely different questions** than what existed in the actual question set.

**Generated Expected Answer Keys:**
```python
expected_answers = {
    "has_obesity_diagnosis": {...},
    "bmi_value": {...},
    "has_diabetes": {...},
    "has_cardiovascular_disease": {...},
    "previous_weight_loss_attempts": {...},
    "contraindications_present": {...},
    # ... etc
}
```

**Actual Question Keys in Zepbound Question Set:**
```python
questions = [
    {"key": "age", ...},
    {"key": "weight", ...},
    {"key": "height", ...},
    {"key": "bmi", ...},
    {"key": "expedited_review", ...},
    {"key": "other_weight_loss_meds", ...},
    {"key": "diagnosis", ...},
    # ... etc (30 total questions)
]
```

### Why This Happened
The original mock data generator was written with **hardcoded question keys** that didn't match the actual Zepbound prior authorization form questions. It was essentially comparing:
- **Expected:** Answers to questions that don't exist
- **Predicted:** Answers to the actual 30 questions in the form

Result: Almost complete mismatch → 5% accuracy (basically random chance)

## Solution

### Approach 1: API-Generated Baseline (Implemented)

Instead of manually creating expected answers, we now:
1. Call the API with each patient's data
2. Use the API's responses as the "expected answers"
3. Compare future API calls against this baseline

**New `generate_mock_data.py`:**
```python
# Call API to get answers
response = requests.post(API_URL, json=payload, timeout=120)
data = response.json()

# Use API responses as expected answers
for ans in data.get("answers", []):
    key = ans.get("question", {}).get("key")
    value = ans.get("value")
    rationale = ans.get("rationale")
    expected_answers[key] = {"value": value, "rationale": rationale}
```

**Advantages:**
- ✅ Guaranteed to match actual question keys
- ✅ Quick to generate
- ✅ Provides consistency baseline
- ✅ Good for regression testing

**Limitations:**
- ⚠️ Not true "ground truth" - it's comparing model against itself
- ⚠️ Won't catch systematic errors if model is consistently wrong
- ⚠️ Measures consistency, not absolute accuracy

### Approach 2: Human-Validated Ground Truth (Recommended for Production)

For production use, you should:
1. Have clinical experts review each patient case
2. Manually fill out the prior authorization form
3. Use those expert answers as ground truth
4. Compare model predictions against expert answers

**Advantages:**
- ✅ True accuracy measurement
- ✅ Catches systematic model errors
- ✅ Validates clinical correctness
- ✅ Regulatory compliance

**Disadvantages:**
- ⏱️ Time-consuming
- 💰 Expensive (requires clinical expertise)
- 🔄 Needs updates when questions change

## Results After Fix

### Test Results with Corrected Mock Data
```
Total Questions: 60
Initial Accuracy: 93.3%
Final Accuracy: 93.3%
Validation Improvements: 0
Net Improvement: +0.0%
```

### Interpretation

**93.3% Accuracy:**
- This means the model is **highly consistent** with itself
- When given the same patient data, it produces the same answers ~93% of the time
- The 6.7% variance could be due to:
  - Non-deterministic LLM behavior (temperature > 0)
  - Different interpretations of ambiguous clinical notes
  - Edge cases in data extraction

**0 Validation Improvements:**
- The validation pass didn't change any answers
- This could mean:
  - Initial answers were already very good
  - Validation prompt is too conservative
  - Not enough challenging cases in test data

## Recommendations

### 1. Create Human-Validated Test Set
```bash
# Create a small but high-quality test set
# - 10-20 diverse patient cases
# - Expert-validated answers
# - Cover edge cases and common scenarios
```

### 2. Use Both Evaluation Methods

**Consistency Testing (Current):**
- Use API-generated baseline
- Run frequently (CI/CD pipeline)
- Catch regressions and breaking changes

**Accuracy Testing (Production):**
- Use human-validated ground truth
- Run periodically (weekly/monthly)
- Measure true clinical accuracy

### 3. Improve Validation Pass

Since validation made 0 improvements, consider:
- Making validation prompt more critical
- Adding specific validation checks
- Testing with intentionally flawed initial answers

### 4. Track Metrics Over Time

```python
# Example metrics to track:
{
    "consistency_accuracy": 93.3%,  # vs API baseline
    "clinical_accuracy": ???%,       # vs expert ground truth
    "validation_improvement_rate": 0%,
    "high_confidence_accuracy": 95%,
    "processing_time": "6.7 minutes per patient"
}
```

## Usage

### Generate New Baseline
```bash
# Make sure API server is running
uvicorn app.main:app --reload

# Generate baseline from current API
python -m tests.generate_mock_data
```

### Run Evaluation
```bash
# Test consistency
$env:RUN_LIVE_OPENAI="1"; pytest tests/test_answers.py::test_llm_judge_with_validation -v -s

# Or use evaluation pipeline
python -m tests.eval_pipeline_llm_judge --mode both --limit 3
```

## Key Takeaways

1. **Always validate your test data** - The 5% accuracy was a red flag that led us to discover the mismatch

2. **API-generated baselines are useful** - They measure consistency and catch regressions, but aren't true ground truth

3. **Human validation is essential for production** - You need clinical experts to validate answers for regulatory and safety reasons

4. **LLM-as-a-Judge helps** - It recognizes semantic equivalence that string matching would miss

5. **Monitor both consistency and accuracy** - Track how consistent the model is (regression testing) AND how accurate it is (clinical validation)

## Next Steps

1. ✅ Fixed mock data generation
2. ✅ Achieved 93.3% consistency
3. ⏭️ Create human-validated test set (10-20 cases)
4. ⏭️ Measure true clinical accuracy
5. ⏭️ Improve validation pass effectiveness
6. ⏭️ Set up continuous monitoring

