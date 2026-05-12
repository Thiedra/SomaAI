"""
simplifier/tasks.py
Celery tasks for async AI simplification and TTS audio generation.
These run in the background so the API response is immediate.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def simplify_note_task(self, note_id: str):
    """
    Celery task: simplify a note using Claude AI.
    Retries up to 3 times on failure with exponential backoff.

    Args:
        note_id: UUID string of the Note to simplify.
    """
    from .models import Note, SimplifiedNote
    from simplifier.services.ai.tts_service import TTSService
    from simplifier.services.ai.claude_service import ClaudeService


    try:
        note = Note.objects.select_related("student").get(id=note_id)
        student = note.student

        # get the text to simplify — from pasted text or uploaded file
        original_text = note.original_text
        if not original_text and note.original_file:
            # read text content from uploaded file
            original_text = note.original_file.read().decode("utf-8", errors="ignore")

        # build dyslexia context string for the prompt
        dyslexic_context = (
            "has dyslexia (use very short sentences, avoid complex words)"
            if student.is_dyslexic
            else "does not have dyslexia"
        )
        learning_style = student.learning_style or "general"

        # build the simplification prompt
        prompt = f"""
You are helping a {learning_style} learner who {dyslexic_context}.
Simplify the text below written in {note.language}.
Rules: short sentences (max 20 words), no jargon, active voice.
Return ONLY valid JSON:
{{"simplified_text": "...", "glossary": [{{"term": "...", "definition": "..."}}]}}

Text: {original_text}
"""
        service = ClaudeService()
        result = service.call(prompt, max_tokens=2000, feature="simplifier")

        # save or update the simplified note
        SimplifiedNote.objects.update_or_create(
            note=note,
            defaults={
                "simplified_text": result["simplified_text"],
                "glossary": result.get("glossary", []),
                "reading_level": "simple" if student.is_dyslexic else "intermediate",
                "ai_model_used": ClaudeService.MODEL,
            },
        )
        logger.info(f"Note {note_id} simplified successfully.")

    except Exception as exc:
        logger.error(f"simplify_note_task failed for {note_id}: {exc}")
        # retry with exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def generate_tts_task(self, tts_request_id: str):
    """
    Celery task: generate TTS audio for a simplified note.
    Updates TTSRequest.status throughout the process.

    Args:
        tts_request_id: UUID string of the TTSRequest to process.
    """
    from .models import TTSRequest
    from django.core.files.base import ContentFile

    try:
        tts = TTSRequest.objects.select_related(
            "simplified_note__note"
        ).get(id=tts_request_id)

        # mark as processing so the frontend knows it started
        tts.status = "processing"
        tts.save(update_fields=["status"])

        text = tts.simplified_note.simplified_text

        # --- TTS generation placeholder ---
        # Replace this block with a real TTS provider (e.g. Google TTS, ElevenLabs)
        # For now we save a placeholder text file to confirm the flow works
        audio_content = ContentFile(
            f"TTS audio for: {text[:100]}".encode("utf-8")
        )
        filename = f"tts_{tts_request_id}.txt"
        tts.audio_file.save(filename, audio_content, save=False)

        tts.status = "done"
        tts.save(update_fields=["status", "audio_file"])
        logger.info(f"TTS {tts_request_id} completed.")

    except Exception as exc:
        logger.error(f"generate_tts_task failed for {tts_request_id}: {exc}")
        # mark as failed so the frontend stops polling
        TTSRequest.objects.filter(id=tts_request_id).update(status="failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
