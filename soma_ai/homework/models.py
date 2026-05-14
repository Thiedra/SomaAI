"""
homework/models.py

Models for the Homework and Assignment features.

Homework    — A task assigned by a teacher to one or more students.
              Students see it on their dashboard under "My Homework".
              Completing homework awards XP to the student.

Assignment  — A class-wide task created by a teacher and broadcast to
              all enrolled students. Students can submit against it.
              The frontend shows assignments separately from homework.

Relationship:
  Teacher creates Assignment → system creates Homework records for each
  enrolled student → students complete their Homework records.
"""
import uuid
from django.db import models
from django.conf import settings


class Assignment(models.Model):
    """
    A class-wide task created by a teacher.

    When a teacher creates an assignment, individual Homework records
    are generated for every student enrolled in their class. The
    `count` field on the frontend is derived from the number of
    related Homework records.

    Frontend shape:
        { id, title, subject, due, classId, count, status }
    """

    class Status(models.TextChoices):
        ASSIGNED  = "assigned",  "Assigned"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Short description of the assignment shown on the dashboard.",
    )
    subject = models.CharField(
        max_length=100,
        verbose_name="Subject",
        help_text="e.g. Mathematics, English, Science.",
    )
    due = models.DateField(
        verbose_name="Due Date",
        help_text="The date by which students must complete this assignment.",
    )
    class_id = models.CharField(
        max_length=50,
        verbose_name="Class ID",
        help_text=(
            "Identifier for the class this assignment targets. "
            "Matches the teacher's class_grade field (e.g. 'P6')."
        ),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_assignments",
        limit_choices_to={"role": "teacher"},
        verbose_name="Created By",
        help_text="The teacher who created this assignment.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
        verbose_name="Status",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Assignment"
        verbose_name_plural = "Assignments"
        ordering = ["due"]

    def __str__(self):
        return f"{self.title} — {self.subject} (due {self.due})"


class Homework(models.Model):
    """
    A single homework task assigned to one specific student.

    Homework records are created automatically when a teacher creates
    an Assignment — one record per enrolled student. They can also be
    created directly by a teacher for an individual student.

    Completing a homework record awards `xp_reward` XP to the student.
    The frontend polls GET /api/v1/homework/ to populate the student's
    homework list, which was previously always empty ([]).

    Frontend shape:
        { id, title, subject, due, status, xpReward }
    """

    class Status(models.TextChoices):
        ASSIGNED  = "assigned",  "Assigned"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="homework_items",
        null=True,
        blank=True,
        verbose_name="Source Assignment",
        help_text=(
            "The assignment this homework was generated from. "
            "Null for homework created directly for an individual student."
        ),
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="homework",
        limit_choices_to={"role": "student"},
        verbose_name="Student",
        help_text="The student this homework is assigned to.",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_homework",
        limit_choices_to={"role": "teacher"},
        verbose_name="Assigned By",
        help_text="The teacher who assigned this homework.",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
    )
    subject = models.CharField(
        max_length=100,
        verbose_name="Subject",
    )
    due = models.DateField(
        verbose_name="Due Date",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
        verbose_name="Status",
    )
    xp_reward = models.IntegerField(
        default=50,
        verbose_name="XP Reward",
        help_text=(
            "XP awarded to the student when they mark this homework as complete. "
            "Default is 50 XP per the frontend spec."
        ),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Completed At",
        help_text="Timestamp set automatically when the student marks this as done.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Homework"
        verbose_name_plural = "Homework"
        ordering = ["due"]

    def __str__(self):
        return f"{self.student.full_name} — {self.title} (due {self.due})"
