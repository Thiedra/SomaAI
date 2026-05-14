"""
services/ai/cohere_service.py
Cohere AI service using Command-R Plus.
Supports JSON responses, plain text responses, and SSE streaming.

Three methods:
  call()       — returns parsed JSON dict. Used by quizzes, simplifier, career.
  call_text()  — returns plain text. Used by ai_proxy endpoints.
  stream()     — yields tokens one by one. Used by AI tutor SSE endpoint.

Import path: from services.ai.cohere_service import CohereService
"""
import time
import logging
from django.conf import settings
from .base import BaseAIService

logger = logging.getLogger(__name__)


def _extract_text(response) -> str:
    """
    Extract text from a Cohere response object.
    Handles both Cohere v4 (response.text) and v5 (response.message.content[0].text).
    """
    # Cohere v4
    if hasattr(response, "text"):
        return response.text
    # Cohere v5
    if hasattr(response, "message"):
        content = response.message.content
        if isinstance(content, list) and content:
            return content[0].text
        return str(content)
    raise ValueError("Cannot extract text from Cohere response — unknown format.")


class CohereService(BaseAIService):
    """
    Wraps the Cohere API using Command-R Plus.
    Every call is logged to AIRequestLog — success or failure.
    """

    MODEL = "command-r-plus"

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_client(self):
        """Return an authenticated Cohere client. Raises if key is missing."""
        from cohere import Client
        if not settings.COHERE_API_KEY:
            raise ValueError(
                "COHERE_API_KEY is not set. Get your key at https://dashboard.cohere.com/"
            )
        return Client(api_key=settings.COHERE_API_KEY)

    def _log(self, feature: str, call_status: str, error: str, ms: int):
        """Write an AIRequestLog entry. Never raises."""
        try:
            from core.models import AIRequestLog
            AIRequestLog.objects.create(
                source_feature=feature,
                ai_model_name=self.MODEL,
                call_status=call_status,
                error_message=error,
                response_time_ms=ms,
            )
        except Exception as e:
            logger.warning(f"Failed to write AIRequestLog: {e}")

    # ── Public methods ────────────────────────────────────────────────────────

    def call(self, prompt: str, max_tokens: int = 1000, feature: str = "unknown") -> dict:
        """
        Send a prompt and return a parsed JSON dict.
        Uses JSON mode — only use this when you need structured data.
        Used by: quizzes, simplifier tasks, career assessment, planner.
        """
        start = time.time()
        call_status = "success"
        error_message = ""

        try:
            client = self._get_client()
            response = client.chat(
                model=self.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an educational AI assistant. "
                            "Always respond with valid JSON only. "
                            "Never include markdown or extra text."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            raw = _extract_text(response)
            logger.debug(f"Cohere JSON [{feature}]: {raw[:300]}")
            return self.parse_json_response(raw)

        except Exception as e:
            call_status = "failed"
            error_message = str(e)
            logger.error(f"Cohere call() failed [{feature}]: {e}")
            raise

        finally:
            self._log(feature, call_status, error_message, int((time.time() - start) * 1000))

    def call_text(
        self,
        prompt: str,
        system_prompt: str = "",
        messages: list = None,
        max_tokens: int = 800,
        feature: str = "unknown",
    ) -> str:
        """
        Send a prompt and return plain text (not JSON).
        Supports full chat history via the `messages` parameter.

        Args:
            prompt:        Current user message. Appended after messages if provided.
            system_prompt: Optional system instruction for the AI.
            messages:      Chat history as [{"role": "user"|"assistant", "content": "..."}].
                           If provided, prompt is appended as the final user message.
            max_tokens:    Max response tokens.
            feature:       Feature name for AIRequestLog.

        Used by: ai_proxy simplify, quiz start/answer, career advice.
        """
        start = time.time()
        call_status = "success"
        error_message = ""

        try:
            client = self._get_client()

            # build message list — never mutate the caller's list
            built = []
            if messages:
                built.extend(messages)
            else:
                if system_prompt:
                    built.append({"role": "system", "content": system_prompt})
                built.append({"role": "user", "content": prompt})

            response = client.chat(
                model=self.MODEL,
                messages=built,
                max_tokens=max_tokens,
                temperature=0.7,
            )

            text = _extract_text(response).strip()
            logger.debug(f"Cohere text [{feature}]: {text[:300]}")
            return text

        except Exception as e:
            call_status = "failed"
            error_message = str(e)
            logger.error(f"Cohere call_text() failed [{feature}]: {e}")
            raise

        finally:
            self._log(feature, call_status, error_message, int((time.time() - start) * 1000))

    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        chat_history: list = None,
    ):
        """
        Stream tokens from Cohere one by one.

        Accepts chat_history in Cohere format (what the frontend sends):
            [{ role: "USER"|"CHATBOT", message: "..." }]
        Converts to the standard messages format internally.

        Args:
            prompt:       Current user message.
            system_prompt: System instruction for the AI.
            chat_history: Previous messages in Cohere frontend format.

        Yields:
            str — one text token at a time.

        Used by: AITutorView (SSE streaming endpoint).
        """
        client = self._get_client()

        # build message list — never mutate the caller's list
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # convert Cohere frontend format → standard messages format
        # Frontend sends: { role: "USER"|"CHATBOT", message: "..." }
        # API expects:    { role: "user"|"assistant", content: "..." }
        for entry in (chat_history or []):
            cohere_role = entry.get("role", "USER")
            role = "user" if cohere_role == "USER" else "assistant"
            messages.append({
                "role": role,
                "content": entry.get("message", ""),
            })

        # append current user message
        messages.append({"role": "user", "content": prompt})

        response = client.chat(
            model=self.MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
            stream=True,
        )

        for event in response:
            # handle both Cohere v4 and v5 streaming event formats
            event_type = getattr(event, "event_type", None)
            if event_type == "text-generation":
                # Cohere v4 streaming format
                token = getattr(event, "text", "")
                if token:
                    yield token
            elif hasattr(event, "delta"):
                # Cohere v5 streaming format
                delta = event.delta
                if delta and hasattr(delta, "message"):
                    content = delta.message.content
                    if isinstance(content, list) and content:
                        token = content[0].text
                        if token:
                            yield token
