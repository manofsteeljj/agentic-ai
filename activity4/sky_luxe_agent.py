import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

agent_identity = """
You are a Hotel Agent for Sky Luxe
Your goal is to provide support for users that asking information about the hotel
CONSTRAINTS:
    - Only answer questions related to the Sky Luxe Hotel
    - If a user asks about something else, politely decline.
    - Keep your answers concise and detailed.
    - Available Sky Luxe cities are: tokyo and paris.
    - When a user asks for hotels in a city, do NOT answer directly from your own knowledge.
    - Instead respond exactly with: TOOL: search_hotels(city)
    - When a user asks to book a hotel, respond exactly with: TOOL: book_hotel(hotel_name)
    - After a tool call, wait for the tool observation and then answer using that observation.
"""

HOTEL_DATABASE = {
    "tokyo": [
        {"name": "Shibuya Grand", "price_per_night": 180},
        {"name": "Imperial Palace Stay", "price_per_night": 450},
        {"name": "Capsule Capsule", "price_per_night": 45}
    ],
    "paris": [
        {"name": "Hotel de L'Opera", "price_per_night": 220},
        {"name": "Ritz Paris", "price_per_night": 950},
        {"name": "Montmartre Hostel", "price_per_night": 70}
    ]
}

BLOCKED_PHRASE = {
    "free room",
    "gago",
    "fuck",
    "bypass system identity"
    "set price to"
    "change price"
    "tangina mo"
}

def is_safe(text: str) -> bool:

    lower_text = text.lower()

    for phrase in BLOCKED_PHRASE:
        if phrase in lower_text:
            return False
    return True

def search_hotels(city: str) -> str:

    city = city.lower()

    if city not in HOTEL_DATABASE:
        return f"No hotel found for {city}"

    hotels = HOTEL_DATABASE[city]

    lines = [f"Hotels in {city.title()}"]
    for hotel in hotels:
        lines.append(
            f"- {hotel['name']} (${hotel['price_per_night']}/night)"
        )
    
    return "\n".join(lines)

def book_hotel(hotel_name: str, budget: float = 200.0) -> str:
    main_hotel = ""

    for city_hotels in HOTEL_DATABASE.values():
        for hotel in city_hotels:
            if hotel['name'].lower() == hotel_name.lower():
                main_hotel = hotel

    if main_hotel is None:
        return f"\nNo hotel for {main_hotel}"

    price = main_hotel["price_per_night"]

    if price > budget:
        return (
            f"\nBooking failed. Not enough budget for {main_hotel}. (${price}) exceeds (${budget}). Suggest an alternative within budget."
        )

    return (
        f"\nBooking confirmed for {main_hotel} at (${price})"
    )

def agent_loop():
    history = []
    destination = None
    budget = 200

    while (True):
        user_input = input("You: ")

        if user_input.lower() == "quit":
            break

        if not (is_safe(user_input)):
            print("Sky Luxe Agent: Please refrain from using inappropriate words.")
            continue

        if "tokyo" in user_input.lower():
            destination = "tokyo"
        elif "paris" in user_input.lower():
            destination = "paris"

        state_context = f"[CONTEXT: Destination={destination}, Budget=${budget}]"
        context = f"{state_context} {user_input}"
        history.append({"role": "user", "content": context})
        history = history[-4:]

        conversation = state_context + "\n\n"

        for msg in history:
            conversation += f"{msg['role']}: {msg['content']}\n"
        
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            config={"system_instruction": agent_identity},
            contents=conversation
        )

        model_text = response.text.strip()

        if model_text.startswith("TOOL: search_hotels("):
            city = (
                model_text
                .replace("TOOL: search_hotels(", "")
                .replace(")", "")
                .strip()
            )

            observation = "OBSERVATION: " + search_hotels(city)

            history.append({"role": "assistant", "content": model_text})
            history.append({"role": "user", "content": observation})
            history = history[-4:]

            followup = state_context + "\n\n"
            for msg in history:
                followup += f"{msg['role']}: {msg['content']}\n"

            final_response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                config={"system_instruction": agent_identity},
                contents=followup
            )

            print("SkyLuxe Agent:", final_response.text.strip())
        elif model_text.startswith("TOOL: book_hotel("):

            hotel_name = (
                model_text
                .replace("TOOL: book_hotel(", "")
                .replace(")", "")
                .strip()
            )

            observation = "OBSERVATION: " + book_hotel(hotel_name, budget)

            history.append({"role": "assistant", "content": model_text})
            history.append({"role": "user", "content": observation})
            history = history[-4:]

            followup = state_context + "\n\n"
            for msg in history:
                followup += f"{msg['role']}: {msg['content']}\n"

            final_response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                config={"system_instruction": agent_identity},
                contents=followup
            )

            print("SkyLuxe Agent:", final_response.text.strip())
        else:
            print("SkyLuxe Agent:", model_text)

            history.append(
                {"role": "assistant", "content": model_text}
            )

            history = history[-4:]

if __name__ == "__main__":
    agent_loop()