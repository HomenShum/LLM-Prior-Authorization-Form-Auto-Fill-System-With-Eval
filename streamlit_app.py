import json
import os

import requests
import streamlit as st

# -----------------------------
# Config
# -----------------------------
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
ANSWERS_URL = f"{API_BASE}/answers"
STREAM_URL = f"{API_BASE}/answers/stream"
SAMPLE_PATIENTS_PATH = "sample_data/patient_data.json"
SAMPLE_QUESTIONS_PATH = "sample_data/zepbound_question_set.json"

st.set_page_config(page_title="Clinical PA Auto-Fill Demo", layout="wide")


# -----------------------------
# Data loaders
# -----------------------------
@st.cache_data(show_spinner=False)
def load_patients() -> list[dict]:
    with open(SAMPLE_PATIENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_questions() -> list[dict]:
    with open(SAMPLE_QUESTIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


patients = load_patients()
questions = load_questions()


# Helpers to key per patient
def make_patient_key(p: dict) -> str:
    return f"{p.get('first_name', '')}|{p.get('last_name', '')}|{p.get('date_of_birth', '')}"


# Initialize session state
if "form_values" not in st.session_state:
    st.session_state.form_values = {}
if "form_rationales" not in st.session_state:
    st.session_state.form_rationales = {}
if "extra_notes_by_patient" not in st.session_state:
    st.session_state.extra_notes_by_patient = {}
if "feedbacks_by_patient" not in st.session_state:
    st.session_state.feedbacks_by_patient = {}
if "deleted_notes_stack_by_patient" not in st.session_state:
    st.session_state.deleted_notes_stack_by_patient = {}
if "deleted_feedback_stack_by_patient" not in st.session_state:
    st.session_state.deleted_feedback_stack_by_patient = {}

# -----------------------------
# Sidebar: patient selector and details
# -----------------------------
st.sidebar.header("Patient Selection")
patient_labels = [
    f"{p['first_name']} {p['last_name']} ({p['prescription']['medication']})"
    for p in patients
]
selected_idx = st.sidebar.selectbox(
    "Choose a patient",
    options=list(range(len(patients))),
    format_func=lambda i: patient_labels[i],
)
selected_patient = patients[selected_idx]
patient_key = make_patient_key(selected_patient)

st.sidebar.subheader("Patient details")
st.sidebar.write(
    f"Name: {selected_patient['first_name']} {selected_patient['last_name']}"
)
st.sidebar.write(f"DOB: {selected_patient['date_of_birth']}")
st.sidebar.write(f"Gender: {selected_patient['gender']}")
rx = selected_patient.get("prescription", {})
st.sidebar.write(
    f"Rx: {rx.get('medication', '?')} {rx.get('dosage', '?')} {rx.get('frequency', '')}"
)
st.sidebar.caption("Visit notes")
base_notes = selected_patient.get("visit_notes", [])
base_len = len(base_notes)

extra_notes = st.session_state.extra_notes_by_patient.get(patient_key, [])
notes = base_notes + extra_notes
# add a fixed height container
with st.sidebar.container(height=250):
    if notes:
        for i, note in enumerate(notes, 1):
            idx = i - 1
            is_extra = idx >= base_len
            label = f"Visit note {i}" + (" (uploaded)" if is_extra else "")
            with st.expander(label):
                st.write(note)
                colA, colB = st.columns([3, 1])
                with colB:
                    del_clicked = st.button(
                        "Delete",
                        key=f"del_note_{patient_key}_{idx}",
                        use_container_width=True,
                        disabled=not is_extra,
                        help=None if is_extra else "Base note cannot be deleted",
                    )
                if is_extra and del_clicked:
                    extra_idx = idx - base_len
                    cur = st.session_state.extra_notes_by_patient.get(
                        patient_key, []
                    ).copy()
                    if 0 <= extra_idx < len(cur):
                        removed = cur.pop(extra_idx)
                        # Update session state
                        st.session_state.extra_notes_by_patient[patient_key] = cur
                        # Push to undo stack
                        stack = st.session_state.deleted_notes_stack_by_patient.get(
                            patient_key, []
                        )
                        st.session_state.deleted_notes_stack_by_patient[patient_key] = (
                            stack + [{"index": extra_idx, "content": removed}]
                        )
                        st.success("Note deleted")
                        st.rerun()
    # Undo last deleted uploaded note
    note_stack = st.session_state.deleted_notes_stack_by_patient.get(patient_key, [])
    if note_stack:
        if st.button(
            "↩️ Undo last note delete",
            key=f"undo_note_{patient_key}",
            use_container_width=True,
        ):
            item = note_stack.pop()
            cur = st.session_state.extra_notes_by_patient.get(patient_key, []).copy()
            ins_idx = min(max(item.get("index", 0), 0), len(cur))
            cur.insert(ins_idx, item.get("content", ""))
            st.session_state.extra_notes_by_patient[patient_key] = cur
            st.session_state.deleted_notes_stack_by_patient[patient_key] = note_stack
            st.success("Restored deleted note")
            st.rerun()

with st.sidebar.container(height=400):
    # Raw text input for a note
    raw_note = st.text_area(
        "Paste raw note text",
        key=f"raw_note_{patient_key}",
        height=120,
        placeholder="Paste note text here…",
    )
    add_raw = st.button("Add raw text note", use_container_width=True)

    st.divider()
    st.caption("Limits: Each file < 10 MB; Combined per request < 32 MB.")
    pdf_method = st.radio(
        "PDF processing",
        ["Files API upload", "Base64 encode"],
        horizontal=True,
        key=f"pdf_method_{patient_key}",
        help="Choose how PDFs are sent to the model. Base64 uses Chat Completions; Files API uses Responses API.",
    )

    # Upload notes: support .txt, .md, and .pdf (PDF via OpenAI extraction)
    uploaded_files = st.file_uploader(
        "Upload visit notes (.txt, .md, .pdf)",
        type=["txt", "md", "pdf"],
        accept_multiple_files=True,
        key="notes_uploader",
    )

    add_files = st.button("Add uploaded notes", use_container_width=True)

    if add_files and uploaded_files:
        # Pre-read files and enforce size limits
        per_file_limit = 10 * 1024 * 1024  # 10 MB
        total_limit = 32 * 1024 * 1024  # 32 MB
        files_info = []
        total_bytes = 0
        for uf in uploaded_files:
            name = getattr(uf, "name", "uploaded")
            data = uf.read()
            size = len(data) if data is not None else 0
            ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
            if size > per_file_limit:
                st.error(
                    f"{name} is {size / 1024 / 1024:.2f} MB, exceeds 10 MB per-file limit."
                )
                continue
            files_info.append({"name": name, "data": data, "size": size, "ext": ext})
            total_bytes += size
        if not files_info:
            st.warning("No valid files to process.")
        elif total_bytes > total_limit:
            st.error(
                f"Selected files total {total_bytes / 1024 / 1024:.2f} MB, exceeds 32 MB request limit. Upload fewer or smaller files."
            )
        else:
            new_notes: list[str] = []
            total = len(files_info)
            progress = st.progress(0)
            status = st.empty()
            for idx_file, info in enumerate(files_info, start=1):
                filename = info["name"]
                data = info["data"]
                ext = info["ext"]
                status.write(f"Processing {idx_file}/{total}: {filename}")
                if ext in ("txt", "md"):
                    try:
                        content = data.decode("utf-8", errors="ignore").strip()
                        if content:
                            new_notes.append(content)
                    except Exception as e:
                        st.warning(f"Failed to read {filename}: {e}")
                elif ext == "pdf":
                    # Use backend API for PDF processing
                    import base64

                    with st.spinner(f"Processing PDF: {filename}"):
                        b64 = base64.b64encode(data).decode("utf-8")
                        file_data_url = f"data:application/pdf;base64,{b64}"

                        method = (
                            "files_api"
                            if pdf_method == "Files API upload"
                            else "base64"
                        )
                        payload = {
                            "method": method,
                            "files": [
                                {"filename": filename, "file_data": file_data_url}
                            ],
                        }

                        try:
                            resp = requests.post(
                                f"{API_BASE}/process-files", json=payload, timeout=120
                            )
                            if resp.status_code == 200:
                                result = resp.json()
                                if result.get("notes"):
                                    new_notes.extend(result["notes"])
                                if result.get("errors"):
                                    for err in result["errors"]:
                                        st.warning(err)
                            else:
                                st.error(f"API error {resp.status_code}: {resp.text}")
                        except Exception as e:
                            st.error(f"Failed to process {filename}: {e}")
                progress.progress(idx_file / total)
            status.empty()
            if new_notes:
                cur = st.session_state.extra_notes_by_patient.get(patient_key, [])
                st.session_state.extra_notes_by_patient[patient_key] = cur + new_notes
                st.success(f"Added {len(new_notes)} note(s)")
                st.rerun()

    if add_raw and raw_note and raw_note.strip():
        cur = st.session_state.extra_notes_by_patient.get(patient_key, [])
        st.session_state.extra_notes_by_patient[patient_key] = cur + [raw_note.strip()]
        st.success("Added 1 note from raw text")
        st.rerun()

# Clinician feedback (not patient-specific, applies to all cases)
st.sidebar.divider()
st.sidebar.caption("Clinician Feedback Notes")
st.sidebar.caption(
    "(These notes are added by clinicians and will be included in the AI context)"
)
existing_fbs = st.session_state.feedbacks_by_patient.get(patient_key, [])
if existing_fbs:
    st.sidebar.caption(f"{len(existing_fbs)} feedback note(s)")
    for i, fb in enumerate(existing_fbs):
        c1, c2 = st.sidebar.columns([8, 2])
        with c1:
            st.markdown(f"- {fb}")
        with c2:
            if st.button("🗑️", key=f"del_fb_{patient_key}_{i}"):
                stack = st.session_state.deleted_feedback_stack_by_patient.get(
                    patient_key, []
                )
                st.session_state.deleted_feedback_stack_by_patient[patient_key] = (
                    stack + [{"index": i, "content": fb}]
                )
                arr = existing_fbs.copy()
                arr.pop(i)
                st.session_state.feedbacks_by_patient[patient_key] = arr
                st.rerun()
    fb_stack = st.session_state.deleted_feedback_stack_by_patient.get(patient_key, [])
    if fb_stack and st.sidebar.button(
        "↩️ Undo last feedback delete", key=f"undo_fb_{patient_key}"
    ):
        item = fb_stack.pop()
        arr = st.session_state.feedbacks_by_patient.get(patient_key, []).copy()
        ins_idx = min(max(item.get("index", 0), 0), len(arr))
        arr.insert(ins_idx, item.get("content", ""))
        st.session_state.feedbacks_by_patient[patient_key] = arr
        st.session_state.deleted_feedback_stack_by_patient[patient_key] = fb_stack
        st.success("Restored feedback")
        st.rerun()
fb_input_key = f"fb_input_{patient_key}"
fb_text = st.sidebar.text_area(
    "Add clinician feedback note",
    key=fb_input_key,
    height=100,
    placeholder="Enter clinical observations, concerns, or additional context...",
)
if st.sidebar.button("Save feedback note"):
    if fb_text and fb_text.strip():
        cur = st.session_state.feedbacks_by_patient.get(patient_key, [])
        st.session_state.feedbacks_by_patient[patient_key] = cur + [fb_text.strip()]
        st.success("Feedback note saved")
        st.rerun()

# -----------------------------
# Auto-fill controls in sidebar
# -----------------------------
st.sidebar.divider()
st.sidebar.subheader("Auto-Fill Controls")

# Validation option
enable_validation = st.sidebar.checkbox(
    "Enable extra validation pass",
    value=False,
    help="Run a second LLM call to validate and correct the initial answers",
    key="enable_validation",
)

# Auto-fill button
if st.sidebar.button(
    "🤖 Auto-Fill with AI",
    use_container_width=True,
    type="primary",
    key="auto_fill_btn",
):
    st.session_state.trigger_autofill = True
    st.rerun()

# -----------------------------
# Main content
# -----------------------------
st.title("Clinical Prior-Authorization Auto-Fill")
st.markdown(
    "Select a patient and click Submit to auto-fill answers using OpenAI Structured Outputs."
)

mode = st.radio(
    "Mode",
    ["Standard", "Streaming"],
    horizontal=True,
    help="Standard waits for the full JSON. Streaming shows fields as they arrive.",
)


with st.form("auto_fill_form"):
    st.subheader("Question Set: Zepbound Prior Authorization")
    st.caption(
        "Fill in the fields manually or click 'Auto-Fill with AI' to populate from patient data."
    )

    # Create interactive form fields based on question type
    form_inputs = {}
    for q in questions:
        key = q["key"]
        content = q["content"]
        qtype = q["type"]

        # Get default value from session state if available
        default_val = st.session_state.form_values.get(key)

        if qtype == "boolean":
            # Use checkbox for boolean questions
            form_inputs[key] = st.checkbox(
                content,
                value=bool(default_val) if default_val is not None else False,
                key=f"input_{key}",
                help=f"Key: {key}",
            )
        else:
            # Use text input for text questions
            form_inputs[key] = st.text_input(
                content,
                value=str(default_val) if default_val else "",
                key=f"input_{key}",
                help=f"Key: {key}",
                placeholder="Enter value or use Auto-Fill",
            )

        # Show rationale if available
        if key in st.session_state.form_rationales:
            st.caption(f"💡 {st.session_state.form_rationales[key]}")

    # Submit button for manual form submission
    manual_submit = st.form_submit_button(
        "📋 Submit Form", use_container_width=True, type="primary"
    )

# Containers for results
standard_container = st.container()
stream_container = st.container()

# Handle manual form submission
if manual_submit:
    st.session_state.form_values = form_inputs.copy()
    st.success("✅ Form submitted!")

    # Prepare form data for download
    import json as json_lib

    form_data = {
        "patient": {
            "name": f"{selected_patient['first_name']} {selected_patient['last_name']}",
            "dob": selected_patient["date_of_birth"],
            "gender": selected_patient["gender"],
        },
        "form": "Zepbound Prior Authorization",
        "answers": [],
    }

    qmap = {q["key"]: q for q in questions}
    for key, value in form_inputs.items():
        q = qmap.get(key, {})
        form_data["answers"].append(
            {
                "question": q.get("content", key),
                "answer": value,
                "rationale": st.session_state.form_rationales.get(key, ""),
            }
        )

    # Offer download
    st.download_button(
        label="📥 Download Form as JSON",
        data=json_lib.dumps(form_data, indent=2),
        file_name=f"pa_form_{selected_patient['first_name']}_{selected_patient['last_name']}.json",
        mime="application/json",
        use_container_width=True,
    )

# Handle auto-fill trigger
if st.session_state.get("trigger_autofill", False):
    st.session_state.trigger_autofill = False

    # Build AnswerInput payload per app.models
    base_notes = selected_patient.get("visit_notes", [])
    extra_notes = st.session_state.extra_notes_by_patient.get(patient_key, [])
    patient_payload = dict(selected_patient)
    patient_payload["visit_notes"] = base_notes + extra_notes
    feedbacks = st.session_state.feedbacks_by_patient.get(patient_key, [])
    payload = {
        "patient": patient_payload,
        "question_set": {
            "name": "Zepbound Prior Authorization",
            "questions": questions,
        },
        "feedbacks": feedbacks,
        "validate": enable_validation,
    }

    if mode == "Standard":
        with st.spinner("Calling /answers (standard)…"):
            resp = requests.post(ANSWERS_URL, json=payload, timeout=600)
        if resp.status_code != 200:
            st.error(f"Error {resp.status_code}: {resp.text}")
        else:
            data = resp.json()
            # Update session state with AI-filled values and rationales
            qmap = {q["key"]: q for q in questions}
            for ans in data.get("answers", []):
                q = ans.get("question", {})
                key = q.get("key")
                st.session_state.form_values[key] = ans.get("value")
                rationale = ans.get("rationale")
                if rationale:
                    st.session_state.form_rationales[key] = rationale

            # Render answers with rationales
            standard_container.subheader("✨ Auto-Filled Answers")
            if data.get("answers"):
                for ans in data.get("answers", []):
                    q = ans.get("question", {})
                    key = q.get("key")
                    content = q.get("content", "")
                    value = ans.get("value")
                    rationale = ans.get("rationale")

                    standard_container.markdown(f"**{content}**")
                    standard_container.write(f"Answer: `{value}`")
                    if rationale:
                        standard_container.caption(f"💡 Rationale: {rationale}")
                    standard_container.divider()

                standard_container.success(
                    "Form fields updated! Scroll up to review and edit if needed."
                )
            else:
                standard_container.info("No answers returned.")

            # Trigger rerun to update form with new values
            st.rerun()
    else:
        # Streaming mode
        stream_container.subheader("🌊 Streaming Auto-Fill (live updates)")
        placeholders: dict[str, st.delta_generator.DeltaGenerator] = {}
        qmap = {q["key"]: q for q in questions}
        # Create a placeholder line for each key
        for q in questions:
            placeholders[q["key"]] = stream_container.empty()

        with st.spinner("Streaming from /answers/stream…"):
            try:
                with requests.post(
                    STREAM_URL, json=payload, stream=True, timeout=180
                ) as r:
                    if r.status_code != 200:
                        st.error(f"Error {r.status_code}: {r.text}")
                    else:
                        for raw in r.iter_lines(decode_unicode=True):
                            if not raw:
                                continue
                            if not raw.startswith("data: "):
                                continue
                            try:
                                event = json.loads(raw[6:])
                            except Exception:
                                continue
                            etype = event.get("type")
                            if etype == "update":
                                for itm in event.get("answers", []):
                                    key = itm.get("key")
                                    val = itm.get("value")
                                    # Update session state
                                    st.session_state.form_values[key] = val
                                    question_text = qmap.get(key, {}).get(
                                        "content", key
                                    )
                                    placeholders[key].markdown(
                                        f"**{key}** — {question_text}: <span style='color:#0b72b9'>{val}</span>",
                                        unsafe_allow_html=True,
                                    )
                            elif etype == "error":
                                stream_container.error(
                                    event.get("detail", "Streaming error")
                                )
                            elif etype == "done":
                                stream_container.success(
                                    "✅ Streaming complete! Form fields updated. Scroll up to review and edit if needed."
                                )
                                # Trigger rerun to update form with new values
                                st.rerun()
                                break
            except requests.RequestException as e:
                stream_container.error(f"Stream error: {e}")

st.divider()
st.caption(
    "Tip: Run FastAPI with `uvicorn app.main:app --reload` and then run this app with `streamlit run streamlit_app.py`. Configure API_BASE_URL env var if needed."
)
