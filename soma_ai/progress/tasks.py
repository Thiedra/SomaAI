"""
progress/tasks.py
Celery beat tasks for weekly snapshots and inactivity alerts.
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Sum

logger = logging.getLogger(__name__)


@shared_task
def compute_weekly_snapshots():
    """Runs every Monday at midnight. Computes WeeklyProgressSnapshot for every student."""
    from progress.models import StudySession, WeeklyProgressSnapshot, SubjectMastery
    from users.models import User
    from quizzes.models import QuizSubmission
    from simplifier.models import StudentNote

    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    students = User.objects.filter(role="student", is_active=True)

    for student in students:
        submissions = QuizSubmission.objects.filter(
            student=student,
            submitted_at__date__range=(week_start, week_end),
        )
        avg_score = submissions.aggregate(avg=Avg("score_percentage"))["avg"] or 0.0

        sessions = StudySession.objects.filter(
            student=student,
            session_date__range=(week_start, week_end),
        )
        total_minutes = sessions.aggregate(total=Sum("duration_minutes"))["total"] or 0

        notes_count = StudentNote.objects.filter(
            student=student,
            created_at__date__range=(week_start, week_end),
        ).count()

        # per-subject scores from SubjectMastery (current snapshot)
        def subject_score(subj):
            m = SubjectMastery.objects.filter(student=student, subject=subj).first()
            return m.value if m else 0.0

        WeeklyProgressSnapshot.objects.update_or_create(
            student=student,
            week_start_date=week_start,
            defaults={
                "average_quiz_score": round(avg_score, 2),
                "total_study_minutes": total_minutes,
                "notes_created_count": notes_count,
                "quizzes_completed_count": submissions.count(),
                "math_score": subject_score("Math"),
                "english_score": subject_score("English"),
                "science_score": subject_score("Science"),
                "kinyarwanda_score": subject_score("Kinyarwanda"),
                "social_score": subject_score("Social"),
            },
        )

    logger.info(f"Weekly snapshots computed for {students.count()} students.")


@shared_task
def check_inactivity_alerts():
    """Runs every day at 7am. Creates inactivity alerts for inactive students."""
    from progress.models import StudySession, TeacherAlert
    from users.models import User, ClassEnrollment

    today = timezone.now().date()
    three_days_ago = today - timedelta(days=3)

    students = User.objects.filter(role="student", is_active=True)

    for student in students:
        has_recent = StudySession.objects.filter(
            student=student,
            session_date__gte=three_days_ago,
        ).exists()

        if has_recent:
            continue

        teachers = ClassEnrollment.objects.filter(
            student=student
        ).select_related("teacher")

        for rel in teachers:
            already_alerted = TeacherAlert.objects.filter(
                student=student,
                teacher=rel.teacher,
                alert_type=TeacherAlert.AlertType.INACTIVITY,
                created_at__date=today,
            ).exists()

            if not already_alerted:
                TeacherAlert.objects.create(
                    student=student,
                    teacher=rel.teacher,
                    alert_type=TeacherAlert.AlertType.INACTIVITY,
                    message=f"{student.full_name} has not studied in the last 3 days.",
                )
                logger.info(f"Inactivity alert created for {student.full_name}")
