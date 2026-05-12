"""
core/models.py
Shared infrastructure models used across the entire project.
"""
from django.db import models


class AIRequestLog(models.Model):
    """
    Audit log for every AI API call made by the platform.

    Logged for every call — success or failure — to:
      - Monitor API costs and usage
      - Debug failed AI responses
      - Track response times per feature
    """

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    source_feature = models.CharField(
        max_length=50,
        verbose_name="Source Feature",
        help_text="Which app triggered this call: simplifier, quizzes, planner, career",
    )
    ai_model_name = models.CharField(
        max_length=100,
        verbose_name="AI Model Name",
        help_text="e.g. claude-sonnet-4-20250514",
    )
    call_status = models.CharField(
        max_length=10,
        choices=Status.choices,
        verbose_name="Call Status",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Error Message",
        help_text="Populated only when call_status is failed",
    )
    response_time_ms = models.IntegerField(
        default=0,
        verbose_name="Response Time (ms)",
        help_text="How long the AI API call took in milliseconds",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "AI Request Log"
        verbose_name_plural = "AI Request Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"[{self.source_feature}] {self.ai_model_name} "
            f"— {self.call_status} ({self.response_time_ms}ms)"
        )
