import base64
import hashlib
import json
import os
import tempfile
from collections.abc import Generator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.env import setup_env

from .models import (
    Answer,
    AnswerInput,
    AnswerOutput,
    ProcessFilesRequest,
    ProcessFilesResponse,
    Question,
)

setup_env()

# ---- Config ----
DEFAULT_MODEL = "gpt-5-mini"  # per request
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


# Initialize the FastAPI application
app = FastAPI(
    title="Pharmacy Prior Authorization API",
    description="API for generating answers to prior authorization questions using patient data",
    version="1.0.0",
)


# --- Local structured-output models for the LLM's parsed response ---
class AnswerItem(BaseModel):
    key: str
    value: str | bool
    rationale: str | None = None
    # Validation-specific fields (populated during validation pass)
    change_needed: bool | None = None
    changed_result: str | bool | None = None
    change_rationale: str | None = None


class AnswersResponse(BaseModel):
    answers: list[AnswerItem]


def _patient_summary(data: AnswerInput) -> str:
    p = data.patient
    rx = p.prescription
    visit_lines = "\n- ".join(p.visit_notes) if p.visit_notes else "—"
    return (
        f"Patient: {p.first_name} {p.last_name}, DOB: {p.date_of_birth}, Gender: {p.gender}.\n"
        f"Current prescription: {rx.medication} {rx.dosage}, {rx.frequency}, duration: {rx.duration}.\n"
        f"Visit notes:\n- {visit_lines}"
    )


# Simple in-memory cache keyed by payload hash
_CACHE: dict[str, dict] = {}


