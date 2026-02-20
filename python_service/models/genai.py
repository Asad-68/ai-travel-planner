import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

API_KEY = os.environ.get("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    model = None

def generate_itinerary_narrative(city, day_plan, user_preferences):
    if not model:
        return "AI narration unavailable (API Key missing)."

    pois = ", ".join([p['name'] for p in day_plan])
    interests = ", ".join([k for k, v in user_preferences.items() if v == 1])

    prompt = (
        f"You are an expert travel guide. Write a comprehensive, engaging summary (approx 100-120 words) for a day trip in {city}. "
        f"The itinerary includes these places in order: {pois}. "
        f"The traveler is interested in: {interests}. "
        "Explain the flow of the day, why these spots are great, and what unique experiences they offer. "
        "Do not just list them; weave a narrative of the day's journey. "
        "Mention specific details about the city's vibe and what makes this route special."
    )

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "Enjoy your day exploring these beautiful locations!"

def chat_with_ai(message, itinerary=None):
    if not model:
        return "I'm sorry, my AI brain is sleeping (API Key missing). Please check your configuration."

    try:
        itinerary_context = ""
        if itinerary and "itinerary" in itinerary:
            itinerary_summary = []
            for day, details in itinerary["itinerary"].items():
                pois = ", ".join([p["name"] for p in details.get("pois", [])])
                itinerary_summary.append(f"{day.capitalize()}: {pois}")

            itinerary_context = (
                "\n--- Current Itinerary Context ---\n"
                f"The user has generated an itinerary for {itinerary.get('num_days', 'some')} days. "
                "The planned stops are:\n" + "\n".join(itinerary_summary) + "\n"
                "-----------------------------------\n\n"
            )

        prompt = (
            "You are Wanderly AI, a highly knowledgeable and friendly travel assistant. "
            "Your goal is to help users with ANY travel-related questions, including their specific itinerary. "
            f"{itinerary_context}"
            "Answer the following question. If the user asks about 'my trip' or specific days, "
            "refer to the itinerary context provided above. "
            "\n\n"
            "Keep your answers helpful, concise, and professional. "
            "If a question is completely unrelated to travel, politely redirect them.\n\n"
            f"User Query: {message}\n"
            "Wanderly AI:"
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "I'm having trouble connecting to the travel network right now. Please try again later."
