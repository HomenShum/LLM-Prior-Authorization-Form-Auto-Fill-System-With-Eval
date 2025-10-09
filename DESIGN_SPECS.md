## Design Specs: Clinical PA Auto-Fill Demo (FastAPI + Streamlit)

### Goals
- Provide a FastAPI `/answers` endpoint that uses OpenAI Structured Outputs to fill a prior authorization question set based on patient data.
- Provide a streaming variant `/answers/stream` that emits SSE events to progressively update answers.
- Provide a `/process-files` endpoint to handle PDF and text file uploads with summarization.
- Build a Streamlit demo UI that allows selecting a patient, viewing context, uploading notes, and triggering auto-fill in Standard or Streaming mode.
- Support caching to avoid reprocessing identical requests.
- Support optional validation pass for quality assurance.
- Provide evaluation pipeline with F1 score metrics.

### Key Decisions
- Use OpenAI Chat Completions with `parse` helper (SDK >= 1.86) and a Pydantic schema to enforce structured output.
- LLM output schema (internal to the model call):
  - `AnswersResponse` with a list of `AnswerItem { key: str, value: str|bool, rationale?: str }`.
  - Server converts `AnswerItem` list into `AnswerOutput { answers: [Answer(question: Question, value)] }` using the input `QuestionSet` to bind types and texts.
- Streaming via `client.beta.chat.completions.stream(..., response_format=AnswersResponse)` and Starlette `StreamingResponse` with `text/event-stream`.
- Stream payload events as NDJSON-like SSE lines prefixed with `data: `, including `type: start|update|done|error`.
- Streamlit consumes the stream with `requests.post(..., stream=True)` and updates placeholders per question key.

### Prompting Strategy
- System prompt constrains style and instructs to return only supported evidence-based values; unknown -> "unknown", booleans -> defaults reasonable if unspecified.
- User content includes a short, structured summary of patient demographics, current Rx, and top visit notes, plus a textual view of the question set (`(type) key: content`).

### Error Handling
- If the model refuses, return HTTP 400 with reason.
- Streaming emits `error` event and then completes.

### Test Strategy
- `tests/test_answers.py` performs a live integration call to `/answers` against OpenAI, gated by `RUN_LIVE_OPENAI=1` to avoid accidental costs.
- Future: Add a streaming integration test gated behind the same flag.

### Security & Privacy Considerations
- Demo uses synthetic sample data. Do not send PHI/PII to external services in production without compliance review and data processing agreements.
- API key loaded from `.env` via `python-dotenv`; never hardcode secrets.

### New Features Implemented

#### 1. File Processing Endpoint (`/process-files`)
- Accepts PDF, text, and markdown files
- Supports two PDF processing methods:
  - **Files API**: Upload to OpenAI Files API, use Responses API with `gpt-5-mini`
  - **Base64**: Encode and send via Chat Completions with `gpt-5`
- Summarizes PDFs into clinical note format
- Enforces file size limits (10 MB per file, 32 MB total)
- Returns extracted/summarized notes and any errors

#### 2. Caching System
- Hash-based caching using patient data + questions + feedbacks + validate flag + model
- Prevents reprocessing identical requests
- In-memory cache (can be extended to Redis/database)

#### 3. Validation Pass
- Optional second LLM call to validate and correct initial answers
- Enabled via `validate: true` in request payload
- Uses dedicated validation prompt that reviews initial answers against patient context
- Improves accuracy at cost of additional API call

#### 4. Rationale Display
- Rationales are now stored in session state and displayed in the UI
- Shown as captions under each form field after auto-fill
- Also displayed in the results summary

#### 5. Evaluation Pipeline
- **`tests/generate_mock_data.py`**: Generates mock test cases with ground truth answers
- **`tests/eval_pipeline.py`**: Runs evaluation and computes F1 score, precision, recall, accuracy
- Supports both standard and validation modes
- Saves detailed results to JSON for analysis

### Limitations & Future Work
- UI does not evaluate `visible_if` conditions to hide/show form fields dynamically (could be added in Streamlit state logic).
- Streaming endpoint does not yet support validation pass (only standard endpoint).
- Cache is in-memory and will be lost on server restart (consider Redis or database).
- Mock test data generation uses simple heuristics; could be improved with more sophisticated ground truth labeling.

