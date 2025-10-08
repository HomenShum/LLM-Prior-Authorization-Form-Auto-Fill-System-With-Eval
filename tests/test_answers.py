import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import AnswerInput, Patient, Question, QuestionSet

client = TestClient(app)


# Create a fixture for loading test data from sample data directory
@pytest.fixture
def test_data():
    # Load patient data
    with open("sample_data/patient_data.json") as f:
        patients_data = json.load(f)

    # Load question set
    with open("sample_data/zepbound_question_set.json") as f:
        questions_data = json.load(f)

    # Use the first patient from the sample data and create Patient model
    patient = Patient(**patients_data[0])

    # Create Question models from the loaded data
    questions = [Question(**q) for q in questions_data]

    # Create QuestionSet model
    question_set = QuestionSet(name="Zepbound Prior Authorization", questions=questions)

    # Create AnswerInput model
    answer_input = AnswerInput(patient=patient, question_set=question_set)

    return answer_input


def test_get_answers(test_data):
    response = client.post("/answers", json=test_data.model_dump())
    assert response.status_code == 200
    assert "answers" in response.json()
    assert len(response.json()["answers"]) > 0
