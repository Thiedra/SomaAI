"""
dashboard/views.py
Teacher dashboard API views.
"""
from datetime import timedelta
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsTeacher
from .serializers import DashboardOverviewSerializer, StudentOverviewSerializer


def get_student_stats(student, today):
    from quizzes.models import QuizSubmission
    from simplifier.models import StudentNote
    from progress.models import StudySession

    seven_days_ago = today - timedelta(days=7)
    three_days_ago = today - timedelta(days=3)

    recent_submissions = QuizSubmission.objects.filter(
        student=student,
        submitted_at__date__gte=seven_days_ago,
    )
    avg_score_7d = (
        sum(s.score_percentage for s in recent_submissions) / recent_submissions.count()
        if recent_submissions.count() > 0 else None
    )

    sessions = StudySession.objects.filter(student=student)
    total_minutes = sum(s.duration_minutes for s in sessions)
    last_session = sessions.order_by("-session_date").first()
    last_study_date = last_session.session_date if last_session else None

    all_submissions = QuizSubmission.objects.filter(student=student)

    struggling_reasons = []

    if avg_score_7d is not None and avg_score_7d < 50:
        struggling_reasons.append(
            f"Average quiz score last 7 days: {round(avg_score_7d, 1)}%"
        )

    has_recent_session = StudySession.objects.filter(
        student=student, session_date__gte=three_days_ago
    ).exists()
    if not has_recent_session:
        struggling_reasons.append("No study activity in the last 3 days")

    last_3_submissions = list(
        QuizSubmission.objects.filter(student=student).order_by("-submitted_at")[:3]
    )
    if len(last_3_submissions) == 3 and all(s.score_percentage < 50 for s in last_3_submissions):
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


class DashboardOverviewView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get dashboard overview",
        description=(
            "Returns aggregated stats for all the teacher's linked students: "
            "class average score, struggling count, unread alerts, most/least active student."
        ),
        tags=["Dashboard"],
        responses={200: DashboardOverviewSerializer},
    )
    def get(self, request):
        from users.models import CustomUser
        from progress.models import TeacherAlert

        today = timezone.now().date()

        students = CustomUser.objects.filter(
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

        all_stats = [get_student_stats(s, today) for s in students]

        scores = [s["avg_score_last_7_days"] for s in all_stats if s["quizzes_completed"] > 0]
        avg_class_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        struggling_count = sum(1 for s in all_stats if s["is_struggling"])

        unread_alerts = TeacherAlert.objects.filter(
            teacher=request.user, is_read=False
        ).count()

        sorted_by_activity = sorted(
            all_stats, key=lambda s: s["total_study_minutes"], reverse=True
        )
        most_active = sorted_by_activity[0]["full_name"] if sorted_by_activity else None
        least_active = sorted_by_activity[-1]["full_name"] if len(sorted_by_activity) > 1 else None

        data = {
            "total_students": students.count(),
            "struggling_students_count": struggling_count,
            "avg_class_score": avg_class_score,
            "total_alerts_unread": unread_alerts,
            "most_active_student": most_active,
            "least_active_student": least_active,
        }
        return Response(DashboardOverviewSerializer(data).data)


class DashboardStudentListView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List all students with stats",
        description=(
            "Returns all linked students with their stats. "
            "Sort with ?sort=score, ?sort=activity, or ?sort=name."
        ),
        tags=["Dashboard"],
        responses={200: StudentOverviewSerializer(many=True)},
    )
    def get(self, request):
        from users.models import CustomUser

        today = timezone.now().date()
        sort_by = request.query_params.get("sort", "name")

        students = CustomUser.objects.filter(
            enrolled_teachers__teacher=request.user, role="student"
        )

        all_stats = [get_student_stats(s, today) for s in students]

        if sort_by == "score":
            all_stats.sort(key=lambda s: s["avg_score_last_7_days"], reverse=True)
        elif sort_by == "activity":
            all_stats.sort(key=lambda s: s["total_study_minutes"], reverse=True)
        else:
            all_stats.sort(key=lambda s: s["full_name"])

        return Response(StudentOverviewSerializer(all_stats, many=True).data)


class DashboardStudentDetailView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get full student details",
        description="Returns complete stats for one linked student including struggling analysis.",
        tags=["Dashboard"],
        responses={
            200: StudentOverviewSerializer,
            403: OpenApiResponse(description="Student not linked to this teacher"),
            404: OpenApiResponse(description="Student not found"),
        },
    )
    def get(self, request, student_id):
        from users.models import CustomUser, ClassEnrollment

        is_linked = ClassEnrollment.objects.filter(
            teacher=request.user, student__id=student_id
        ).exists()

        if not is_linked:
            return Response({"error": "This student is not linked to you."}, status=403)

        try:
            student = CustomUser.objects.get(id=student_id, role="student")
        except CustomUser.DoesNotExist:
            return Response({"error": "Student not found."}, status=404)

        today = timezone.now().date()
        stats = get_student_stats(student, today)
        return Response(StudentOverviewSerializer(stats).data)


class DashboardStrugglingView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get struggling students",
        description=(
            "Returns only students flagged as struggling. "
            "Struggling = score < 50% last 7 days, OR inactive 3+ days, "
            "OR 3 consecutive failed quizzes."
        ),
        tags=["Dashboard"],
        responses={200: StudentOverviewSerializer(many=True)},
    )
    def get(self, request):
        from users.models import CustomUser

        today = timezone.now().date()

        students = CustomUser.objects.filter(
            enrolled_teachers__teacher=request.user, role="student"
        )

        struggling = [
            stats for s in students
            if (stats := get_student_stats(s, today))["is_struggling"]
        ]

        struggling.sort(key=lambda s: len(s["struggling_reasons"]), reverse=True)

        return Response(StudentOverviewSerializer(struggling, many=True).data)
