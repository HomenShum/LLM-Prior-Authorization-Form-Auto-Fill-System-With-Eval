## Folder Structure (Key Files)

- app/
  - env.py                # .env loading and observability setup
  - main.py               # FastAPI app with /answers, /answers/stream, and /process-files
  - models.py             # Pydantic models for Patient, QuestionSet, Answer, ProcessFiles, etc.
- sample_data/
  - patient_data.json     # Synthetic patient records (list)
  - zepbound_question_set.json # PA question set for demo
- tests/
  - test_answers.py       # Live integration test (gated by RUN_LIVE_OPENAI)
  - generate_mock_data.py # Generate mock test cases with ground truth
  - eval_pipeline.py      # Evaluation pipeline with F1 score metrics
  - mock_test_data.json   # Generated mock test data (created by generate_mock_data.py)
  - eval_results.json     # Evaluation results (created by eval_pipeline.py)
  - README.md             # Documentation for evaluation pipeline
- streamlit_app.py        # Streamlit demo UI (Standard + Streaming + File Upload)
- openai_structured_ouput_official_doc.md # Reference patterns for structured outputs
- homen_shum_notes.md     # Project notes / goals
- DESIGN_SPECS.md         # Architecture and design decisions for this demo
- FOLDER_STRUCTURES.md    # This file

## Run Instructions (dev)
1) Start API:
   - uvicorn app.main:app --reload
2) Run Streamlit UI:
   - streamlit run streamlit_app.py
3) Optional live test:
   - set RUN_LIVE_OPENAI=1 && pytest -q
4) Generate mock test data:
   - python -m tests.generate_mock_data
5) Run evaluation pipeline:
   - python -m tests.eval_pipeline
   - python -m tests.eval_pipeline --validate  # with validation pass

## Dependencies
- FastAPI/Starlette (already in pyproject)
- OpenAI >= 1.86.0 (declared in dev deps)
- Streamlit for demo UI
- requests for HTTP calls from Streamlit

If not present, install via your environment's package manager (uv, pip, etc.).
