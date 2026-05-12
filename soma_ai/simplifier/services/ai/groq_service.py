"""
simplifier/services/ai/groq_service.py
Groq AI service — free, ultra-fast inference.
Drop-in replacement for ClaudeService.
Import path: from simplifier.services.ai.groq_service import GroqService
"""
import time
import logging
from django.conf import settings
from .base import BaseAIService

logger = logging.getLogger(__name__)


class GroqService(BaseAIService):
    """
    Wraps the Groq API using llama-3.3-70b model.
    Free tier: 14,400 requests/day, 6,000 tokens/minute.
    Every call is logged to AIRequestLog — success or failure.
    """

    MODEL = "llama-3.3-70b-versatile"

    def call(self, prompt: str, max_tokens: int = 1000, feature: str = "unknown") -> dict:
        """
        Send a prompt to Groq and return a parsed JSON dict.

        Args:
            prompt: Full prompt string to send.
            max_tokens: Maximum tokens in the response.
            feature: Calling feature name for logging (simplifier, quizzes, planner, career).

        Returns:
            Parsed dict from Groq's JSON response.

        Raises:
            ValueError: If GROQ_API_KEY is missing or Groq returns invalid JSON.
        """
        from groq import Groq
        from core.models import AIRequestLog

        start_time = time.time()
        call_status = "success"
        error_message = ""

        try:
            if not settings.GROQ_API_KEY:
                raise ValueError(
                    "GROQ_API_KEY is not set in your .env file. "
                    "Get your free key from https://console.groq.com/"
                )

            client = Groq(api_key=settings.GROQ_API_KEY)

            response = client.chat.completions.create(
                model=self.MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = response.choices[0].message.content
            logger.debug(f"Groq raw response [{feature}]: {raw_text[:300]}")

            return self.parse_json_response(raw_text)

        except Exception as e:
            call_status = "failed"
            error_message = str(e)
            logger.error(f"Groq API call failed [{feature}]: {e}")
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
