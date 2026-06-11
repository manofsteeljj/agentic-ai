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

# Identity
identity = """
    You are 'Japanese-American Support'
    Your goal is to provide support for users that asking for a information about software and hardware components for PC 
    CONSTRAINTS:
        - Only answer questions related to software and hardware components of a computer.
        - If a user asks about something else, politely decline in Japanese and English language.
        - Keep your answers concise and technical and use both Japanese and English language.
"""

# 3. Intialize working memory
chat = client.chats.create(
    model='gemini-3.1-flash-lite',
    config=types.GenerateContentConfig(
        system_instruction=identity
    )
)

# 4. Agent Loop
def agent_loop(user_input):
    # Simply send the message to the existing chat session.
    # It automatically remembers previous turns.
    response = chat.send_message(user_input)
    return response.text

def main():
    print("\n--- Agent is active. Type 'exit' to quit. ---")
    while True:
        try:
            user_msg = input("\nUser: ")
            if user_msg.lower() == 'exit':
                print("You're missing out the best bit! Goodbye!")
                break;

            if not user_msg.strip():
                continue

            response = agent_loop(user_msg)
            print(f"Agent: {response}" )
        except KeyboardInterrupt:
            print("\nSession interrupted. Exiting!")
            break;


if __name__ ==  "__main__":
    main()
