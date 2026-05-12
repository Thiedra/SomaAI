"""
services/ai/base.py
Abstract base class for all AI service integrations.
Provides shared JSON parsing and error handling.
"""
import json
import re
import logging

logger = logging.getLogger(__name__)


class BaseAIService:
    """
    All AI providers must extend this class.
    Provides consistent JSON parsing across all AI features.
    """

    def call(self, prompt: str, max_tokens: int = 1000, feature: str = "unknown") -> dict:
        """Send a prompt and return parsed JSON. Must be implemented by subclass."""
        raise NotImplementedError("Subclasses must implement call()")

    def parse_json_response(self, raw: str) -> dict:
        """
        Parse JSON from AI response text.
        Handles markdown code fences that AI models sometimes wrap around JSON.
        Raises ValueError with a clear message if JSON is invalid.
        """
        # strip markdown fences like ```json ... ```
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse AI JSON response: {e}\n"
                f"Raw output (first 500 chars): {raw[:500]}"
            )
            raise ValueError(
                f"AI returned invalid JSON. Error: {e}. "
                f"Response preview: {raw[:200]}"
            )
