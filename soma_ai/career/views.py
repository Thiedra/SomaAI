"""
career/views.py
API views for career assessment questions, answer submission, and results.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsStudent
from .models import CareerAssessment, CareerRecommendation
from .serializers import (
    CareerQuestionSerializer, CareerAnswerSerializer,
    CareerAssessmentSerializer,
)
from .constants import CAREER_QUESTIONS
from .tasks import generate_career_paths_task


class CareerQuestionsView(APIView):
    """Return the 8 hardcoded career assessment questions."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get career assessment questions",
        description="Returns the 8 questions the student must answer for career matching.",
        tags=["Career"],
        responses={200: CareerQuestionSerializer(many=True)},
    )
    def get(self, request):
        serializer = CareerQuestionSerializer(CAREER_QUESTIONS, many=True)
        return Response(serializer.data)


class CareerProfileView(APIView):
    """Submit answers to get career matches, or retrieve existing matches."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get career assessment and matches",
        description="Returns the student's career assessment with 3 ranked recommendations.",
        tags=["Career"],
        responses={
            200: CareerAssessmentSerializer,
            404: OpenApiResponse(description="No assessment yet — submit answers first"),
        },
    )
    def get(self, request):
        try:
            assessment = CareerAssessment.objects.prefetch_related(
                "recommendations"
            ).get(student=request.user)
        except CareerAssessment.DoesNotExist:
            return Response(
                {"error": "No career assessment yet. Submit your answers first."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CareerAssessmentSerializer(assessment).data)

    @extend_schema(
        summary="Submit career assessment answers",
        description=(
            "Submit answers to all 8 questions. "
            "AI generates 3 ranked career recommendations asynchronously. "
            "Poll GET /career/profile/ for results."
        ),
        tags=["Career"],
        request=CareerAnswerSerializer,
        responses={
            202: CareerAssessmentSerializer,
            400: OpenApiResponse(description="Missing or invalid answers"),
        },
    )
    def post(self, request):
        serializer = CareerAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assessment, _ = CareerAssessment.objects.update_or_create(
            student=request.user,
            defaults={"question_answers": serializer.validated_data["answers"]},
        )

        generate_career_paths_task.delay(str(assessment.id))

        return Response(
            CareerAssessmentSerializer(assessment).data,
            status=status.HTTP_202_ACCEPTED,
        )


class CareerProfileRefreshView(APIView):
    """Re-run AI career matching using existing answers."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Refresh career matches",
        description="Re-runs AI matching using the student's existing answers. Updates the 3 recommendations.",
        tags=["Career"],
        responses={
            202: OpenApiResponse(description="Refresh queued"),
            404: OpenApiResponse(description="No assessment found — submit answers first"),
        },
    )
    def post(self, request):
        try:
            assessment = CareerAssessment.objects.get(student=request.user)
        except CareerAssessment.DoesNotExist:
            return Response(
                {"error": "No career assessment found. Submit answers first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        generate_career_paths_task.delay(str(assessment.id))
        return Response(
            {"detail": "Career refresh started. Poll GET /career/profile/ for results."},
            status=status.HTTP_202_ACCEPTED,
        )
