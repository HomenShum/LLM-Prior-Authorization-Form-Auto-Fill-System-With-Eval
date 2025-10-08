# AI / Product Engineering Project

Thank you for taking the time to complete our engineering take-home project. We appreciate the time and effort you put into this! We also want to use this as an opportunity for you to get a feel for how it would be to work with us at Develop Health. So with this project you'll implement a part of the Develop Health product 🎉


## Overview

The Develop Health prior authorization product makes it quick and easy for medical staff to complete prior authorization forms. We do this by using LLMs to answer the questions on the form in a fraction of the time it would take a human to do it. You're going to be implementing a small part of the backend that powers the form autofilling.

## Objective

Implement the `/answers` endpoint that accepts JSON with patient information and questions from a prior authorization form and returns answers to the questions. You can use an LLM of your choice to generate the answers.

#### Requirements
- Use an LLM of your choice to generate answers to the questions.
- The endpoint should return answers based on the provided patient information and form questions.
- Design the implementation to handle form questions and patient data efficiently.

#### Extras
If you have time after completing the core objective, feel free to choose any of these extras. These are not required but are meant to explore additional complexity:

- Waiting a few minutes for answers to be generated isn't a great user experience. Update the backend to return answers as they're generated, rather than waiting for all of them to complete.
- Optimize the implementation of the `/answers` endpoint. Use caching or other techniques to store frequently used or computationally expensive answers to enhance the system's performance and improve response times.
- Incorporate a feedback mechanism to continuously improve the system. Users can rate the accuracy and usefulness of the answers provided by the system. This feedback can then be used to refine the `get_answer` function and enhance its performance over time.

If you're more interested in the AI engineer role, you may consider some of the following:
- Explore and implement methods to optimize the prompts given to the LLM, without resorting to fine-tuning. This could include:
  - Using few-shot prompting to provide examples of how answers should be generated.
  - Implementing an actor-critic system to assess the results and iteratively improve the answer.
  - Experimenting with reasoning models and prompts optimized for them.
- Create an eval pipeline. You could consider using tools such as https://ai.pydantic.dev/ to make this easier.
- Set up an annotation UI so that our internal clinical staff could review answers and give feedback to the model to improve it. 


Or if you're more interested in the product engineer role, some more product leaning extras would be:
- Setting up a frontend for displaying the questions, answers, and AI explanations to providers so that they can review and modify before submitting.
- Making a UI for providers to upload clinical notes to trigger the answering flow.

Note that if you create a frontend we will be assessing the design and UX of it. Feel free to use AI designers to help!

## Time Commitment

The coding part of this exercise should take approximately 3 hours. In addition to that, we would like you to spend about 30 to 45 minutes writing about your design choices, any assumptions you made, and any tradeoffs you considered.

## Deliverables

1. A FastAPI application in Python that implements the `/answers` endpoint as described above.
2. A PR with the following description:
    - Overview of what you implemented and how
    - Design choices, assumptions, and tradeoffs
    - How you used AI tools in completing this project. See below for more details
3. A short (~5 min) loom (or similar video walkthrough) showing what you built and brief overview of the code. Please demonstrate the frontend if you chose to build one (not required).

## AI Tooling

You can and should be using AI tools to complete this! Use anything from Copilot to Claude Code or Lovable. We want this project to reflect what it'll be like to work at Develop Health, and we work to stay on the cutting edge of AI tools to ensure we're working as efficiently as possible.
We're excited to see what tools you used and how you used them. i.e.
- How did you prompt the LLM to get good results?
- What worked and didn't work if you tried to first vibe code this whole project?
- Is there a new tool you've come across that works better than others? Teach us all about it!

A few important things to note when completing this with AI:
1. As with a production application, you are responsible for the final output, not the AI. Make sure you understand the code, what it's doing, and why. The next stage in the interview process would be a live session to discuss the project in more detail. Answering why a certain piece is implemented a particular way with "Not sure, that's what the LLM did" isn't an ok answer.
2. With the state of vibe coding today, it's often easier to go broad vs deep (though we'll see if that is still a valid statement in 6 more months 😅). I.e. you could likely have the AI attempt all of the extra components and do a surface level solution to them all in the timeframe. That is ok, but won't give us a lot of interesting things to talk about. We'd prefer you go deeper into a few of the extra pieces and come with novel insights and tech challenges to discuss in the live session. Use this project as an opportunity to show your talents and what you can create outside of the limits of current AI.

### IMPORTANT

You may use AI tools to write code and arrive at the solution, however please be very mindful about using AI to write the PR descriptions or design write-ups, as it tends to produce slop. If you get tired of reading it - we probably will too.

## Submission

