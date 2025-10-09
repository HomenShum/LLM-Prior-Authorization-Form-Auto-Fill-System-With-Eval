import os
from typing import Literal

import dotenv
import openai
from pydantic import BaseModel, Field

dotenv.load_dotenv()

# print(f"Using OpenAI API key: {os.getenv('OPENAI_API_KEY')}")

client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

print(f"Using OpenAI SDK library version {openai.__version__}")


class ChatReply(BaseModel):
    type: Literal["chat"] = Field(description="Conversational reply for Q&A.")
    message: str = Field(description="Text to display in a chat bubble.")


class DocumentReply(BaseModel):
    type: Literal["document"] = Field(description="Copy-pasteable document.")
    body: str = Field(
        description="Full text of a document or code to show in a viewer."
    )


class Output(BaseModel):
    # Union → JSON Schema anyOf under `result`
    result: ChatReply | DocumentReply = Field(
        description="Either a chat reply or a document."
    )


messages = [
    {"role": "system", "content": "You are a helpful AI, aptly named 'Mumbles'."},
    {"role": "user", "content": "Do you actually mumble?"},
]

# Send the request with the updated response_format
try:
    completion = client.beta.chat.completions.parse(
        model="gpt-5-mini",
        messages=messages,
        response_format=Output,
        # max_completion_tokens=500,  # prevents runaway loops
        # top_p=0.4  # more constraint on token sampling
    )

    # Access the parsed response
    ai_response = completion.choices[0].message.parsed
    # print(ai_response)  # parsed object dump

    # Type detector: print the type and the text contents
    result = ai_response.result
    if result.type == "chat":
        print("result.type of chat detected")
        print(f"message: {result.message}")
    elif result.type == "document":
        print("result.type of document detected")
        print(f"body: {result.body}")
    else:
        # Fallback for unexpected types
        print("Issue: neither expected type was received")
        print(f"response: {completion.choices[0]}")

except Exception as e:
    print(f"An error occurred: {e}")

# Streaming
# Note: OpenAI and BaseModel already imported at top


class EntitiesModel(BaseModel):
    attributes: list[str]
    colors: list[str]
    animals: list[str]


streaming_client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

with streaming_client.beta.chat.completions.stream(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": "Extract entities from the input text"},
        {
            "role": "user",
            "content": "The quick brown fox jumps over the lazy dog with piercing blue eyes",
        },
    ],
    response_format=EntitiesModel,
) as stream:
    for event in stream:
        if event.type == "content.delta":
            if event.parsed is not None:
                # Print the parsed data as JSON
                print("content.delta parsed:", event.parsed)
        elif event.type == "content.done":
            print("content.done")
        elif event.type == "error":
            print("Error in stream:", event.error)

final_completion = stream.get_final_completion()
print("Final completion:", final_completion)
