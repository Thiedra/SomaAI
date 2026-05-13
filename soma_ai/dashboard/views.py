"""
dashboard/views.py
Teacher dashboard API views.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg, Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsTeacher
from users.models import User, ClassEnrollment
from users.serializers import TeacherProfileSerializer
from progress.models import TeacherAlert, SubjectMastery, WeeklyProgressSnapshot, StudySession
from .serializers import (
    DashboardOverviewSerializer, StudentOverviewSerializer,
    ClassStudentSerializer, TeacherReportSerializer,
)


def _time_ago(date) -> str:
    """Convert a date to a human-readable 'X ago' string like the frontend expects."""
    if not date:
        return "never"
    now = timezone.now().date()
    diff = (now - date).days
    if diff == 0:
        return "today"
    if diff == 1:
        return "1d ago"
    return f"{diff}d ago"


def _calc_risk(mastery: float, last_active_date) -> str:
    """
    Frontend risk logic:
      high   = mastery < 50  OR  inactive > 2 days
      medium = mastery 50–65 OR  inactive > 1 day
      low    = mastery > 65  AND active recently
    """
    today = timezone.now().date()
    inactive_days = (today - last_active_date).days if last_active_date else 999

    if mastery < 50 or inactive_days > 2:
        return "high"
    if mastery <= 65 or inactive_days > 1:
        return "medium"
    return "low"


def _get_student_stats(student, today):
    """
    Compute all stats for one student.
    Uses .aggregate() to avoid loading all rows into memory.
    """
    seven_days_ago = today - timedelta(days=7)
    three_days_ago = today - timedelta(days=3)

    from quizzes.models import QuizSubmission

    avg_score_7d = QuizSubmission.objects.filter(
        student=student,
        submitted_at__date__gte=seven_days_ago,
    ).aggregate(avg=Avg("score_percentage"))["avg"]

    total_minutes = StudySession.objects.filter(
        student=student
    ).aggregate(total=Sum("duration_minutes"))["total"] or 0

    last_session = StudySession.objects.filter(
        student=student
    ).order_by("-session_date").first()
    last_study_date = last_session.session_date if last_session else None

    all_submissions = QuizSubmission.objects.filter(student=student)

    struggling_reasons = []

    if avg_score_7d is not None and avg_score_7d < 50:
        struggling_reasons.append(
            f"Average quiz score last 7 days: {round(avg_score_7d, 1)}%"
        )

    has_recent = StudySession.objects.filter(
        student=student, session_date__gte=three_days_ago
    ).exists()
    if not has_recent:
        struggling_reasons.append("No study activity in the last 3 days")

    last_3 = list(
        QuizSubmission.objects.filter(
            student=student
        ).order_by("-submitted_at")[:3]
    )
    if len(last_3) == 3 and all(s.score_percentage < 50 for s in last_3):
        struggling_reasons.append("3 consecutive failed quizzes")

    return {
        "id": student.id,
        "full_name": student.full_name,
        "email": student.email,
        "avg_score_last_7_days": round(avg_score_7d, 1) if avg_score_7d is not None else 0.0,
        "total_study_minutes": total_minutes,
        "last_study_date": last_study_date,
        "quizzes_completed": all_submissions.count(),
        "is_struggling": len(struggling_reasons) > 0,
        "struggling_reasons": struggling_reasons,
    }


def _get_class_student(student) -> dict:
    """
    Build the ClassStudent object the frontend expects:
    { id, name, grade, mastery, dyslexia, lastActive, risk }
    """
    # overall mastery = average of all subject masteries
    mastery_avg = SubjectMastery.objects.filter(
        student=student
    ).aggregate(avg=Avg("value"))["avg"] or 0.0

    last_session = StudySession.objects.filter(
        student=student
    ).order_by("-session_date").first()
    last_active_date = last_session.session_date if last_session else None

    return {
        "id": student.id,
        "name": student.full_name,
        "grade": student.grade,
        "mastery": round(mastery_avg, 1),
        "dyslexia": student.is_dyslexic,
        "lastActive": _time_ago(last_active_date),
        "risk": _calc_risk(mastery_avg, last_active_date),
    }


class TeacherMeView(APIView):
    """
    GET /api/v1/teacher/me/
    Returns the authenticated teacher's profile.
    Shape: { id, soma_id, name, school, role, classGrade, classSize }
    """
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get teacher profile",
        description="Returns the authenticated teacher's profile including class grade and size.",
        tags=["Teacher"],
        responses={200: TeacherProfileSerializer},
    )
    def get(self, request):
        return Response(TeacherProfileSerializer(request.user).data)


class TeacherStudentsView(APIView):
    """
    GET /api/v1/teacher/students/
    Returns all enrolled students with mastery, lastActive, risk.
    Matches frontend ClassStudent shape exactly.
    """
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List class students",
        description=(
            "Returns all enrolled students with mastery %, last active time, "
            "risk level (low/medium/high), and dyslexia flag."
        ),
        tags=["Teacher"],
        responses={200: ClassStudentSerializer(many=True)},
    )
    def get(self, request):
        students = User.objects.filter(
            enrolled_teachers__teacher=request.user,
            role="student",
        )
        data = [_get_class_student(s) for s in students]
        return Response(ClassStudentSerializer(data, many=True).data)


class TeacherStudentDetailView(APIView):
    """
    GET /api/v1/teacher/students/<id>/
    Returns a single enrolled student's ClassStudent object.
    """
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get single class student",
        description="Returns mastery, risk, lastActive for one enrolled student.",
        tags=["Teacher"],
        responses={
            200: ClassStudentSerializer,
            403: OpenApiResponse(description="Student not enrolled in your class"),
            404: OpenApiResponse(description="Student not found"),
        },
    )
    def get(self, request, student_id):
        if not ClassEnrollment.objects.filter(
            teacher=request.user, student__id=student_id
        ).exists():
            return Response(
                {"error": "This student is not enrolled in your class."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            student = User.objects.get(id=student_id, role="student")
        except User.DoesNotExist:
            return Response(
                {"error": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ClassStudentSerializer(_get_class_student(student)).data)


class TeacherReportsView(APIView):
    """
    GET /api/v1/teacher/reports/
    Returns mastery and weekly progress data for ALL enrolled students.
    Matches frontend: { mastery: Mastery[], progress: ProgressData[] }
    """
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get class reports",
        description=(
            "Returns per-subject mastery and weekly progress for all enrolled students. "
            "Used to power the teacher's reports/charts page."
        ),
        tags=["Teacher"],
        responses={200: TeacherReportSerializer},
    )
    def get(self, request):
        students = User.objects.filter(
            enrolled_teachers__teacher=request.user,
            role="student",
        )

        mastery_data = []
        progress_data = []

        for student in students:
            # mastery per subject
            for m in SubjectMastery.objects.filter(student=student):
                mastery_data.append({
                    "studentId": str(student.id),
                    "subject": m.subject,
                    "value": m.value,
                })

            # last 6 weekly snapshots
            snapshots = list(
                WeeklyProgressSnapshot.objects.filter(
                    student=student
                ).order_by("week_start_date")[:6]
            )
            for i, snap in enumerate(snapshots):
                progress_data.append({
                    "studentId": str(student.id),
                    "week": f"W{i + 1}",
                    "math": snap.math_score,
                    "english": snap.english_score,
                    "science": snap.science_score,
                })

        return Response(TeacherReportSerializer({
            "mastery": mastery_data,
            "progress": progress_data,
        }).data)


class DashboardOverviewView(APIView):
    """GET /api/v1/dashboard/overview/ — aggregated class stats."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get dashboard overview",
        description=(
            "Returns aggregated stats: class average score, struggling count, "
            "unread alerts, most/least active student."
        ),
        tags=["Dashboard"],
        responses={200: DashboardOverviewSerializer},
    )
    def get(self, request):
        today = timezone.now().date()
        students = User.objects.filter(
            enrolled_teachers__teacher=request.user, role="student"
        )

        if not students.exists():
            return Response(DashboardOverviewSerializer({
                "total_students": 0,
                "struggling_students_count": 0,
                "avg_class_score": 0.0,
                "total_alerts_unread": 0,
                "most_active_student": None,
                "least_active_student": None,
            }).data)

        all_stats = [_get_student_stats(s, today) for s in students]

        scores = [
            s["avg_score_last_7_days"]
            for s in all_stats if s["quizzes_completed"] > 0
        ]
        avg_class_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        struggling_count = sum(1 for s in all_stats if s["is_struggling"])

        unread_alerts = TeacherAlert.objects.filter(
            teacher=request.user, is_read=False
        ).count()

        sorted_by_activity = sorted(
            all_stats, key=lambda s: s["total_study_minutes"], reverse=True
        )
        most_active = sorted_by_activity[0]["full_name"] if sorted_by_activity else None
        least_active = (
            sorted_by_activity[-1]["full_name"]
            if len(sorted_by_activity) > 1 else None
        )

        return Response(DashboardOverviewSerializer({
            "total_students": students.count(),
            "struggling_students_count": struggling_count,
            "avg_class_score": avg_class_score,
            "total_alerts_unread": unread_alerts,
            "most_active_student": most_active,
            "least_active_student": least_active,
        }).data)


