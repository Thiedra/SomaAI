import uuid
from django.db import models
from django.conf import settings


class GameScore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="game_scores",
    )
    game_id = models.CharField(max_length=100, verbose_name="Game ID")
    score = models.IntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Game Score"
        verbose_name_plural = "Game Scores"
        ordering = ["-played_at"]

    def __str__(self):
        return f"{self.student.full_name} — {self.game_id}: {self.score}"
