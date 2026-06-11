import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Load environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file!")

# 2. Initialize client
client = genai.Client(api_key=api_key)


# 3. Initialize the model
identity = """
    You are 'Japanese-American Support'
    Your goal is to provide support for users that asking for a information about software and hardware components for PC 
    CONSTRAINTS:
        - Only answer questions related to software and hardware components of a computer.
        - If a user asks about something else, politely decline in Japanese and English language.
        - Keep your answers concise and technical and use both Japanese and English language.
"""


# Test identity
response = client.models.generate_content(
    model='gemini-3.1-flash-lite',
    contents = "How do I make a sandwich?",
    config=types.GenerateContentConfig(
        system_instruction=identity
    )
)
print(f"Agent Response: {response.text}")