from django.contrib import admin
from .models import StudySession, WeeklyProgressSnapshot, TeacherAlert


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ["student", "activity_type", "session_date", "duration_minutes"]
    list_filter = ["activity_type", "session_date"]
    search_fields = ["student__email", "student__full_name"]
    readonly_fields = ["id"]


@admin.register(WeeklyProgressSnapshot)
class WeeklyProgressSnapshotAdmin(admin.ModelAdmin):
    list_display = ["student", "week_start_date", "average_quiz_score", "quizzes_completed_count", "total_study_minutes"]
    list_filter = ["week_start_date"]
    search_fields = ["student__email"]
    readonly_fields = ["id"]


@admin.register(TeacherAlert)
class TeacherAlertAdmin(admin.ModelAdmin):
    list_display = ["student", "teacher", "alert_type", "is_read", "created_at"]
    list_filter = ["alert_type", "is_read", "created_at"]
    search_fields = ["student__email", "teacher__email"]
    readonly_fields = ["id", "created_at"]
