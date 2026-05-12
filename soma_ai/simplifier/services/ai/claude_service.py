"""
simplifier/services/ai/claude_service.py
Claude (Anthropic) AI service.
Shared across all apps: simplifier, quizzes, planner, career.
Import path: from simplifier.services.ai.claude_service import ClaudeService
"""
import time
import logging
from django.conf import settings
from .base import BaseAIService

logger = logging.getLogger(__name__)


class ClaudeService(BaseAIService):
    """
    Wraps the Anthropic Claude API.
    Every call is logged to AIRequestLog — success or failure.
    Used by all AI features in Soma AI.
    """

    MODEL = "claude-opus-4-5"

    def call(self, prompt: str, max_tokens: int = 1000, feature: str = "unknown") -> dict:
        """
        Send a prompt to Claude and return a parsed JSON dict.

        Args:
            prompt: Full prompt string to send.
            max_tokens: Maximum tokens in the response.
            feature: Calling feature name for logging (simplifier, quizzes, planner, career).

        Returns:
            Parsed dict from Claude's JSON response.

        Raises:
            ValueError: If ANTHROPIC_API_KEY is missing or Claude returns invalid JSON.
        """
        import anthropic
        from core.models import AIRequestLog

        start_time = time.time()
        call_status = "success"
        error_message = ""

        try:
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError(
                    "ANTHROPIC_API_KEY is not set in your .env file. "
                    "Get your key from https://console.anthropic.com/"
                )

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            message = client.messages.create(
                model=self.MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = message.content[0].text
            logger.debug(f"Claude raw response [{feature}]: {raw_text[:300]}")

            return self.parse_json_response(raw_text)

        except Exception as e:
            call_status = "failed"
            error_message = str(e)
            logger.error(f"Claude API call failed [{feature}]: {e}")
            raise

        finally:
            response_time_ms = int((time.time() - start_time) * 1000)
            try:
                AIRequestLog.objects.create(
                    source_feature=feature,
                    ai_model_name=self.MODEL,
                    call_status=call_status,
                    error_message=error_message,
                    response_time_ms=response_time_ms,
                )
            except Exception as log_error:
                logger.warning(f"Failed to write AIRequestLog: {log_error}")
