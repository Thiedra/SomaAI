"""
progress/views.py
"""
from django.db.models import Avg, Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.utils import timezone
from datetime import timedelta

from core.permissions import IsStudent, IsTeacher
from users.models import User, ClassEnrollment
from .models import SubjectMastery, StudySession, WeeklyProgressSnapshot, TeacherAlert
from .serializers import (
    SubjectMasterySerializer, WeeklyProgressFrontendSerializer,
    ProgressSummarySerializer, ProgressSnapshotSerializer, AlertSerializer,
)


class MyMasteryView(APIView):
    """
    GET /api/v1/progress/me/mastery/
    Returns per-subject mastery for the authenticated student.
    Frontend shape: [{ studentId, subject, value }, ...]
    """
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get subject mastery",
        description="Returns mastery percentage for each subject: Math, English, Science, Kinyarwanda, Social.",
        tags=["Progress"],
        responses={200: SubjectMasterySerializer(many=True)},
    )
    def get(self, request):
        masteries = SubjectMastery.objects.filter(student=request.user)
        return Response(SubjectMasterySerializer(masteries, many=True).data)


class MyProgressFrontendView(APIView):
    """
    GET /api/v1/progress/me/weekly/
    Returns last 6 weekly snapshots in the exact frontend shape:
    [{ studentId, week: "W1", math, english, science }, ...]
    """
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get weekly progress data",
        description="Returns last 6 weeks of per-subject progress for the frontend chart.",
        tags=["Progress"],
        responses={200: WeeklyProgressFrontendSerializer(many=True)},
    )
    def get(self, request):
        snapshots = list(
            WeeklyProgressSnapshot.objects.filter(
                student=request.user
            ).order_by("week_start_date")[:6]
        )
        data = []
        for i, snapshot in enumerate(snapshots):
            serializer = WeeklyProgressFrontendSerializer(
                snapshot, context={"index": i}
            )
            data.append(serializer.data)
        return Response(data)


class MyProgressView(APIView):
    """GET /api/v1/progress/me/ — overall summary."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get own progress summary",
        description="Returns total quizzes, average score, study minutes, streak, and last activity.",
        tags=["Progress"],
        responses={200: ProgressSummarySerializer},
    )
    def get(self, request):
        from quizzes.models import QuizSubmission
        from simplifier.models import StudentNote

        student = request.user
        submissions = QuizSubmission.objects.filter(student=student)
        sessions = StudySession.objects.filter(student=student)

        avg_score = (
            submissions.aggregate(avg=Avg("score_percentage"))["avg"] or 0.0
        )
        total_minutes = sessions.aggregate(total=Sum("duration_minutes"))["total"] or 0
        last_session = sessions.first()

        data = {
            "total_quizzes": submissions.count(),
            "avg_quiz_score": round(avg_score, 2),
            "total_study_minutes": total_minutes,
            "total_notes": StudentNote.objects.filter(student=student).count(),
            "last_study_date": last_session.session_date if last_session else None,
            "current_streak_days": student.streak,
        }
        return Response(ProgressSummarySerializer(data).data)


class MyProgressGraphView(APIView):
    """GET /api/v1/progress/me/graph/ — full snapshots for internal use."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get progress graph data (full snapshots)",
        tags=["Progress"],
        responses={200: ProgressSnapshotSerializer(many=True)},
    )
    def get(self, request):
        snapshots = WeeklyProgressSnapshot.objects.filter(
            student=request.user
        ).order_by("week_start_date")[:8]
        return Response(ProgressSnapshotSerializer(snapshots, many=True).data)


class StudentProgressView(APIView):
    """Teacher — view a specific linked student's progress summary."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="View a student's progress",
        tags=["Progress"],
        responses={
            200: ProgressSummarySerializer,
            403: OpenApiResponse(description="Student not linked to this teacher"),
            404: OpenApiResponse(description="Student not found"),
        },
    )
    def get(self, request, student_id):
        from quizzes.models import QuizSubmission
        from simplifier.models import StudentNote

        if not ClassEnrollment.objects.filter(
            teacher=request.user, student__id=student_id
        ).exists():
            return Response(
                {"error": "Student not linked to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            student = User.objects.get(id=student_id, role="student")
        except User.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        submissions = QuizSubmission.objects.filter(student=student)
        sessions = StudySession.objects.filter(student=student)

        avg_score = submissions.aggregate(avg=Avg("score_percentage"))["avg"] or 0.0
        total_minutes = sessions.aggregate(total=Sum("duration_minutes"))["total"] or 0
        last_session = sessions.first()

        data = {
            "total_quizzes": submissions.count(),
            "avg_quiz_score": round(avg_score, 2),
            "total_study_minutes": total_minutes,
            "total_notes": StudentNote.objects.filter(student=student).count(),
            "last_study_date": last_session.session_date if last_session else None,
            "current_streak_days": student.streak,
        }
        return Response(ProgressSummarySerializer(data).data)


class AlertListView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List teacher alerts",
        tags=["Progress"],
        responses={200: AlertSerializer(many=True)},
    )
    def get(self, request):
        alerts = TeacherAlert.objects.filter(teacher=request.user)
        return Response(AlertSerializer(alerts, many=True).data)


class AlertMarkReadView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Mark alert as read",
        tags=["Progress"],
        responses={
            200: AlertSerializer,
            404: OpenApiResponse(description="Alert not found"),
        },
    )
    def patch(self, request, alert_id):
        try:
            alert = TeacherAlert.objects.get(id=alert_id, teacher=request.user)
        except TeacherAlert.DoesNotExist:
            return Response({"error": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response(AlertSerializer(alert).data)


class MotivationView(APIView):
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get daily motivation message",
        tags=["Progress"],
        responses={200: OpenApiResponse(description="Motivational message")},
    )
    def get(self, request):
        avg = request.user.xp / max(request.user.level, 1)
        if request.user.streak >= 7:
            message = "Outstanding! A 7-day streak — you are unstoppable!"
        elif request.user.xp >= 1000:
            message = "Outstanding work! You are mastering your subjects. Keep it up!"
        elif request.user.streak >= 3:
            message = "Good progress! Every study session brings you closer to your goal."
        else:
            message = "Every expert was once a beginner. Today is a great day to start again."

        return Response({
            "message": message,
            "streak": request.user.streak,
            "xp": request.user.xp,
            "level": request.user.level,
            "student_name": request.user.full_name,
        })
