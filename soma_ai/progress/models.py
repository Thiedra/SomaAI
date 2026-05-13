"""
progress/models.py
Models for subject mastery, study sessions, weekly snapshots, and teacher alerts.
"""
import uuid
from django.db import models
from django.conf import settings


SUBJECT_CHOICES = [
    ("Math", "Math"),
    ("English", "English"),
    ("Science", "Science"),
    ("Kinyarwanda", "Kinyarwanda"),
    ("Social", "Social"),
]


class SubjectMastery(models.Model):
    """
    Tracks a student's mastery percentage per subject (0–100).
    Updated automatically every time a quiz submission is saved.
    One record per student per subject — updated in place, never duplicated.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subject_masteries",
        verbose_name="Student",
    )
    subject = models.CharField(
        max_length=20,
        choices=SUBJECT_CHOICES,
        verbose_name="Subject",
    )
    value = models.FloatField(
        default=0.0,
        verbose_name="Mastery (%)",
        help_text="0–100 mastery percentage for this subject",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subject Mastery"
        verbose_name_plural = "Subject Masteries"
        unique_together = ("student", "subject")
        ordering = ["subject"]

    def __str__(self):
        return f"{self.student.full_name} — {self.subject}: {self.value}%"


class StudySession(models.Model):
    """
    Records a single study activity completed by a student.
    Created automatically via signals when a student submits a quiz,
    completes a planner slot, or simplifies a note.
    """

    class ActivityType(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        NOTE_SIMPLIFICATION = "simplifier", "Note Simplification"
        STUDY_PLANNER = "planner", "Study Planner"
        NOTE_READING = "notes", "Note Reading"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_sessions",
        verbose_name="Student",
    )
    session_date = models.DateField(verbose_name="Session Date")
    duration_minutes = models.IntegerField(default=0, verbose_name="Duration (minutes)")
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        verbose_name="Activity Type",
    )

    class Meta:
        verbose_name = "Study Session"
        verbose_name_plural = "Study Sessions"
        ordering = ["-session_date"]

    def __str__(self):
        return f"{self.student.full_name} — {self.get_activity_type_display()} on {self.session_date}"


class WeeklyProgressSnapshot(models.Model):
    """
    A computed weekly summary of a student's performance.
    Generated every Monday via Celery beat.
    Stores both overall stats and per-subject scores for the frontend chart.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weekly_snapshots",
        verbose_name="Student",
    )
    week_start_date = models.DateField(
        verbose_name="Week Start Date",
        help_text="Always a Monday",
    )
    # overall
    average_quiz_score = models.FloatField(default=0.0, verbose_name="Average Quiz Score (%)")
    total_study_minutes = models.IntegerField(default=0, verbose_name="Total Study Minutes")
    notes_created_count = models.IntegerField(default=0, verbose_name="Notes Created")
    quizzes_completed_count = models.IntegerField(default=0, verbose_name="Quizzes Completed")
    # per-subject scores — used by frontend progress chart
    math_score = models.FloatField(default=0.0, verbose_name="Math Score (%)")
    english_score = models.FloatField(default=0.0, verbose_name="English Score (%)")
    science_score = models.FloatField(default=0.0, verbose_name="Science Score (%)")
    kinyarwanda_score = models.FloatField(default=0.0, verbose_name="Kinyarwanda Score (%)")
    social_score = models.FloatField(default=0.0, verbose_name="Social Score (%)")

    class Meta:
        verbose_name = "Weekly Progress Snapshot"
        verbose_name_plural = "Weekly Progress Snapshots"
        ordering = ["-week_start_date"]
        unique_together = ("student", "week_start_date")

    def __str__(self):
        return f"{self.student.full_name} — week of {self.week_start_date}"


class TeacherAlert(models.Model):
    """
    A notification sent to a teacher when one of their students is struggling.
    """

    class AlertType(models.TextChoices):
        SCORE_DROP = "score_drop", "Score Drop"
        INACTIVITY = "inactivity", "Inactivity"
        STRUGGLING_TOPIC = "struggling_topic", "Struggling Topic"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_alerts",
        verbose_name="Student",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_alerts",
        verbose_name="Teacher",
    )
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        verbose_name="Alert Type",
    )
    message = models.TextField(verbose_name="Alert Message")
    is_read = models.BooleanField(default=False, verbose_name="Read by Teacher")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Teacher Alert"
        verbose_name_plural = "Teacher Alerts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_alert_type_display()}] {self.student.full_name} → {self.teacher.full_name}"
