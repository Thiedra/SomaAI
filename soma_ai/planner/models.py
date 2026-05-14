"""
planner/models.py

Models for the Soma AI Study Planner feature.

CalendarEvent  — student-created calendar events, previously stored in
                 localStorage (key: "soma_cal_events"). Now persisted in the
                 database so events survive across devices and sessions.

StudyPlan      — AI-generated personalised study plan (reserved for future use).
UpcomingExam   — exam dates linked to a study plan.
DailyStudyBlock — AI-scheduled time blocks within a study plan.
"""
import uuid
from django.db import models
from django.conf import settings


class CalendarEvent(models.Model):
    """
    Represents a single entry on the student's study planner calendar.

    This model is the backend equivalent of the frontend CalEvent type:
        { id, title, date, color, type, done, mark, dueNotified }

    Events are scoped to a single student — a student can only read,
    update, or delete their own events. Teachers can set the `mark` field
    via a separate endpoint when grading submitted work.

    Color and type choices are intentionally restricted to match the
    exact values the frontend renders — do not add new values without
    updating the frontend COLOR_MAP and TYPE_MAP constants.
    """

    class Color(models.TextChoices):
        GREEN  = "green",  "Green"
        BLUE   = "blue",   "Blue"
        PURPLE = "purple", "Purple"
        ORANGE = "orange", "Orange"
        RED    = "red",    "Red"
        YELLOW = "yellow", "Yellow"

    class EventType(models.TextChoices):
        TASK       = "task",       "Task"
        ASSIGNMENT = "assignment", "Assignment"
        EXAM       = "exam",       "Exam"
        REMINDER   = "reminder",   "Reminder"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID — matches the id stored in the frontend localStorage entry.",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_events",
        verbose_name="Student",
        help_text="The student who owns this event.",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Short label shown on the calendar tile.",
    )
    date = models.DateField(
        verbose_name="Event Date",
        help_text="The date this event falls on — format YYYY-MM-DD.",
    )
    color = models.CharField(
        max_length=10,
        choices=Color.choices,
        default=Color.BLUE,
        verbose_name="Color",
        help_text="Colour used to render the event tile on the frontend calendar.",
    )
    type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.TASK,
        verbose_name="Event Type",
        help_text="Controls the icon and badge shown on the frontend.",
    )
    done = models.BooleanField(
        default=False,
        verbose_name="Done",
        help_text="True when the student marks the event as completed.",
    )
    mark = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Mark (0–100)",
        help_text=(
            "Teacher-assigned grade for this event. "
            "Null until the teacher grades the submission."
        ),
    )
    due_notified = models.BooleanField(
        default=False,
        verbose_name="Due Notified",
        help_text="True once the frontend has shown a due-date notification for this event.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Calendar Event"
        verbose_name_plural = "Calendar Events"
        ordering = ["date"]

    def __str__(self):
        return f"{self.student.full_name} — {self.title} ({self.date})"


class StudyPlan(models.Model):
    """
    An AI-generated personalised study plan for a student.

    Only one plan can be active per student at a time. When a new plan
    is generated, the previous active plan is automatically deactivated.

    NOTE: This model is reserved for future AI planner integration.
          The current frontend uses CalendarEvent for manual planning.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_plans",
        verbose_name="Student",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Only one active plan is allowed per student at a time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Study Plan"
        verbose_name_plural = "Study Plans"
        ordering = ["-created_at"]

    def __str__(self):
        label = "Active" if self.is_active else "Inactive"
        return f"{self.student.full_name}'s Study Plan ({label})"


class UpcomingExam(models.Model):
    """
    An exam the student needs to prepare for, linked to their active StudyPlan.

    Priority level controls how much study time the AI allocates to this
    subject when generating the daily study blocks.
    """

    class Priority(models.IntegerChoices):
        HIGH   = 1, "High Priority"    # nearest or most critical exam
        MEDIUM = 2, "Medium Priority"
        LOW    = 3, "Low Priority"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name="upcoming_exams",
        verbose_name="Study Plan",
    )
    subject_name = models.CharField(max_length=255, verbose_name="Subject Name")
    exam_date = models.DateField(verbose_name="Exam Date")
    priority_level = models.IntegerField(
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Priority Level",
    )

    class Meta:
        verbose_name = "Upcoming Exam"
        verbose_name_plural = "Upcoming Exams"
        ordering = ["exam_date"]

    def __str__(self):
        return f"{self.subject_name} — {self.exam_date} ({self.get_priority_level_display()})"


class DailyStudyBlock(models.Model):
    """
    A single time-blocked study session within an AI-generated StudyPlan.

    Blocks are created by the AI based on the student's exam dates,
    available hours per day, and weak subjects. A block can be
    automatically rescheduled by the AI if the student misses a session.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name="daily_blocks",
        verbose_name="Study Plan",
    )
    scheduled_date = models.DateField(verbose_name="Scheduled Date")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    subject_name = models.CharField(max_length=255, verbose_name="Subject")
    study_goal = models.TextField(
        verbose_name="Study Goal",
        help_text="Specific task the student should complete during this block.",
    )
    is_completed = models.BooleanField(
        default=False,
        verbose_name="Completed",
        help_text="Set to True when the student marks this block as done.",
    )
    was_rescheduled_by_ai = models.BooleanField(
        default=False,
        verbose_name="AI Rescheduled",
        help_text="True if this block was regenerated after a missed session.",
    )

    class Meta:
        verbose_name = "Daily Study Block"
        verbose_name_plural = "Daily Study Blocks"
        ordering = ["scheduled_date", "start_time"]

    def __str__(self):
        return (
            f"{self.scheduled_date} "
            f"{self.start_time}–{self.end_time} | {self.subject_name}"
        )
