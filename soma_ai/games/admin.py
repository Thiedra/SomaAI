from django.contrib import admin
from .models import GameScore

@admin.register(GameScore)
class GameScoreAdmin(admin.ModelAdmin):
    list_display = ["student", "game_id", "score", "played_at"]
    list_filter = ["game_id", "played_at"]
    search_fields = ["student__full_name", "game_id"]
    readonly_fields = ["id", "played_at"]
