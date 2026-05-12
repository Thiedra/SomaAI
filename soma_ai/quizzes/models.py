"""
quizzes/models.py
Models for AI-generated quizzes, multiple-choice questions, and student attempts.
"""
import uuid
from django.db import models
from django.conf import settings


class Quiz(models.Model):
    """
    A set of AI-generated questions based on a student's simplified note.
    Questions are created asynchronously by Claude AI after the quiz is created.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_note = models.ForeignKey(
        "simplifier.StudentNote",
        on_delete=models.CASCADE,
        related_name="quizzes",
        verbose_name="Source Note",
        help_text="The note this quiz was generated from",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
        verbose_name="Student",
    )
    language = models.CharField(
        max_length=20,
        default="english",
        verbose_name="Quiz Language",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quiz — {self.source_note.title} ({self.student.full_name})"


class QuizQuestion(models.Model):
    """
    A single multiple-choice question in a Quiz.
    Has four answer options (A–D) with one correct answer.
    The correct answer is never sent to the frontend during the quiz.
    """

    class AnswerOption(models.TextChoices):
        A = "a", "Option A"
        B = "b", "Option B"
        C = "c", "Option C"
        D = "d", "Option D"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Quiz",
    )
    question_text = models.TextField(verbose_name="Question")
    option_a = models.CharField(max_length=500, verbose_name="Option A")
    option_b = models.CharField(max_length=500, verbose_name="Option B")
    option_c = models.CharField(max_length=500, verbose_name="Option C")
    option_d = models.CharField(max_length=500, verbose_name="Option D")
    correct_answer = models.CharField(
        max_length=1,
        choices=AnswerOption.choices,
        verbose_name="Correct Answer",
    )
    answer_explanation = models.TextField(
        null=True, blank=True,
        verbose_name="Answer Explanation",
        help_text="Why this answer is correct — shown after submission",
    )

    class Meta:
        verbose_name = "Quiz Question"
        verbose_name_plural = "Quiz Questions"

    def __str__(self):
        return f"Q: {self.question_text[:80]}"


class QuizSubmission(models.Model):
    """
    Records a student's answers and calculated score for a quiz.
    Only one submission is allowed per student per quiz.
    The score is always calculated server-side — never trusted from the client.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name="Quiz",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_submissions",
        verbose_name="Student",
    )
    # format: {"<question_uuid>": "b", "<question_uuid>": "c"}
    submitted_answers = models.JSONField(
        verbose_name="Submitted Answers",
        help_text="Map of question UUID to selected option letter",
    )
    score_percentage = models.IntegerField(
        default=0,
        verbose_name="Score (%)",
        help_text="Calculated server-side as a percentage 0–100",
    )
    duration_seconds = models.IntegerField(
        default=0,
        verbose_name="Time Taken (seconds)",
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Submitted At")

    class Meta:
        verbose_name = "Quiz Submission"
        verbose_name_plural = "Quiz Submissions"
        unique_together = ("quiz", "student")  # one submission per student per quiz

    def __str__(self):
        return f"{self.student.full_name} — {self.quiz} — {self.score_percentage}%"