def _cache_key_from_answer_input(data: AnswerInput) -> str:
    # Hash patient + questions + feedbacks + validate flag + model
    payload = {
        "patient": data.patient.model_dump(),
        "question_set": data.question_set.model_dump(),
        "feedbacks": getattr(data, "feedbacks", None),
        "validate": getattr(data, "validate", None),
        "model": OPENAI_MODEL,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _build_messages(data: AnswerInput) -> list[dict]:
    system = (
        "You are a clinical prior-authorization assistant. Read the patient's info and visit notes, "
        "then answer each question with the most likely chart-supported value. "
        "Only use information supported by the notes. If information is missing, respond with 'unknown' "
        "for text or False for boolean questions. "
        "Return answers keyed by the provided 'key' exactly and include a short rationale when possible. "
        "You must produce JSON that conforms to the provided schema."
    )

    questions_as_text = "\n".join(
        f"- ({q.type}) {q.key}: {q.content}" for q in data.question_set.questions
    )

    # Optional clinician feedback
    feedback_section = ""
    try:
        fbs = getattr(data, "feedbacks", None)
        if fbs:
            feedback_text = "\n".join(f"- {fb}" for fb in fbs)
            feedback_section = f"\n\nClinician feedback notes:\n{feedback_text}"
    except Exception:
        pass

    user = (
        "Patient context and questions follow.\n\n"
        f"{_patient_summary(data)}\n\n"
        "Questions to answer (key => value):\n"
        f"{questions_as_text}"
        "Feedback notes that may help your analysis or clarify the patient's condition:"
        f"{feedback_section}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_validation_messages(
    data: AnswerInput, initial: AnswersResponse
) -> list[dict]:
    system = (
        "You are a clinical QA validator. Re-evaluate the initial answers strictly against the patient context. "
        "Correct any mistakes and ensure each answer is chart-supported. "
        "For each answer, you must indicate whether a change was needed:\n"
        "- If the initial answer was correct, set 'change_needed' to false and keep the original 'value' and 'rationale'.\n"
        "- If the initial answer needs correction, set 'change_needed' to true, provide the corrected value in 'changed_result', "
        "and explain why the change was necessary in 'change_rationale'.\n"
        "Return the same JSON schema with these validation fields populated."
    )
    # Render initial answers with rationales
    init_lines = []
    for ai in initial.answers:
        r = f" (rationale: {ai.rationale})" if ai.rationale else ""
        init_lines.append(f"- {ai.key} => {ai.value}{r}")
    initial_text = "\n".join(init_lines) if init_lines else "(none)"

    questions_as_text = "\n".join(
        f"- ({q.type}) {q.key}: {q.content}" for q in data.question_set.questions
    )

    # Optional clinician feedback
    feedback_section = ""
    try:
        fbs = getattr(data, "feedbacks", None)
        if fbs:
            feedback_text = "\n".join(f"- {fb}" for fb in fbs)
            feedback_section = f"\n\nClinician feedback notes:\n{feedback_text}"
    except Exception:
        pass

    user = (
        "Patient context follows, then the initial answers. Re-issue corrected answers if needed.\n\n"
        f"{_patient_summary(data)}\n\n"
        "Questions to answer (key => value):\n"
        f"{questions_as_text}"
        "Feedback notes that may help your analysis or clarify the patient's condition:"
        f"{feedback_section}"
        f"Initial answers:\n{initial_text}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _answers_to_output(
    parsed: AnswersResponse, questions: list[Question]
) -> AnswerOutput:
    by_key: dict[str, Question] = {q.key: q for q in questions}
    results: list[Answer] = []
    for item in parsed.answers:
        if item.key not in by_key:
            continue
        q = by_key[item.key]
        if q.type == "boolean":
            if isinstance(item.value, bool):
                val: str | bool = item.value
            else:
                val = str(item.value).strip().lower() in {"true", "yes", "y", "1"}
        else:
            val = str(item.value)

        # Handle validation fields
        changed_val: str | bool | None = None
        if item.changed_result is not None:
            if q.type == "boolean":
                if isinstance(item.changed_result, bool):
                    changed_val = item.changed_result
                else:
                    changed_val = str(item.changed_result).strip().lower() in {
                        "true",
                        "yes",
                        "y",
                        "1",
                    }
            else:
                changed_val = str(item.changed_result)

        results.append(
            Answer(
                question=q,
                value=val,
                rationale=item.rationale,
                change_needed=item.change_needed,
                changed_result=changed_val,
                change_rationale=item.change_rationale,
            )
        )
    return AnswerOutput(answers=results)


# ---- Endpoints ----
@app.get("/")
async def root():
    return {
        "message": "Pharmacy Prior Authorization API is running",
        "status": "healthy",
        "model": OPENAI_MODEL,
    }


@app.post("/answers")
async def get_answers(data: AnswerInput) -> AnswerOutput:
    """
    Generate answers to prior authorization questions based on patient data.
    Uses Structured Outputs to parse into AnswersResponse, then maps to AnswerOutput.
    Supports caching and optional validation pass.
    """
    from openai import OpenAI

    client = OpenAI()  # uses OPENAI_API_KEY

    # Check cache
    cache_key = _cache_key_from_answer_input(data)
    if cache_key in _CACHE:
        cached = _CACHE[cache_key]
        return AnswerOutput(**cached)

    try:
        # Initial generation
        completion = client.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=_build_messages(data),
            response_format=AnswersResponse,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {e}") from e

    msg = completion.choices[0].message
    refusal = getattr(msg, "refusal", None)
    if refusal:
        raise HTTPException(status_code=400, detail=f"Model refused: {refusal}")

    parsed: AnswersResponse = msg.parsed  # type: ignore

    # Optional validation pass
    if getattr(data, "validate", False):
        try:
            validation_completion = client.beta.chat.completions.parse(
                model=OPENAI_MODEL,
                messages=_build_validation_messages(data, parsed),
                response_format=AnswersResponse,
            )
            val_msg = validation_completion.choices[0].message
            if not getattr(val_msg, "refusal", None):
                parsed = val_msg.parsed  # type: ignore
        except Exception:
            # If validation fails, use initial response
            pass

    result = _answers_to_output(parsed, data.question_set.questions)

    # Cache the result
    _CACHE[cache_key] = result.model_dump()

    return result


@app.post("/process-files", response_model=ProcessFilesResponse)
async def process_files(request: ProcessFilesRequest) -> ProcessFilesResponse:
    """
    Process uploaded files (PDF, text) and extract/summarize content.
    Supports both Files API and Base64 methods.
    """
    from openai import OpenAI

    client = OpenAI()
    notes: list[str] = []
    errors: list[str] = []

    SUMMARY_PROMPT = (
        "Summarize this PDF into a concise CLINICAL VISIT NOTE for the chart. "
        "Use clear section headings (Chief Complaint, HPI, PMH, Medications, Allergies, "
        "Vitals, Labs/Imaging, Assessment, Plan). Use bullet points where helpful. "
        "Keep it de-identified. Output plain text (Markdown allowed), no extra commentary."
    )

    for file_item in request.files:
        filename = file_item.filename
        file_data = file_item.file_data

        try:
            # Determine file type
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

            if ext in ("txt", "md"):
                # Decode text files
                if file_data.startswith("data:"):
                    # Extract base64 part
                    parts = file_data.split(",", 1)
                    if len(parts) == 2:
                        content = (
                            base64.b64decode(parts[1])
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                    else:
                        content = (
                            base64.b64decode(file_data)
                            .decode("utf-8", errors="ignore")
                            .strip()
                        )
                else:
                    content = (
                        base64.b64decode(file_data)
                        .decode("utf-8", errors="ignore")
                        .strip()
                    )

                if content:
                    notes.append(content)

            elif ext == "pdf":
                if request.method == "files_api":
                    # Files API method
                    # Decode base64 to bytes
                    if file_data.startswith("data:"):
                        parts = file_data.split(",", 1)
                        pdf_bytes = (
                            base64.b64decode(parts[1])
                            if len(parts) == 2
                            else base64.b64decode(file_data)
                        )
                    else:
                        pdf_bytes = base64.b64decode(file_data)

                    # Write to temp file
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf"
                    ) as tmp:
                        tmp.write(pdf_bytes)
                        tmp_path = tmp.name

                    # Upload to OpenAI
                    with open(tmp_path, "rb") as f:
                        ofile = client.files.create(file=f, purpose="user_data")

                    # Use Responses API
                    resp = client.responses.create(
                        model="gpt-5-mini",
                        input=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "input_file", "file_id": ofile.id},
                                    {"type": "input_text", "text": SUMMARY_PROMPT},
                                ],
                            }
                        ],
                    )
                    extracted = (getattr(resp, "output_text", None) or "").strip()

                else:
                    # Base64 method
                    completion = client.chat.completions.create(
                        model="gpt-5",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "file",
                                        "file": {
                                            "filename": filename,
                                            "file_data": file_data,
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": SUMMARY_PROMPT,
                                    },
                                ],
                            }
                        ],
                    )
                    out = completion.choices[0].message.content
                    if isinstance(out, list):
                        extracted = "".join(
                            [
                                seg.get("text", "")
                                if isinstance(seg, dict)
                                else str(seg)
                                for seg in out
                            ]
                        ).strip()
                    else:
                        extracted = str(out or "").strip()

                if extracted:
                    notes.append(extracted)
                else:
                    errors.append(f"No content extracted from {filename}")

        except Exception as e:
            errors.append(f"Failed to process {filename}: {str(e)}")

    return ProcessFilesResponse(notes=notes, errors=errors)


