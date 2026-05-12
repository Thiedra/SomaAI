"""
simplifier/views.py
API views for note management, AI simplification, and TTS requests.
All endpoints are restricted to the note's owner (student).
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsStudent
from .models import StudentNote, SimplifiedNote, AudioGeneration
from .serializers import NoteSerializer, SimplifiedNoteSerializer, AudioGenerationSerializer
from .tasks import simplify_note_task, generate_tts_task


class NoteListCreateView(APIView):
    """List all notes for the logged-in student, or create a new one."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="List own notes",
        description="Returns all notes belonging to the authenticated student.",
        tags=["Notes"],
        responses={200: NoteSerializer(many=True)},
    )
    def get(self, request):
        notes = StudentNote.objects.filter(student=request.user)
        return Response(NoteSerializer(notes, many=True).data)

    @extend_schema(
        summary="Create a note",
        description="Upload a file or paste text. At least one must be provided.",
        tags=["Notes"],
        request=NoteSerializer,
        responses={
            201: NoteSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = NoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.save(student=request.user)
        return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)


class NoteDetailView(APIView):
    """Retrieve or delete a single note. Only the owner can access it."""
    permission_classes = [IsStudent]

    def get_object(self, note_id, user):
        try:
            return StudentNote.objects.get(id=note_id, student=user)
        except StudentNote.DoesNotExist:
            return None

    @extend_schema(
        summary="Get a note",
        tags=["Notes"],
        responses={
            200: NoteSerializer,
            404: OpenApiResponse(description="Note not found"),
        },
    )
    def get(self, request, note_id):
        note = self.get_object(note_id, request.user)
        if not note:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(NoteSerializer(note).data)

    @extend_schema(
        summary="Delete a note",
        tags=["Notes"],
        responses={
            204: OpenApiResponse(description="Deleted"),
            404: OpenApiResponse(description="Note not found"),
        },
    )
    def delete(self, request, note_id):
        note = self.get_object(note_id, request.user)
        if not note:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SimplifyNoteView(APIView):
    """Trigger async AI simplification for a note."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Simplify a note with AI",
        description="Queues a Celery task to simplify the note. Poll /simplified/ for the result.",
        tags=["Simplifier"],
        responses={
            202: OpenApiResponse(description="Simplification queued"),
            404: OpenApiResponse(description="Note not found"),
        },
    )
    def post(self, request, note_id):
        try:
            note = StudentNote.objects.get(id=note_id, student=request.user)
        except StudentNote.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        simplify_note_task.delay(str(note.id))
        return Response(
            {"detail": "Simplification started. Poll /simplified/ for the result."},
            status=status.HTTP_202_ACCEPTED,
        )


class SimplifiedNoteView(APIView):
    """Get the AI-simplified version of a note."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get simplified note",
        description="Returns the AI simplification result. Returns 404 if not yet ready.",
        tags=["Simplifier"],
        responses={
            200: SimplifiedNoteSerializer,
            404: OpenApiResponse(description="Not simplified yet"),
        },
    )
    def get(self, request, note_id):
        try:
            note = StudentNote.objects.get(id=note_id, student=request.user)
            simplified = note.simplified_version
        except (StudentNote.DoesNotExist, SimplifiedNote.DoesNotExist):
            return Response(
                {"error": "Not found or not yet simplified."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SimplifiedNoteSerializer(simplified).data)


class TTSRequestView(APIView):
    """Request audio generation for a simplified note."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Request TTS audio",
        description="Queues a Celery task to generate audio. Poll /tts/status/ for progress.",
        tags=["Simplifier"],
        responses={
            202: AudioGenerationSerializer,
            404: OpenApiResponse(description="Note not simplified yet"),
        },
    )
    def post(self, request, note_id):
        try:
            note = StudentNote.objects.get(id=note_id, student=request.user)
            simplified = note.simplified_version
        except (StudentNote.DoesNotExist, SimplifiedNote.DoesNotExist):
            return Response(
                {"error": "Simplify the note first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        audio = AudioGeneration.objects.create(
            simplified_note=simplified,
            language=note.language,
        )
        generate_tts_task.delay(str(audio.id))
        return Response(AudioGenerationSerializer(audio).data, status=status.HTTP_202_ACCEPTED)


class TTSStatusView(APIView):
    """Poll the status of an audio generation request."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get TTS status",
        description="Returns the current status of the TTS job: pending, processing, completed, or failed.",
        tags=["Simplifier"],
        responses={
            200: AudioGenerationSerializer,
            404: OpenApiResponse(description="Note not found"),
        },
    )
    def get(self, request, note_id):
        try:
            note = StudentNote.objects.get(id=note_id, student=request.user)
            audio = AudioGeneration.objects.filter(
                simplified_note__original_note=note
            ).latest("created_at")
        except (StudentNote.DoesNotExist, AudioGeneration.DoesNotExist):
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AudioGenerationSerializer(audio).data)
