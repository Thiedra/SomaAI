"""
career/models.py
Models for the AI career guidance feature.
Student answers 8 questions, AI returns 3 ranked career recommendations.
"""
import uuid
from django.db import models
from django.conf import settings


class CareerAssessment(models.Model):
    """
    Stores a student's answers to the 8 career assessment questions.
    One assessment per student — re-submitting updates the existing record.
    Triggers AI career matching when created or updated.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="career_assessment",
        verbose_name="Student",
    )
    # format: {"q1": "I enjoy mathematics", "q2": "I prefer working with data", ...}
    question_answers = models.JSONField(
        verbose_name="Assessment Answers",
        help_text="Student's answers to all 8 career assessment questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Career Assessment"
        verbose_name_plural = "Career Assessments"

    def __str__(self):
        return f"Career Assessment — {self.student.full_name}"


class CareerRecommendation(models.Model):
    """
    A single AI-generated career recommendation linked to a CareerAssessment.
    Each assessment produces exactly 3 recommendations ranked 1 (best match) to 3.
    Includes required subjects and local African universities.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        CareerAssessment,
        on_delete=models.CASCADE,
        related_name="recommendations",
        verbose_name="Career Assessment",
    )
    career_title = models.CharField(
        max_length=255,
        verbose_name="Career Title",
        help_text="e.g. Software Engineer, Medical Doctor",
    )
    career_description = models.TextField(
        verbose_name="Career Description",
    )
    # e.g. ["Mathematics", "Physics", "Computer Science"]
    required_subjects = models.JSONField(
        default=list,
        verbose_name="Required Subjects",
    )
    # e.g. [{"name": "University of Rwanda", "location": "Kigali", "duration_years": 4}]
    african_universities = models.JSONField(
        default=list,
        verbose_name="African Universities",
        help_text="Local universities where this career can be studied",
    )
    match_score = models.FloatField(
        verbose_name="Match Score (%)",
        help_text="How well this career matches the student's profile (0–100)",
    )
    rank = models.IntegerField(
        verbose_name="Rank",
        help_text="1 = best match, 3 = third best match",
    )

    class Meta:
        verbose_name = "Career Recommendation"
        verbose_name_plural = "Career Recommendations"
        ordering = ["rank"]

    def __str__(self):
        return f"Rank {self.rank}: {self.career_title} — {self.assessment.student.full_name}"
