"""
services/ai/base.py
Base class for all AI service integrations.
Provides shared JSON parsing and error handling used by Claude and OpenAI services.
"""
import json
import re
import logging

logger = logging.getLogger(__name__)


class BaseAIService:
    """
    Abstract base for AI services.
    All AI providers (Claude, OpenAI) must extend this class.
    """

    def call(self, prompt: str, max_tokens: int = 1000) -> dict:
        """
        Send a prompt to the AI provider and return parsed JSON.
        Must be implemented by each subclass.
        """
        raise NotImplementedError("Subclasses must implement call()")

    def parse_json_response(self, raw: str) -> dict:
        """
        Parse JSON from AI response text.
        Strips markdown code fences (```json ... ```) if present.
        Raises ValueError with a clear message if parsing fails.
        """
        # remove markdown code fences if the AI wrapped the JSON in them
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON response: {e}\nRaw: {raw}")
            raise ValueError(f"AI returned invalid JSON: {e}")