@app.post("/answers/stream")
async def stream_answers(data: AnswerInput):
    """
    Stream structured answers incrementally using OpenAI streaming (SSE).

    Emits SSE 'data:' lines with JSON payloads:
      {"type":"start"}
      {"type":"update","answers":[{key, value, rationale?}, ...]}
      {"type":"done","answers":[...final snapshot...]}

    On error:
      {"type":"error","detail":"..."}
    """

    def sse_generator() -> Generator[bytes, None, None]:
        from openai import OpenAI

        client = OpenAI()
        snapshot: dict[str, AnswerItem] = {}

        def _emit(payload: dict) -> bytes:
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()

        try:
            yield _emit({"type": "start"})
            with client.beta.chat.completions.stream(
                model=OPENAI_MODEL,
                messages=_build_messages(data),
                response_format=AnswersResponse,
            ) as stream:
                for event in stream:
                    # Partial parsed content as it arrives (robust to dict or Pydantic)
                    if event.type == "content.delta":
                        if event.parsed is None:
                            continue
                        updated: list[AnswerItem] = []
                        if isinstance(event.parsed, dict):
                            answers_payload = event.parsed.get("answers") or []
                            if isinstance(answers_payload, list):
                                for itm in answers_payload:
                                    if not isinstance(itm, dict):
                                        continue
                                    key = itm.get("key")
                                    value = itm.get("value")
                                    if key is None or value is None:
                                        # Skip until we have both key and value
                                        continue
                                    rationale = itm.get("rationale")
                                    answer_item = AnswerItem(
                                        key=key, value=value, rationale=rationale
                                    )
                                    snapshot[key] = answer_item
                                    updated.append(answer_item)
                        else:
                            # event.parsed is a Pydantic AnswersResponse
                            partial: AnswersResponse = event.parsed  # type: ignore
                            for itm in getattr(partial, "answers", []):
                                snapshot[itm.key] = itm
                                updated.append(itm)
                        if updated:
                            yield _emit(
                                {
                                    "type": "update",
                                    "answers": [i.model_dump() for i in updated],
                                }
                            )
                    elif event.type == "content.done":
                        # Content streaming is complete
                        pass
                    elif event.type == "error":
                        yield _emit({"type": "error", "detail": str(event.error)})

                # Final completion (full object for safety)
                final = stream.get_final_completion()
                final_msg = final.choices[0].message
                refusal = getattr(final_msg, "refusal", None)
                if refusal:
                    yield _emit({"type": "error", "detail": str(refusal)})
                else:
                    # If the final includes a complete parsed object, prefer it to ensure no drift
                    try:
                        if hasattr(final_msg, "parsed") and final_msg.parsed:
                            if isinstance(final_msg.parsed, dict):
                                answers_payload = final_msg.parsed.get("answers") or []
                                new_snap: dict[str, AnswerItem] = {}
                                if isinstance(answers_payload, list):
                                    for itm in answers_payload:
                                        if not isinstance(itm, dict):
                                            continue
                                        key = itm.get("key")
                                        value = itm.get("value")
                                        if key is None or value is None:
                                            continue
                                        new_snap[key] = AnswerItem(
                                            key=key,
                                            value=value,
                                            rationale=itm.get("rationale"),
                                        )
                                if new_snap:
                                    snapshot = new_snap
                            else:
                                final_parsed: AnswersResponse = final_msg.parsed  # type: ignore
                                snapshot = {i.key: i for i in final_parsed.answers}
                    except Exception:
                        pass
                    yield _emit(
                        {
                            "type": "done",
                            "answers": [i.model_dump() for i in snapshot.values()],
                        }
                    )
        except Exception as e:
            yield _emit({"type": "error", "detail": str(e)})

    # SSE-friendly headers to avoid buffering
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        sse_generator(), media_type="text/event-stream", headers=headers
    )
