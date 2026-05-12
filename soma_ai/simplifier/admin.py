from django.contrib import admin
from .models import StudentNote, SimplifiedNote, AudioGeneration


class SimplifiedNoteInline(admin.StackedInline):
    model = SimplifiedNote
    extra = 0
    readonly_fields = ["simplified_text", "glossary", "ai_model_used", "created_at"]


@admin.register(StudentNote)
class StudentNoteAdmin(admin.ModelAdmin):
    list_display = ["title", "student", "language", "created_at"]
    list_filter = ["language", "created_at"]
    search_fields = ["title", "student__email"]
    readonly_fields = ["id", "created_at"]
    inlines = [SimplifiedNoteInline]


@admin.register(SimplifiedNote)
class SimplifiedNoteAdmin(admin.ModelAdmin):
    list_display = ["original_note", "reading_level", "ai_model_used", "created_at"]
    list_filter = ["reading_level", "ai_model_used"]
    readonly_fields = ["id", "simplified_text", "glossary", "ai_model_used", "created_at"]


@admin.register(AudioGeneration)
class AudioGenerationAdmin(admin.ModelAdmin):
    list_display = ["simplified_note", "status", "language", "created_at"]
    list_filter = ["status", "language"]
    readonly_fields = ["id", "created_at"]
