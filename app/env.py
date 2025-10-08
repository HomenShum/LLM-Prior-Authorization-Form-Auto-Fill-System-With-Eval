import os

import logfire
from dotenv import load_dotenv


def setup_env():
    load_dotenv()

    if logfire_token := os.getenv("LOGFIRE_KEY"):
        logfire.configure(token=logfire_token)
        logfire.instrument_asyncpg()


def get_openai_api_key():
    return os.getenv("OPENAI_API_KEY")
