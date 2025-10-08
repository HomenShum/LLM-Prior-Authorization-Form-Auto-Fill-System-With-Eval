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
    patient: Patient
    question_set: QuestionSet


class AnswerOutput(BaseModel):
    answers: list[Answer]
