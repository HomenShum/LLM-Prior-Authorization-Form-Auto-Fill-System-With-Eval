# AI-Powered Prior Authorization Form Auto-Fill System

A full-stack healthcare automation application that uses LLMs to automatically complete prior authorization forms from patient clinical data. Built with **FastAPI** backend and **Streamlit** frontend, the system leverages OpenAI's structured outputs to extract and validate medical information.

## Core Features

- **Automatic Form Filling**: Extracts answers from patient visit notes and demographics using GPT models with structured JSON output
- **Validation Pass**: Optional second LLM call to review and correct initial answers with detailed change tracking (what changed, why, and rationale)
- **Mock Data Generation**: Synthetic patient data and test case generation for development and testing
- **LLM-as-a-Judge Evaluation**: Sophisticated semantic evaluation system that judges answer correctness using clinical knowledge rather than string matching, tracking validation improvements/degradations with confidence levels
- **Streaming Support**: Real-time SSE streaming for progressive form field updates
- **File Processing**: PDF/text upload with clinical note summarization
- **Caching**: Hash-based request caching to avoid redundant API calls

## Tech Stack

- **Backend**: FastAPI with Pydantic models
- **Frontend**: Streamlit interactive UI
- **LLM**: OpenAI GPT (gpt-5-mini/gpt-5) with structured outputs
- **Evaluation**: F1 score metrics + LLM judge with confidence scoring

## Use Case

Automates the tedious process of filling pharmaceutical prior authorization forms (e.g., Zepbound) by intelligently extracting relevant clinical information from patient records.

This system demonstrates production-ready LLM integration with validation, evaluation pipelines, and quality assurance mechanisms for healthcare automation.

---

## Implementation Highlights

### Features Implemented

1. **User dropdown select patient data**
2. **User can view or upload to update the existing visitor notes**
3. **User can provide feedback before or after to guide the form filling process**
4. **Streamlit display works as intended**
5. **User interactions work as intended**
6. **FastAPI endpoint for answer and file upload work as intended** (streaming not fully tested due to organization restraint requiring verified OPENAI_API_KEY)

### Optimizations

1. **Actor-Critic with Feedback** - Using the validation loop
2. **Eval Pipeline** - Testing for F1 score with and without validation loop (Tweaked validation loop after initial test result to include the QA and Feedback notes)
3. **Caching** - No more reprocessing when unneeded

---

## Evaluation Results

### Initial F1 Score Testing

Upon initial testing, we observed the F1 score eval pipeline outputting results that seemed to disagree with our model main.py FastAPI pipeline output. As a result, the F1 score was quite low:

```
=================================================== short test summary info ====================================================
FAILED tests/test_answers.py::test_f1_score_without_validation - AssertionError: F1 score too low: 0.077
FAILED tests/test_answers.py::test_f1_score_with_validation - AssertionError: F1 score too low: 0.053
====================================== 2 failed, 1 passed, 1 warning in 701.59s (0:11:41) ======================================
```

**Analysis**: We needed to validate the True Answer Dataset to see whether or not the true answer dataset was even correct. We approached this with **LLM-as-a-Judge** to double check the generated True Answer Dataset before testing with the Non-validated LLM form parsing response and the Validated LLM form parsing response.

### LLM-as-a-Judge Results

#### Generating Mock Expected Answers

```bash
python -m tests.generate_mock_data
```

This generated 10 sets of 30 questions with expected answers based on 10 sample patient data.

#### Running the Tests

```bash
$env:RUN_LIVE_OPENAI="1"; pytest tests/test_answers.py::test_llm_judge_without_validation -v -s
$env:RUN_LIVE_OPENAI="1"; pytest tests/test_answers.py::test_llm_judge_with_validation -v -s
```

**Results**:
- **Without validation**: 100% accuracy
- **With validation**: 93.3% accuracy

This is likely the result of the prompt not being optimized for the validation pass right now, and the LLM is confused by the additional context from reading the extra `{initial_answer}` context clue.

**Further optimization needed**:
- Incorporate special prompt design
- Use larger parameter reasoning model rather than gpt-5-mini
- Add few-shot examples for edge cases

