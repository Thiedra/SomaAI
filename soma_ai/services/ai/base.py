"""
services/ai/base.py
Abstract base class for all AI service integrations.
"""
import json
import re
import logging

logger = logging.getLogger(__name__)


class BaseAIService:

    def call(self, prompt: str, max_tokens: int = 1000, feature: str = "unknown") -> dict:
        """Send a prompt, return parsed JSON dict. For structured data only."""
        raise NotImplementedError

    def call_text(
        self,
        prompt: str,
        system_prompt: str = "",
        messages: list = None,
        max_tokens: int = 800,
        feature: str = "unknown",
    ) -> str:
        """Send a prompt, return plain text string. For conversational responses."""
        raise NotImplementedError

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        chat_history: list = None,
    ):
        """Stream tokens one by one. For SSE tutor endpoint."""
        raise NotImplementedError

    def parse_json_response(self, raw: str) -> dict:
        """Parse JSON from AI response. Strips markdown fences if present."""
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI JSON: {e}\nRaw: {raw[:500]}")
            raise ValueError(f"AI returned invalid JSON: {e}")
