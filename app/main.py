from fastapi import FastAPI

from app.env import setup_env

from .models import AnswerInput, AnswerOutput

setup_env()


# Initialize the FastAPI application
app = FastAPI(
    title="Pharmacy Prior Authorization API",
    description="API for generating answers to prior authorization questions using patient data",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Pharmacy Prior Authorization API is running",
        "status": "healthy",
    }


@app.post("/answers")
async def get_answers(data: AnswerInput) -> AnswerOutput:
    """
    Generate answers to prior authorization questions based on patient data.

    This endpoint accepts patient information and a list of questions,
    then uses LLM to generate appropriate answers based on the patient's
    medical history, current medications, and other relevant data.
    """
    ## TODO: Implement your logic here
    # Example response structure - replace with actual LLM implementation
    return AnswerOutput(answers=[])