#### Detailed Test Logs

<details>
<summary>Mock Data Generation Log</summary>

```
(engineer-take-home) PS D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum>
 python -m tests.generate_mock_data
Loaded 10 patients and 30 questions

Generating expected answers by calling API...
======================================================================

[1/10] Processing patient: Isaiah Reed
  ✓ Generated 30 expected answers

[2/10] Processing patient: Elizabeth Munoz
  ✓ Generated 30 expected answers

[3/10] Processing patient: Rebecca Edwards
  ✓ Generated 30 expected answers

[4/10] Processing patient: Suzanne Harris
  ✓ Generated 30 expected answers

[5/10] Processing patient: Jeffrey Donovan
  ✓ Generated 30 expected answers

[6/10] Processing patient: Madison Cook
  ✓ Generated 30 expected answers

[7/10] Processing patient: Michelle Andrews
  ✓ Generated 30 expected answers

[8/10] Processing patient: Michelle Dougherty
  ✓ Generated 30 expected answers

[9/10] Processing patient: Anthony Chaney
  ✓ Generated 30 expected answers

[10/10] Processing patient: James Aguilar
  ✓ Generated 30 expected answers

======================================================================
✅ Generated 10 mock test cases
📁 Saved to: D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum\tests\mock_test_data.json

⚠️  NOTE: These are API-generated answers, not human-validated ground truth.
   For production use, have clinical experts review and validate these answers.
```

</details>

<details>
<summary>LLM Judge WITH Validation Test Log</summary>

```
(engineer-take-home) PS D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum>
 $env:RUN_LIVE_OPENAI="1"; pytest tests/test_answers.py::test_llm_judge_with_validation -v -s
=============================== test session starts ===============================
platform win32 -- Python 3.11.5, pytest-8.4.0, pluggy-1.6.0 -- D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum
configfile: pyproject.toml
plugins: anyio-4.9.0, Faker-37.4.0, logfire-3.18.0
collected 1 item

tests/test_answers.py::test_llm_judge_with_validation
============================================================
Testing LLM Judge WITH Validation Pass
============================================================

[1] Testing patient: Isaiah Reed

[2] Testing patient: Elizabeth Munoz

------------------------------------------------------------
Total Questions: 60
Initial Accuracy: 93.3%
Final Accuracy: 93.3%
Validation Improvements: 0
Net Improvement: +0.0%
============================================================
PASSED

================================ warnings summary =================================
.venv\Lib\site-packages\pydantic\_internal\_fields.py:198
  D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum\.venv\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "validate" in "AnswerInput" shadows an attribute in parent "BaseModel"
    warnings.warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
==================== 1 passed, 1 warning in 402.39s (0:06:42) =====================
```

</details>

<details>
<summary>LLM Judge WITHOUT Validation Test Log</summary>

```
(engineer-take-home) PS D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum>
 $env:RUN_LIVE_OPENAI="1"; pytest tests/test_answers.py::test_llm_judge_without_validation -v -s
=============================== test session starts ===============================
platform win32 -- Python 3.11.5, pytest-8.4.0, pluggy-1.6.0 -- D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum
configfile: pyproject.toml
plugins: anyio-4.9.0, Faker-37.4.0, logfire-3.18.0
collected 1 item

tests/test_answers.py::test_llm_judge_without_validation
============================================================
Testing LLM Judge WITHOUT Validation Pass
============================================================

[1] Testing patient: Isaiah Reed

[2] Testing patient: Elizabeth Munoz

------------------------------------------------------------
Total Questions: 60
Correct Answers: 60
Accuracy: 100.0%
High-Confidence Accuracy: 100.0%
============================================================
PASSED

================================ warnings summary =================================
.venv\Lib\site-packages\pydantic\_internal\_fields.py:198
  D:\VSCode Projects\Develop_Health\take_home_test\Homen-Shum\.venv\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "validate" in "AnswerInput" shadows an attribute in parent "BaseModel"
    warnings.warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
==================== 1 passed, 1 warning in 110.80s (0:01:50) =====================
```

</details>

---

## AI Tooling and Design Considerations

### Development Tools

