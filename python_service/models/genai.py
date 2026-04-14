"""
models/genai.py
---------------
Gemini API integration for:
  • Itinerary narrative generation
  • Travel chatbot with conversation memory

Improvements:
  • ConversationMemory class with rolling-window truncation
  • Compact prompts to reduce token usage
  • Configurable model name (via config.py / env var)
  • Specific fallback messages for different error types
  • All public functions have thorough docstrings
"""

from __future__ import annotations

import logging
import os
from collections import deque
from typing import Deque, List, Tuple

import google.generativeai as genai
from dotenv import load_dotenv

from config import CHAT_MEMORY_TURNS, GEMINI_MODEL_NAME, NARRATIVE_MAX_WORDS

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# ─── Model Initialisation ─────────────────────────────────────────────────────

_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if _API_KEY:
    genai.configure(api_key=_API_KEY)
    _model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    logger.info("Gemini model initialised: %s", GEMINI_MODEL_NAME)
else:
    _model = None
    logger.warning("GEMINI_API_KEY not set — AI features disabled.")

_MAX_RETRIES = 3          # max retry attempts on 429
_RETRY_BASE_WAIT = 12.0   # seconds to wait before first retry


# ─── Retry Helper ─────────────────────────────────────────────────────────────

def _generate_with_retry(prompt: str) -> str:
    """
    Call _model.generate_content(prompt) with exponential-backoff retries
    on HTTP 429 (rate limit / quota exceeded) errors.

    Raises any non-429 exception immediately (or after all retries exhausted).
    Returns the response text on success.
    """
    import time
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = _model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str and attempt < _MAX_RETRIES:
                wait = _RETRY_BASE_WAIT * attempt
                logger.warning(
                    "Gemini 429 on attempt %d/%d — retrying in %.0fs",
                    attempt, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
            else:
                raise


# ─── Conversation Memory ──────────────────────────────────────────────────────

class ConversationMemory:
    """
    Rolling-window store of (user_message, assistant_reply) pairs.

    Keeps at most ``max_turns`` exchanges so that prompt size stays bounded.
    Each session should have its own ConversationMemory instance.
    """

    def __init__(self, max_turns: int = CHAT_MEMORY_TURNS) -> None:
        self.max_turns: int = max_turns
        self._history: Deque[Tuple[str, str]] = deque(maxlen=max_turns)

    def add(self, user_msg: str, assistant_msg: str) -> None:
        """Append a new exchange to memory."""
        self._history.append((user_msg, assistant_msg))

    def format_for_prompt(self) -> str:
        """
        Return memory as a compact multi-line string for injection into prompts.
        Format: 'User: …\\nAssistant: …\\n'
        """
        if not self._history:
            return ""
        lines = []
        for user_msg, asst_msg in self._history:
            lines.append(f"User: {user_msg}")
            lines.append(f"Assistant: {asst_msg}")
        return "\n".join(lines) + "\n"

    def clear(self) -> None:
        """Reset conversation history."""
        self._history.clear()

    def __len__(self) -> int:
        return len(self._history)


# ─── Itinerary Narrative ──────────────────────────────────────────────────────

def generate_itinerary_narrative(
    city: str,
    day_plan: List[dict],
    user_preferences: dict,
) -> str:
    """
    Generate a short narrative (~100 words) for a single day's itinerary.

    Parameters
    ----------
    city             : destination city name
    day_plan         : list of POI dicts with at least {'name': str, 'category': str}
    user_preferences : dict of interest → 0|1 (e.g. {'Nature': 1, 'Heritage': 0})

    Returns a narrative string, or a safe fallback on failure.
    """
    if _model is None:
        return "AI narration unavailable — API key missing."

    if not day_plan:
        return f"Enjoy a relaxing free day exploring {city} at your own pace!"

    poi_names = ", ".join(p["name"] for p in day_plan)
    interests  = ", ".join(k for k, v in user_preferences.items() if v)
    interests  = interests or "general sightseeing"

    # Compact prompt — estimated ~80 tokens
    prompt = (
        f"Write a vivid {NARRATIVE_MAX_WORDS}-word travel narrative for a day in {city}. "
        f"Stops (in order): {poi_names}. "
        f"Traveller interests: {interests}. "
        "Weave a flowing story — don't just list places."
    )

    try:
        return _generate_with_retry(prompt)
    except genai.types.BlockedPromptException:
        logger.warning("Narrative prompt was blocked by safety filters.")
        return f"Discover {city}'s highlights through these carefully chosen stops!"
    except Exception as exc:
        logger.error("Narrative generation failed: %s", exc)
        return f"Enjoy exploring {city} — these spots promise an unforgettable day!"


# ─── Chatbot ──────────────────────────────────────────────────────────────────

def chat_with_ai(
    message: str,
    itinerary: dict | None = None,
    memory: ConversationMemory | None = None,
) -> str:
    """
    Answer a travel-related user message, optionally with itinerary context
    and rolling conversation memory.

    Parameters
    ----------
    message   : the user's latest message
    itinerary : optional itinerary dict from /api/plan-trip response
    memory    : optional ConversationMemory instance for multi-turn chats

    Returns assistant reply string.
    """
    if _model is None:
        return "AI assistant unavailable — API key not configured."

    # Build compact itinerary context (only if provided)
    itinerary_block = ""
    if itinerary and isinstance(itinerary.get("itinerary"), dict):
        lines = []
        for day, details in itinerary["itinerary"].items():
            names = ", ".join(p["name"] for p in details.get("pois", []))
            lines.append(f"{day.capitalize()}: {names}")
        if lines:
            itinerary_block = (
                "[Itinerary]\n" + "\n".join(lines) + "\n[/Itinerary]\n\n"
            )

    # Build conversation history block
    history_block = ""
    if memory and len(memory) > 0:
        history_block = "[History]\n" + memory.format_for_prompt() + "[/History]\n\n"

    prompt = (
        "You are Wanderly AI, a friendly travel assistant. "
        "Answer travel questions concisely and helpfully. "
        "For non-travel topics, politely redirect.\n\n"
        f"{itinerary_block}"
        f"{history_block}"
        f"User: {message}\n"
        "Wanderly AI:"
    )

    try:
        reply = _generate_with_retry(prompt)

        # Update memory with this exchange
        if memory is not None:
            memory.add(message, reply)

        return reply
    except genai.types.BlockedPromptException:
        logger.warning("Chat prompt blocked by Gemini safety filters.")
        return "I can't answer that, but I'm happy to help with your travel plans!"
    except Exception as exc:
        logger.error("Chat generation failed: %s", exc)
        return "I'm having trouble connecting right now. Please try again in a moment."
