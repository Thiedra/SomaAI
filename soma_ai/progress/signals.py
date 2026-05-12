"""
progress/signals.py
Django signals that automatically record study activity, fire alerts,
and trigger email notifications when a student completes a quiz.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender="quizzes.QuizAttempt")
def handle_quiz_attempt(sender, instance, created, **kwargs):
    """
    Fires when a QuizAttempt is saved.
    - Records a StudySession.
    - Creates score_drop Alert + sends email if score < 50%.
    - Creates struggling_topic Alert if 3+ failed quizzes on same note.
    """
    if not created:
        return

    from progress.models import StudySession, Alert
    from users.models import TeacherStudentRelationship
    from notifications.tasks import send_alert_email

    student = instance.student
    today = timezone.now().date()

    # record study session
    StudySession.objects.create(
        student=student,
        date=today,
        duration_minutes=max(1, instance.time_taken_seconds // 60),
        activity_type="quiz",
    )

    teachers = TeacherStudentRelationship.objects.filter(
        student=student
    ).select_related("teacher")

    if not teachers.exists():
        return

    # --- score_drop alert ---
    if instance.score < 50:
        for rel in teachers:
            alert = Alert.objects.create(
                student=student,
                teacher=rel.teacher,
                alert_type="score_drop",
                message=(
                    f"{student.full_name} scored {instance.score}% on a quiz "
                    f"for note '{instance.quiz.note.title}'."
                ),
            )
            # send email immediately
            send_alert_email.delay(str(alert.id))
        logger.info(f"score_drop alert created for {student.full_name}")

    # --- struggling_topic alert ---
    from quizzes.models import QuizAttempt
    failed_attempts = QuizAttempt.objects.filter(
        student=student,
        quiz__note=instance.quiz.note,
        score__lt=50,
    ).count()

    if failed_attempts >= 3:
        for rel in teachers:
            already_alerted = Alert.objects.filter(
                student=student,
                teacher=rel.teacher,
                alert_type="struggling_topic",
                message__icontains=instance.quiz.note.title,
            ).exists()

            if not already_alerted:
                alert = Alert.objects.create(
                    student=student,
                    teacher=rel.teacher,
                    alert_type="struggling_topic",
                    message=(
                        f"{student.full_name} has failed 3 or more quizzes "
                        f"on '{instance.quiz.note.title}'."
                    ),
                )
                send_alert_email.delay(str(alert.id))
        logger.info(f"struggling_topic alert created for {student.full_name}")