1. **Augment VS Code Extension** - AI-powered coding assistant
2. **Feeding Web Documentation as Context**:
   - [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
   - [OpenAI PDF Files](https://platform.openai.com/docs/guides/pdf-files?api-mode=chat#base64-encoded-files)

### Design Process

3. **Whiteboarding with hand-drawn low fidelity design** into section-by-section implementation manually prompted:

![develop_health_quicknotes (2)](https://github.com/user-attachments/assets/cc32731a-a200-4e93-be62-a0afac85cd5a)
![develop_health_quicknotes](https://github.com/user-attachments/assets/1b7ace99-847c-4e3e-b559-8e0c5990a061)
![develop_health_quicknotes (1)](https://github.com/user-attachments/assets/b935dcc7-1245-4c7b-a1cc-92d89972b991)

Each section and written checkpoint is jotted down for clarity of thought and structured implementation.

4. **Evaluation design** tailored to the context of the sample data and the AI Engineer take home interview descriptions.

### Automated Testing with Augment

5. **Augment can be smartly prompted** to run automated testing until all "live smoke tests using real API keys" pass:
   - Set `$env:YOUR_KEY` in the Augment CLI terminal
   - This specific prompt and key setting allow Augment to run the test-fix-refine-retest loop for hours
   - **Note**: This feature works wonderfully with message-per-month pricing but would be expensive with credit-based pricing
   - **Future to-do**: Create live smoke tests with True Answer Dataset and validate with tests generated using real APIs integrated into FastAPI backend after careful scenario-based test designs

Example design for a different application (notebook application with automated agent for research tasks):

<img width="700" height="1412" alt="image" src="https://github.com/user-attachments/assets/c1f7358d-28f4-450d-87f4-a1d086c90e55" />

---

## Future Considerations

### Scalability

6. **Visitor Note RAG Implementation** for scaling to hundreds/thousands of visitor notes accumulated over a person's lifespan:
   - Async per form question per visitor note validation pipeline
   - Enhance correctness and speed of completion
   - Each question may have top 100K visitor notes suitable for the response
   - Order them based on datetime and batch into grouped chunks (10 notes per chunk)
   - Come up with preliminary decision and rationale
   - Concatenate the 10 batched decision and rationale responses
   - Final response prioritizing the most recent preliminary decisions

### Production Assumptions

7. **Production Environment Considerations**:
   - **HIPAA Compliance**: Production LLM Model used is isolated within provider environment that can guarantee HIPAA Business Associate Agreement
   - **Golden Dataset**: Production application and form filling pipeline deployment is tested and evaluated for Accuracy and F1 score with Golden True Answer Dataset that is historically submitted and human verified
   - **Ensemble Methods**: Production environment result can be further enhanced with ensembling method where we mesh multiple LLMs' responses and calculate weighted confidence score to see which model scores highest for each question
   - **F1 Score Insights**: Can give insight into which question and which patient/medical background the LLM model performs best upon
   - **Re-evaluation Pipeline**: Use another validation pipeline with overall high F1 score LLM model to judge over the decision and rationale
   - **Observability**: Pydantic Logfire can help with observation over the LLMs' performance

---

## Additional Enhancements

Additionally, we added the `validated_findings` field for the LLM response that has the LLM validation to display under the rationale field for each form question and highlight the form question if the answer were to be modified as a result of the additional validation loop.

---

## Getting Started

For detailed setup and usage instructions, please refer to:
- [Design Specifications](DESIGN_SPECS.md)
- [Folder Structure](FOLDER_STRUCTURES.md)
- [Validation Features Summary](VALIDATION_FEATURES_SUMMARY.md)
- [LLM Judge Guide](tests/LLM_JUDGE_GUIDE.md)
- [Evaluation Findings](tests/EVALUATION_FINDINGS.md)

---

## Commit History

- `fef8669` - Add validation features, LLM judge evaluation, and comprehensive documentation
- `82d356e` - feat: Add LLM-as-a-Judge evaluation and fix validation metadata
- `8fb1969` - feat: Implement prior authorization auto-fill with validation loop and F1 evaluation
- `336a1e2` - initial note
- `6e2b2ba` - Initial commit