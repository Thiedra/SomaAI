from django.contrib import admin
from .models import Quiz, QuizQuestion, QuizSubmission


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    readonly_fields = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_answer"]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["source_note", "student", "language", "created_at"]
    list_filter = ["language", "created_at"]
    search_fields = ["source_note__title", "student__email"]
    readonly_fields = ["id", "created_at"]
    inlines = [QuizQuestionInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ["question_text", "quiz", "correct_answer"]
    search_fields = ["question_text"]
    readonly_fields = ["id"]


@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = ["student", "quiz", "score_percentage", "duration_seconds", "submitted_at"]
    list_filter = ["submitted_at"]
    search_fields = ["student__email"]
    readonly_fields = ["id", "score_percentage", "submitted_answers", "submitted_at"]
