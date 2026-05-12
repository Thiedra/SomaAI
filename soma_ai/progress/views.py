"""
progress/views.py
API views for student progress tracking and teacher alert management.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.utils import timezone
from datetime import timedelta

from core.permissions import IsStudent, IsTeacher
from .models import StudySession, WeeklyProgressSnapshot, TeacherAlert
from .serializers import (
    ProgressSummarySerializer, ProgressSnapshotSerializer, AlertSerializer,
)


class MyProgressView(APIView):
    """Student — get own overall progress summary including streak."""
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
            sum(s.score_percentage for s in submissions) / submissions.count()
            if submissions.count() > 0 else 0.0
        )

        last_session = sessions.first()
        last_study_date = last_session.session_date if last_session else None

        streak = 0
        check_date = timezone.now().date()
        while StudySession.objects.filter(student=student, session_date=check_date).exists():
            streak += 1
            check_date -= timedelta(days=1)

        data = {
            "total_quizzes": submissions.count(),
            "avg_quiz_score": round(avg_score, 2),
            "total_study_minutes": sum(s.duration_minutes for s in sessions),
            "total_notes": StudentNote.objects.filter(student=student).count(),
            "last_study_date": last_study_date,
            "current_streak_days": streak,
        }
        return Response(ProgressSummarySerializer(data).data)


class MyProgressGraphView(APIView):
    """Student — get last 8 weeks of progress data for graph display."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get progress graph data",
        description="Returns weekly snapshots for the last 8 weeks for chart rendering.",
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
        description="Teacher views progress summary of one of their linked students.",
        tags=["Progress"],
        responses={
            200: ProgressSummarySerializer,
            403: OpenApiResponse(description="Student not linked to this teacher"),
            404: OpenApiResponse(description="Student not found"),
        },
    )
    def get(self, request, student_id):
        from users.models import CustomUser, ClassEnrollment
        from quizzes.models import QuizSubmission
        from simplifier.models import StudentNote

        is_linked = ClassEnrollment.objects.filter(
            teacher=request.user, student__id=student_id
        ).exists()

        if not is_linked:
            return Response(
                {"error": "Student not linked to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            student = CustomUser.objects.get(id=student_id, role="student")
        except CustomUser.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        submissions = QuizSubmission.objects.filter(student=student)
        sessions = StudySession.objects.filter(student=student)
        avg_score = (
            sum(s.score_percentage for s in submissions) / submissions.count()
            if submissions.count() > 0 else 0.0
        )
        last_session = sessions.first()

        streak = 0
        check_date = timezone.now().date()
        while StudySession.objects.filter(student=student, session_date=check_date).exists():
            streak += 1
            check_date -= timedelta(days=1)

        data = {
            "total_quizzes": submissions.count(),
            "avg_quiz_score": round(avg_score, 2),
            "total_study_minutes": sum(s.duration_minutes for s in sessions),
            "total_notes": StudentNote.objects.filter(student=student).count(),
            "last_study_date": last_session.session_date if last_session else None,
            "current_streak_days": streak,
        }
        return Response(ProgressSummarySerializer(data).data)


class AlertListView(APIView):
    """Teacher — list all alerts for their linked students."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List teacher alerts",
        description="Returns all alerts for the teacher's linked students, newest first.",
        tags=["Progress"],
        responses={200: AlertSerializer(many=True)},
    )
    def get(self, request):
        alerts = TeacherAlert.objects.filter(teacher=request.user)
        return Response(AlertSerializer(alerts, many=True).data)


class AlertMarkReadView(APIView):
    """Teacher — mark a specific alert as read."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Mark alert as read",
        description="Marks a single alert as read. Only the alert's teacher can do this.",
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
    """Return a daily motivational message based on student performance."""
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Get daily motivation message",
        description="Returns a motivational message based on the student's average quiz score.",
        tags=["Progress"],
        responses={200: OpenApiResponse(description="Motivational message and stats")},
    )
    def get(self, request):
        from quizzes.models import QuizSubmission
        submissions = QuizSubmission.objects.filter(student=request.user)
        avg = (
            sum(s.score_percentage for s in submissions) / submissions.count()
            if submissions.count() > 0 else 0
        )

        if avg >= 80:
            message = "Outstanding work! You are mastering your subjects. Keep it up!"
        elif avg >= 60:
            message = "Good progress! Every study session brings you closer to your goal."
        elif avg >= 40:
            message = "You are improving! Consistency is the key — keep showing up."
        else:
            message = "Every expert was once a beginner. Today is a great day to start again."

        return Response({
            "message": message,
            "avg_score": round(avg, 1),
            "student_name": request.user.full_name,
        })