class DashboardStudentListView(APIView):
    """GET /api/v1/dashboard/students/ — all students with internal stats."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List all students with stats",
        description="Sort with ?sort=score, ?sort=activity, or ?sort=name.",
        tags=["Dashboard"],
        responses={200: StudentOverviewSerializer(many=True)},
    )
    def get(self, request):
        today = timezone.now().date()
        sort_by = request.query_params.get("sort", "name")
        students = User.objects.filter(
            enrolled_teachers__teacher=request.user, role="student"
        )
        all_stats = [_get_student_stats(s, today) for s in students]

        if sort_by == "score":
            all_stats.sort(key=lambda s: s["avg_score_last_7_days"], reverse=True)
        elif sort_by == "activity":
            all_stats.sort(key=lambda s: s["total_study_minutes"], reverse=True)
        else:
            all_stats.sort(key=lambda s: s["full_name"])

        return Response(StudentOverviewSerializer(all_stats, many=True).data)


class DashboardStudentDetailView(APIView):
    """GET /api/v1/dashboard/students/<id>/full/ — full stats for one student."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get full student details",
        tags=["Dashboard"],
        responses={
            200: StudentOverviewSerializer,
            403: OpenApiResponse(description="Student not linked to this teacher"),
            404: OpenApiResponse(description="Student not found"),
        },
    )
    def get(self, request, student_id):
        if not ClassEnrollment.objects.filter(
            teacher=request.user, student__id=student_id
        ).exists():
            return Response(
                {"error": "This student is not linked to you."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            student = User.objects.get(id=student_id, role="student")
        except User.DoesNotExist:
            return Response(
                {"error": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            StudentOverviewSerializer(_get_student_stats(student, timezone.now().date())).data
        )


class DashboardStrugglingView(APIView):
    """GET /api/v1/dashboard/struggling/ — only struggling students."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get struggling students",
        tags=["Dashboard"],
        responses={200: StudentOverviewSerializer(many=True)},
    )
    def get(self, request):
        today = timezone.now().date()
        students = User.objects.filter(
            enrolled_teachers__teacher=request.user, role="student"
        )
        struggling = [
            stats for s in students
            if (stats := _get_student_stats(s, today))["is_struggling"]
        ]
        struggling.sort(key=lambda s: len(s["struggling_reasons"]), reverse=True)
        return Response(StudentOverviewSerializer(struggling, many=True).data)
