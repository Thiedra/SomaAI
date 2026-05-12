"""
progress/tasks.py
Celery beat tasks for weekly progress snapshots and inactivity alerts.
These run on a schedule — not triggered by user actions.
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def compute_weekly_snapshots():
    """
    Celery beat task — runs every Monday at midnight.
    Computes a ProgressSnapshot for every active student
    covering the previous week (Monday to Sunday).
    """
    from progress.models import StudySession, ProgressSnapshot
    from users.models import CustomUser
    from quizzes.models import QuizAttempt
    from simplifier.models import Note

    today = timezone.now().date()
    # find the most recent Monday
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    students = CustomUser.objects.filter(role="student", is_active=True)

    for student in students:
        # get all quiz attempts this week
        attempts = QuizAttempt.objects.filter(
            student=student,
            completed_at__date__range=(week_start, week_end),
        )
        avg_score = (
            sum(a.score for a in attempts) / attempts.count()
            if attempts.count() > 0 else 0.0
        )

        # total study minutes from sessions this week
        sessions = StudySession.objects.filter(
            student=student,
            date__range=(week_start, week_end),
        )
        total_minutes = sum(s.duration_minutes for s in sessions)

        # notes created this week
        notes_count = Note.objects.filter(
            student=student,
            created_at__date__range=(week_start, week_end),
        ).count()

        # save or update the snapshot for this week
        ProgressSnapshot.objects.update_or_create(
            student=student,
            week_start=week_start,
            defaults={
                "avg_quiz_score": round(avg_score, 2),
                "total_study_minutes": total_minutes,
                "notes_created": notes_count,
                "quizzes_completed": attempts.count(),
            },
        )

    logger.info(f"Weekly snapshots computed for {students.count()} students.")


@shared_task
def check_inactivity_alerts():
    """
    Celery beat task — runs every day.
    Creates an inactivity Alert for any student who has had
    no study session in the last 3 days.
    """
    from progress.models import StudySession, Alert
    from users.models import CustomUser, TeacherStudentRelationship

    today = timezone.now().date()
    three_days_ago = today - timedelta(days=3)

    students = CustomUser.objects.filter(role="student", is_active=True)

    for student in students:
        # check if student has any session in the last 3 days
        recent_session = StudySession.objects.filter(
            student=student,
            date__gte=three_days_ago,
        ).exists()

        if recent_session:
            continue  # student is active — no alert needed

        # get linked teachers
        teachers = TeacherStudentRelationship.objects.filter(
            student=student
        ).select_related("teacher")

        for rel in teachers:
            # avoid duplicate inactivity alerts on the same day
            already_alerted = Alert.objects.filter(
                student=student,
                teacher=rel.teacher,
                alert_type="inactivity",
                created_at__date=today,
            ).exists()

            if not already_alerted:
                Alert.objects.create(
                    student=student,
                    teacher=rel.teacher,
                    alert_type="inactivity",
                    message=(
                        f"{student.full_name} has not studied in the last 3 days."
                    ),
                )
                logger.info(
                    f"Inactivity alert created for {student.full_name}"
                )
