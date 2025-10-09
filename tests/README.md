# Evaluation Pipeline

This directory contains tools for generating mock test data and evaluating the prior authorization form auto-fill system.

## Files

- **`generate_mock_data.py`**: Generates mock test cases with ground truth answers based on sample patient data
- **`eval_pipeline.py`**: Runs evaluation against the API and computes F1 score and other metrics
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

### 2. Run Evaluation

Make sure the FastAPI server is running:

```bash
uvicorn app.main:app --reload
```

Then run the evaluation pipeline:

```bash
# Basic evaluation (no validation pass)
python -m tests.eval_pipeline

# With validation pass enabled
python -m tests.eval_pipeline --validate

# Custom output file
python -m tests.eval_pipeline --output my_results.json
```

This will:
- Load mock test data
- Call the `/answers` API endpoint for each test case
- Compare predicted answers with expected answers
- Compute metrics: precision, recall, F1 score, accuracy
- Print summary statistics
- Save detailed results to JSON file

## Metrics

The evaluation computes the following metrics:

- **Precision**: Of all predicted positive answers, how many were correct?
- **Recall**: Of all actual positive answers, how many did we predict?
- **F1 Score**: Harmonic mean of precision and recall (main metric)
- **Accuracy**: Overall correctness across all questions

### Scoring Logic

- **Boolean questions**: Standard binary classification (exact match)
- **Text questions**: 
  - Exact match = 1.0 point
  - Partial match (substring) = 0.5 points
  - No match = 0 points

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

## Extending the Evaluation

To add more test cases:

1. Add more patients to `sample_data/patient_data.json`
2. Update `generate_mock_data.py` to generate appropriate ground truth answers
3. Re-run the generation and evaluation scripts

To customize metrics:

1. Edit the `compute_metrics()` function in `eval_pipeline.py`
2. Add custom scoring logic for specific question types
3. Add new metric calculations as needed