Please push commits to a new branch as you go. When you're finished, please run pre-commit, open a pull request against the dev branch and **submit the PR url on the submission link you received in a previous email**. We're looking forward to seeing what you come up with!

## Evaluation Criteria

We'll be evaluating your submission based on the following:

- Functionality: Does the application work as described in the instructions?
- Code Quality: Is the code easy to understand and maintain? Is it organized well? We're an early stage startup so plenty of times it's the right call to go with a 'hacky' solution that gets the job done quickly. What is important is to consciously choose these cases and document them well (which can be just a comment in the code).
- Testing: Are there adequate tests for the application? We don't expect (or want) you to write unit tests for everything. But an integration test or two is normally a good idea. If you don't have time to include these you can just outline what you would test in your write-up.
- Documentation: Is the application and its design well-documented?
- Design Write-Up: Do you clearly explain your design choices, assumptions, and tradeoffs?
- Innovative Design: Does the implementation demonstrate creative or thoughtful design decisions?

If any areas of the project description are unclear or seem ambiguous, please use your best judgement in order to move ahead. 

Best of luck! We're looking forward to your submission. 


## Project Structure

The project was set up with uv, using FastAPI, and Docker for containerization.

The project structure is as follows:

- `app/`: Main application directory
  - `main.py`: Contains the FastAPI application with an `/answers` endpoint
  - `models.py`: Pydantic models for request/response validation
  - `env.py`: Environment setup utilities
- `tests/`: Test suite
  - `test_answers.py`: Contains unit tests for the answers endpoint
- `scripts/`: Utility scripts
  - `generate_patient_data.py`: Generates comprehensive synthetic patient records
- `sample_data/`: Sample data files
  - `patient_data.json`: Sample patient data
  - `zepbound_question_set.json`: Sample prior authorization questions
  - `example_request.json`: Example request for the /answers endpoint
- `Dockerfile`: Used to build the Docker image
- `pyproject.toml` and `uv.lock`: Project metadata and dependencies managed by uv
- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `.gitignore`: Git ignore rules


### Prerequisites

- Python 3.10+ (supports up to Python 3.13)
- Docker (optional, for containerization)
- uv
- OpenAI API key or other LLM provider API key
- Pydantic Logfire account (optional, for observability)

### Installation

1. Clone the repository

```bash
git clone https://github.com/{your_name}/engineer-take-home.git
```

2. Navigate to the project directory

```bash
cd engineer-take-home
```

3. **Set up environment variables**

Create a `.env` file in the project root directory: 

```bash
cp .env.example .env
```

**Getting your API keys:**

- **OpenAI**: Go to [OpenAI API Keys](https://platform.openai.com/api-keys), sign up/login, and create a new API key
- **Anthropic (Claude)**: Visit [Anthropic Console](https://console.anthropic.com/) to get your API key
- **Google (Gemini)**: Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

**Setting up Pydantic Logfire (Optional):**

Pydantic Logfire provides observability and monitoring for your application, including:
- Request/response logging
- Performance metrics
- Error tracking
- LLM usage analytics

To set it up:

1. Sign up for a free account at [Pydantic Logfire](https://logfire.pydantic.dev/)
2. Create a new project and copy your token to your .env file

Once configured, you can view your application's logs, traces, and metrics at https://logfire-us.pydantic.dev/


4. Install the Python dependencies with uv

```bash
uv sync
```

5. Install pre-commit

```bash
uv run pre-commit install
```

### Build and Run with Docker

You can build the Docker image and run it using the following commands:

```bash
docker build -t engineer-take-home .
docker run -p 8000:8000 engineer-take-home
```

The application will be available at http://localhost:8000.

### Development Server

To run the development server locally (without Docker):

```bash
uv run uvicorn app.main:app --reload
```

The application will be available at http://localhost:8000 with hot reloading enabled.

### Usage

To use the `/answers` endpoint, make a POST request with a JSON body containing patient information and questions.

Example using curl:

```bash
curl -X POST "http://localhost:8000/answers" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d @sample_data/example_request.json
```

The endpoint currently returns an empty answers array `{"answers": []}` - this is where you'll implement your LLM integration.

### Running Tests

To run the test suite with Pytest, use the following command:

```bash
uv run pytest
```

**Note:** The tests currently fail because the `/answers` endpoint returns empty answers. This is expected behavior until you implement the core functionality.

### API Documentation

When the server is running, you can access:
- **Interactive API docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc documentation**: http://localhost:8000/redoc

### Troubleshooting/FAQ

**uv Issues**: If you encounter uv-related issues, try:
```bash
rm -rf .venv uv.lock  # Remove current environment and lock file
uv sync               # Reinstall dependencies
```