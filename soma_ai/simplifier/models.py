"""
simplifier/models.py
Models for student notes, AI simplification results, and audio generation.
"""
import uuid
from django.db import models
from django.conf import settings


class StudentNote(models.Model):
    """
    A note created by a student — either typed text or an uploaded file.
    At least one of text_content or uploaded_file must be provided.
    The note is the source material for AI simplification and quiz generation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name="Student",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Note Title",
    )
    text_content = models.TextField(
        null=True, blank=True,
        verbose_name="Pasted Text",
        help_text="Text pasted directly by the student",
    )
    uploaded_file = models.FileField(
        upload_to="notes/uploads/",
        null=True, blank=True,
        verbose_name="Uploaded File",
        help_text="Document uploaded by the student (PDF, DOCX, TXT)",
    )
    language = models.CharField(
        max_length=20,
        default="english",
        verbose_name="Note Language",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Student Note"
        verbose_name_plural = "Student Notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.student.full_name}"


class SimplifiedNote(models.Model):
    """
    AI-generated simplified version of a StudentNote.
    One-to-one with StudentNote — each note has at most one simplification.
    Includes a glossary of key terms to help students understand difficult words.
    """

    class ReadingLevel(models.TextChoices):
        SIMPLE = "simple", "Simple"               # very short sentences, basic words
        INTERMEDIATE = "intermediate", "Intermediate"  # slightly more complex

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_note = models.OneToOneField(
        StudentNote,
        on_delete=models.CASCADE,
        related_name="simplified_version",
        verbose_name="Original Note",
    )
    simplified_text = models.TextField(
        verbose_name="Simplified Text",
    )
    # format: [{"term": "photosynthesis", "definition": "how plants make food"}]
    glossary = models.JSONField(
        default=list,
        verbose_name="Key Terms Glossary",
        help_text="List of difficult terms with simple definitions",
    )
    reading_level = models.CharField(
        max_length=20,
        choices=ReadingLevel.choices,
        default=ReadingLevel.SIMPLE,
        verbose_name="Reading Level",
    )
    ai_model_used = models.CharField(
        max_length=100,
        verbose_name="AI Model",
        help_text="The AI model that generated this simplification",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Simplified Note"
        verbose_name_plural = "Simplified Notes"

    def __str__(self):
        return f"Simplified: {self.original_note.title}"


class AudioGeneration(models.Model):
    """
    Tracks a text-to-speech audio generation request for a simplified note.
    Processed asynchronously via Celery.
    The frontend polls the status field until it becomes 'completed' or 'failed'.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"          # queued, not yet started
        PROCESSING = "processing", "Processing" # Celery task is running
        COMPLETED = "completed", "Completed"    # audio file is ready
        FAILED = "failed", "Failed"             # generation failed

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    simplified_note = models.ForeignKey(
        SimplifiedNote,
        on_delete=models.CASCADE,
        related_name="audio_generations",
        verbose_name="Simplified Note",
    )
    audio_file = models.FileField(
        upload_to="notes/audio/",
        null=True, blank=True,
        verbose_name="Audio File",
        help_text="Generated MP3 file — available when status is completed",
    )
    language = models.CharField(
        max_length=20,
        default="english",
        verbose_name="Audio Language",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Generation Status",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audio Generation"
        verbose_name_plural = "Audio Generations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Audio [{self.status}] — {self.simplified_note.original_note.title}"
