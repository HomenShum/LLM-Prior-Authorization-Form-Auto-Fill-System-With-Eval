from typing import Literal

from pydantic import BaseModel


class Question(BaseModel):
    type: Literal["text", "boolean"]
    key: str
    content: str
    visible_if: str | None = None


class QuestionSet(BaseModel):
    name: str
    questions: list[Question]


class Answer(BaseModel):
    question: Question
    value: str | bool
    rationale: str | None = None


class Prescription(BaseModel):
    medication: str
    dosage: str
    frequency: str
    duration: str


class Patient(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    prescription: Prescription
    visit_notes: list[str]


class AnswerInput(BaseModel):
    model_config = {"protected_namespaces": ()}

    patient: Patient
    question_set: QuestionSet
    # Optional clinician feedback notes to guide the LLM
    feedbacks: list[str] | None = None
    # Optional: request extra validation pass after initial generation
    validate: bool | None = None


# ---- File processing (PDF/text) ----
class FileItem(BaseModel):
    filename: str
    # Base64-encoded data URL for the file, e.g., "data:application/pdf;base64,...."
    file_data: str


class ProcessFilesRequest(BaseModel):
    method: Literal["files_api", "base64"]
    files: list[FileItem]


class ProcessFilesResponse(BaseModel):
    notes: list[str]
    errors: list[str] = []


class AnswerOutput(BaseModel):
    answers: list[Answer]
