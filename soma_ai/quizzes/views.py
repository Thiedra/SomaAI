"""
quizzes/views.py
API views for quiz generation, retrieval, submission, and results.
Score is always calculated server-side on submission.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsStudent
from simplifier.models import StudentNote
from .models import Quiz, QuizQuestion, QuizSubmission
from .serializers import (
    GenerateQuizSerializer, QuizSerializer, QuizResultSerializer,
    AttemptSubmitSerializer, QuizSubmissionSerializer,
)
from .tasks import generate_quiz_task


class GenerateQuizView(APIView):
    """Generate a new quiz from a simplified note using Claude AI."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Generate a quiz from a note",
        description="Creates a quiz and queues AI question generation. Note must be simplified first.",
        tags=["Quizzes"],
        request=GenerateQuizSerializer,
        responses={
            202: QuizSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Note not found"),
        },
    )
    def post(self, request):
        serializer = GenerateQuizSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note_id = serializer.validated_data["note_id"]
        question_count = serializer.validated_data["question_count"]

        try:
            note = StudentNote.objects.get(id=note_id, student=request.user)
        except StudentNote.DoesNotExist:
            return Response({"error": "Note not found."}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(note, "simplified_version"):
            return Response(
                {"error": "Simplify the note before generating a quiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quiz = Quiz.objects.create(
            source_note=note,
            student=request.user,
            language=note.language,
        )
        generate_quiz_task.delay(str(quiz.id), question_count)
        return Response(QuizSerializer(quiz).data, status=status.HTTP_202_ACCEPTED)


class QuizListView(APIView):
    """List all quizzes belonging to the authenticated student."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="List own quizzes",
        tags=["Quizzes"],
        responses={200: QuizSerializer(many=True)},
    )
    def get(self, request):
        quizzes = Quiz.objects.filter(student=request.user).prefetch_related("questions")
        return Response(QuizSerializer(quizzes, many=True).data)


class QuizDetailView(APIView):
    """Get a single quiz with its questions. Only the owner can access it."""
    permission_classes = [IsStudent]

    def get_object(self, quiz_id, user):
        try:
            return Quiz.objects.prefetch_related("questions").get(id=quiz_id, student=user)
        except Quiz.DoesNotExist:
            return None

    @extend_schema(
        summary="Get quiz with questions",
        description="Returns the quiz and its questions. Correct answers are hidden.",
        tags=["Quizzes"],
        responses={
            200: QuizSerializer,
            404: OpenApiResponse(description="Quiz not found"),
        },
    )
    def get(self, request, quiz_id):
        quiz = self.get_object(quiz_id, request.user)
        if not quiz:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuizSerializer(quiz).data)


class AttemptQuizView(APIView):
    """Submit answers for a quiz. Only one submission allowed per student."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Submit quiz answers",
        description="Submit answers and receive a score. Only one submission allowed.",
        tags=["Quizzes"],
        request=AttemptSubmitSerializer,
        responses={
            201: QuizSubmissionSerializer,
            400: OpenApiResponse(description="Already submitted or validation error"),
            404: OpenApiResponse(description="Quiz not found"),
        },
    )
    def post(self, request, quiz_id):
        try:
            quiz = Quiz.objects.prefetch_related("questions").get(
                id=quiz_id, student=request.user
            )
        except Quiz.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if QuizSubmission.objects.filter(quiz=quiz, student=request.user).exists():
            return Response(
                {"error": "You have already submitted this quiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AttemptSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submitted_answers = serializer.validated_data["answers"]
        duration_seconds = serializer.validated_data["duration_seconds"]

        questions = quiz.questions.all()
        correct_count = sum(
            1 for q in questions
            if submitted_answers.get(str(q.id)) == q.correct_answer
        )
        score = int((correct_count / questions.count()) * 100) if questions.count() > 0 else 0

        submission = QuizSubmission.objects.create(
            quiz=quiz,
            student=request.user,
            submitted_answers=submitted_answers,
            score_percentage=score,
            duration_seconds=duration_seconds,
        )

        return Response(QuizSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class QuizResultsView(APIView):
    """Get full quiz results including correct answers after submission."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get quiz results",
        description="Returns questions with correct answers and the student's score.",
        tags=["Quizzes"],
        responses={
            200: QuizResultSerializer,
            404: OpenApiResponse(description="Quiz not found or not yet submitted"),
        },
    )
    def get(self, request, quiz_id):
        try:
            quiz = Quiz.objects.prefetch_related("questions").get(
                id=quiz_id, student=request.user
            )
            submission = QuizSubmission.objects.get(quiz=quiz, student=request.user)
        except (Quiz.DoesNotExist, QuizSubmission.DoesNotExist):
            return Response(
                {"error": "Quiz not found or not yet submitted."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "quiz": QuizResultSerializer(quiz).data,
            "submission": QuizSubmissionSerializer(submission).data,
        })
