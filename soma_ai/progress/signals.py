"""
progress/signals.py
Signals that fire on quiz submission:
- records a StudySession
- updates SubjectMastery for the quiz subject
- updates weak_subject on the student
- creates TeacherAlert if score < 50% or 3 consecutive failures
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Avg

logger = logging.getLogger(__name__)


@receiver(post_save, sender="quizzes.QuizSubmission")
def handle_quiz_submission(sender, instance, created, **kwargs):
    if not created:
        return

    from progress.models import StudySession, SubjectMastery, TeacherAlert
    from users.models import ClassEnrollment

    student = instance.student
    today = timezone.now().date()

    # 1 — record study session
    StudySession.objects.create(
        student=student,
        session_date=today,
        duration_minutes=max(1, instance.duration_seconds // 60),
        activity_type="quiz",
    )

    # 2 — update subject mastery
    # derive subject from the quiz's source note title (e.g. "P6 Mathematics PB" → "Math")
    subject = _derive_subject(instance.quiz.source_note.title)
    if subject:
        all_scores = sender.objects.filter(
            student=student,
            quiz__source_note__title__icontains=_subject_keyword(subject),
        ).aggregate(avg=Avg("score_percentage"))["avg"] or 0.0

        SubjectMastery.objects.update_or_create(
            student=student,
            subject=subject,
            defaults={"value": round(all_scores, 1)},
        )

        # 3 — update weak_subject on the student profile
        _update_weak_subject(student)

    # 4 — teacher alerts
    teachers = ClassEnrollment.objects.filter(
        student=student
    ).select_related("teacher")

    if not teachers.exists():
        return

    if instance.score_percentage < 50:
        for rel in teachers:
            alert = TeacherAlert.objects.create(
                student=student,
                teacher=rel.teacher,
                alert_type=TeacherAlert.AlertType.SCORE_DROP,
                message=(
                    f"{student.full_name} scored {instance.score_percentage}% on "
                    f"'{instance.quiz.source_note.title}'."
                ),
            )
            try:
                from notifications.tasks import send_alert_email
                send_alert_email.delay(str(alert.id))
            except Exception as e:
                logger.warning(f"Could not queue alert email: {e}")

    # struggling_topic: 3+ failed submissions on same note
    from quizzes.models import QuizSubmission
    failed_count = QuizSubmission.objects.filter(
        student=student,
        quiz__source_note=instance.quiz.source_note,
        score_percentage__lt=50,
    ).count()

    if failed_count >= 3:
        for rel in teachers:
            already = TeacherAlert.objects.filter(
                student=student,
                teacher=rel.teacher,
                alert_type=TeacherAlert.AlertType.STRUGGLING_TOPIC,
                message__icontains=instance.quiz.source_note.title,
            ).exists()
            if not already:
                alert = TeacherAlert.objects.create(
                    student=student,
                    teacher=rel.teacher,
                    alert_type=TeacherAlert.AlertType.STRUGGLING_TOPIC,
                    message=(
                        f"{student.full_name} has failed 3+ quizzes on "
                        f"'{instance.quiz.source_note.title}'."
                    ),
                )
                try:
                    from notifications.tasks import send_alert_email
                    send_alert_email.delay(str(alert.id))
                except Exception as e:
                    logger.warning(f"Could not queue alert email: {e}")


def _derive_subject(note_title: str) -> str | None:
    """Map a note title to a frontend subject name."""
    title = note_title.lower()
    if "math" in title:
        return "Math"
    if "english" in title:
        return "English"
    if "science" in title or "set" in title:
        return "Science"
    if "kinyarwanda" in title:
        return "Kinyarwanda"
    if "social" in title:
        return "Social"
    return None


def _subject_keyword(subject: str) -> str:
    mapping = {
        "Math": "math",
        "English": "english",
        "Science": "science",
        "Kinyarwanda": "kinyarwanda",
        "Social": "social",
    }
    return mapping.get(subject, subject.lower())


def _update_weak_subject(student):
    """Set student.weak_subject to the subject with the lowest mastery."""
    from progress.models import SubjectMastery
    weakest = (
        SubjectMastery.objects.filter(student=student)
        .order_by("value")
        .first()
    )
    if weakest:
        student.weak_subject = weakest.subject
        student.save(update_fields=["weak_subject"])
