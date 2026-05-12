"""
simplifier/services/ai/tts_service.py
Text-to-speech service using OpenAI TTS API.
Converts simplified note text into MP3 audio files.
Import path: from simplifier.services.ai.tts_service import TTSService
"""
import logging
import time
from django.conf import settings
from .base import BaseAIService

logger = logging.getLogger(__name__)

# map Soma AI language codes to OpenAI TTS voices
LANGUAGE_VOICE_MAP = {
    "english": "nova",
    "kinyarwanda": "nova",
    "french": "nova",
    "swahili": "nova",
}


class TTSService:
    """
    Wraps the OpenAI Text-to-Speech API.
    Generates MP3 audio from simplified note text.
    """

    MODEL = "tts-1"
    MODEL_HD = "tts-1-hd"

    def generate_audio(
        self,
        text: str,
        language: str = "english",
        use_hd: bool = False,
    ) -> bytes:
        """
        Convert text to speech and return raw MP3 bytes.

        Args:
            text: The simplified note text to convert.
            language: Language code for voice selection.
            use_hd: Use high-definition model (slower, better quality).

        Returns:
            Raw MP3 audio as bytes.
        """
        import openai
        from core.models import AIRequestLog

        start_time = time.time()
        call_status = "success"
        error_message = ""

        try:
            if not settings.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY is not set in your .env file. "
                    "Get your key from https://platform.openai.com/api-keys"
                )

            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            voice = LANGUAGE_VOICE_MAP.get(language, "nova")
            model = self.MODEL_HD if use_hd else self.MODEL

            # OpenAI TTS supports up to 4096 characters
            text_to_speak = text[:4000] if len(text) > 4000 else text

            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text_to_speak,
                response_format="mp3",
            )

            audio_bytes = response.content
            logger.info(
                f"TTS generated {len(audio_bytes)} bytes "
                f"for language={language}, voice={voice}"
            )
            return audio_bytes

        except Exception as e:
            call_status = "failed"
            error_message = str(e)
            logger.error(f"TTS generation failed: {e}")
            raise

        finally:
            response_time_ms = int((time.time() - start_time) * 1000)
            try:
                AIRequestLog.objects.create(
                    source_feature="tts",
                    ai_model_name=self.MODEL,
                    call_status=call_status,
                    error_message=error_message,
                    response_time_ms=response_time_ms,
                )
            except Exception as log_error:
                logger.warning(f"Failed to write AIRequestLog: {log_error}")
