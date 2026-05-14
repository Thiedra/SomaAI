"""
notifications/tasks.py
Celery tasks for sending email notifications.
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_alert_email(self, alert_id: str):
    from progress.models import TeacherAlert
    try:
        alert = TeacherAlert.objects.select_related("teacher", "student").get(id=alert_id)
        html_message = render_to_string("emails/alert_email.html", {
            "teacher_name": alert.teacher.full_name,
            "student_name": alert.student.full_name,
            "alert_type": alert.get_alert_type_display(),
            "message": alert.message,
        })
        send_mail(
            subject=f"Soma AI Alert — {alert.student.full_name} needs attention",
            message=alert.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[alert.teacher.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Alert email sent to {alert.teacher.email}")
    except Exception as exc:
        logger.error(f"send_alert_email failed for alert {alert_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_all_weekly_student_summaries():
    from users.models import User
    students = User.objects.filter(role="student", is_active=True)
    for student in students:
        send_weekly_student_summary.delay(str(student.id))
    logger.info(f"Queued weekly summaries for {students.count()} students.")


@shared_task(bind=True, max_retries=3)
def send_weekly_student_summary(self, student_id: str):
    from users.models import User
    from quizzes.models import QuizSubmission
    from progress.models import StudySession
    from django.utils import timezone
    from datetime import timedelta

    try:
        student = User.objects.get(id=student_id)
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        submissions = QuizSubmission.objects.filter(
            student=student,
            submitted_at__date__range=(week_start, week_end),
        )
        sessions = StudySession.objects.filter(
            student=student,
            session_date__range=(week_start, week_end),
        )

        avg_score = (
            round(sum(s.score_percentage for s in submissions) / submissions.count(), 1)
            if submissions.count() > 0 else 0
        )
        study_minutes = sum(s.duration_minutes for s in sessions)

        if avg_score >= 80:
            motivational_message = "Outstanding week! You are on fire. Keep it up!"
        elif avg_score >= 60:
            motivational_message = "Great progress this week! Every session counts."
        elif submissions.count() == 0:
            motivational_message = "A new week is a fresh start. You can do this!"
        else:
            motivational_message = "Keep going — consistency is the key to success."

        html_message = render_to_string("emails/weekly_student_summary.html", {
            "student_name": student.full_name,
            "quizzes_completed": submissions.count(),
            "avg_score": avg_score,
            "study_minutes": study_minutes,
            "motivational_message": motivational_message,
        })
        send_mail(
            subject="Your Weekly Study Summary — Soma AI",
            message=f"Hi {student.full_name}, here is your weekly summary.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Weekly summary sent to {student.email}")
    except Exception as exc:
        logger.error(f"send_weekly_student_summary failed for {student_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_all_weekly_teacher_reports():
    from users.models import User
    teachers = User.objects.filter(role="teacher", is_active=True)
    for teacher in teachers:
        send_weekly_teacher_report.delay(str(teacher.id))
    logger.info(f"Queued weekly reports for {teachers.count()} teachers.")


@shared_task(bind=True, max_retries=3)
def send_weekly_teacher_report(self, teacher_id: str):
    from users.models import User, ClassEnrollment
    from quizzes.models import QuizSubmission
    from progress.models import StudySession
    from django.utils import timezone
    from datetime import timedelta

    try:
        teacher = User.objects.get(id=teacher_id)
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)
        three_days_ago = today - timedelta(days=3)

        students = User.objects.filter(
            enrolled_teachers__teacher=teacher, role="student"
        )
        if not students.exists():
            return

        all_scores = []
        struggling_students = []

        for student in students:
            recent_submissions = QuizSubmission.objects.filter(
                student=student,
                submitted_at__date__gte=seven_days_ago,
            )
            avg = (
                sum(s.score_percentage for s in recent_submissions) / recent_submissions.count()
                if recent_submissions.count() > 0 else None
            )
            if avg is not None:
                all_scores.append(avg)

            reasons = []
            if avg is not None and avg < 50:
                reasons.append(f"Low quiz score: {round(avg, 1)}%")

            has_recent = StudySession.objects.filter(
                student=student, session_date__gte=three_days_ago
            ).exists()
            if not has_recent:
                reasons.append("Inactive for 3+ days")

            if reasons:
                struggling_students.append({
                    "name": student.full_name,
                    "reason": " | ".join(reasons),
                })

        avg_class_score = (
            round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
        )

        html_message = render_to_string("emails/weekly_teacher_report.html", {
            "teacher_name": teacher.full_name,
            "total_students": students.count(),
            "avg_class_score": avg_class_score,
            "struggling_count": len(struggling_students),
            "struggling_students": struggling_students,
        })
        send_mail(
            subject="Your Weekly Class Report — Soma AI",
            message=f"Hi {teacher.full_name}, here is your weekly class report.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[teacher.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Weekly teacher report sent to {teacher.email}")
    except Exception as exc:
        logger.error(f"send_weekly_teacher_report failed for {teacher_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
