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
    Celery task: simplify a note using Cohere AI.
    Retries up to 3 times on failure with exponential backoff.

    Args:
        note_id: UUID string of the StudentNote to simplify.
    """
    from .models import StudentNote, SimplifiedNote
    from services.ai.cohere_service import CohereService

    try:
        note = StudentNote.objects.select_related("student").get(id=note_id)
        student = note.student

        original_text = note.text_content
        if not original_text and note.uploaded_file:
            original_text = note.uploaded_file.read().decode("utf-8", errors="ignore")

        dyslexic_context = (
            "has dyslexia (use very short sentences, avoid complex words)"
            if student.is_dyslexic
            else "does not have dyslexia"
        )
        learning_style = student.learning_style or "general"

        prompt = f"""
You are helping a {learning_style} learner who {dyslexic_context}.
Simplify the text below written in {note.language}.
Rules: short sentences (max 20 words), no jargon, active voice.
Return ONLY valid JSON:
{{"simplified_text": "...", "glossary": [{{"term": "...", "definition": "..."}}]}}

Text: {original_text}
"""
        service = CohereService()
        result = service.call(prompt, max_tokens=2000, feature="simplifier")

        SimplifiedNote.objects.update_or_create(
            original_note=note,
            defaults={
                "simplified_text": result["simplified_text"],
                "glossary": result.get("glossary", []),
                "reading_level": "simple" if student.is_dyslexic else "intermediate",
                "ai_model_used": CohereService.MODEL,
            },
        )
        logger.info(f"Note {note_id} simplified successfully.")

    except Exception as exc:
        logger.error(f"simplify_note_task failed for {note_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def generate_tts_task(self, audio_id: str):
    """
    Celery task: generate TTS audio for a simplified note.
    Updates AudioGeneration.status throughout the process.

    Args:
        audio_id: UUID string of the AudioGeneration to process.
    """
    from .models import AudioGeneration
    from django.core.files.base import ContentFile

    try:
        audio = AudioGeneration.objects.select_related(
            "simplified_note__original_note"
        ).get(id=audio_id)

        audio.status = "processing"
        audio.save(update_fields=["status"])

        text = audio.simplified_note.simplified_text

        # --- TTS generation placeholder ---
        # Replace with a real TTS provider (e.g. Google TTS, ElevenLabs)
        audio_content = ContentFile(
            f"TTS audio for: {text[:100]}".encode("utf-8")
        )
        filename = f"tts_{audio_id}.txt"
        audio.audio_file.save(filename, audio_content, save=False)

        audio.status = "completed"
        audio.save(update_fields=["status", "audio_file"])
        logger.info(f"TTS {audio_id} completed.")

    except Exception as exc:
        logger.error(f"generate_tts_task failed for {audio_id}: {exc}")
        AudioGeneration.objects.filter(id=audio_id).update(status="failed")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
