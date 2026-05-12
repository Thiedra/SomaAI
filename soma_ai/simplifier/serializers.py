"""
simplifier/serializers.py
Serializers for note creation, simplified note output, and TTS status.
"""
from rest_framework import serializers
from .models import StudentNote, SimplifiedNote, AudioGeneration


class NoteSerializer(serializers.ModelSerializer):
    """
    Used for creating and listing notes.
    Student is set automatically from the request — not from the client.
    At least one of text_content or uploaded_file must be provided.
    """
    class Meta:
        model = StudentNote
        fields = ["id", "title", "text_content", "uploaded_file", "language", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        """Ensure the note has either text or a file — not neither."""
        if not data.get("text_content") and not data.get("uploaded_file"):
            raise serializers.ValidationError(
                "Provide either text_content or uploaded_file."
            )
        return data


class SimplifiedNoteSerializer(serializers.ModelSerializer):
    """Read-only serializer for returning AI simplification results."""
    class Meta:
        model = SimplifiedNote
        fields = ["id", "simplified_text", "glossary", "reading_level", "ai_model_used", "created_at"]
        read_only_fields = fields


class AudioGenerationSerializer(serializers.ModelSerializer):
    """Returns the current status of an audio generation request and the audio URL if ready."""
    class Meta:
        model = AudioGeneration
        fields = ["id", "status", "audio_file", "language", "created_at"]
        read_only_fields = fields
