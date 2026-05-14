"""
planner/admin.py

Admin configuration for the Study Planner models.

CalendarEvent   — manually created student events (primary feature).
StudyPlan       — AI-generated plans (reserved for future use).
UpcomingExam    — exam dates linked to a study plan.
DailyStudyBlock — AI-scheduled time blocks within a study plan.
"""
from django.contrib import admin
from .models import CalendarEvent, StudyPlan, UpcomingExam, DailyStudyBlock


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    """
    Admin view for student calendar events.
    Allows filtering by type, color, done status, and date.
    Teachers can set the mark field directly from here.
    """
    list_display  = ["student", "title", "date", "type", "color", "done", "mark"]
    list_filter   = ["type", "color", "done", "date"]
    search_fields = ["student__full_name", "student__soma_id", "title"]
    ordering      = ["date"]
    readonly_fields = ["id", "created_at"]

    fieldsets = (
        ("Event Info", {
            "fields": ("id", "student", "title", "date", "type", "color")
        }),
        ("Status", {
            "fields": ("done", "mark", "due_notified")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    """Admin view for AI-generated study plans."""
    list_display  = ["student", "is_active", "created_at"]
    list_filter   = ["is_active"]
    search_fields = ["student__full_name", "student__soma_id"]
    readonly_fields = ["id", "created_at"]


@admin.register(UpcomingExam)
class UpcomingExamAdmin(admin.ModelAdmin):
    """Admin view for exam dates linked to study plans."""
    list_display = ["subject_name", "exam_date", "priority_level", "study_plan"]
    list_filter  = ["priority_level"]
    ordering     = ["exam_date"]
    readonly_fields = ["id"]


@admin.register(DailyStudyBlock)
class DailyStudyBlockAdmin(admin.ModelAdmin):
    """Admin view for AI-generated daily study blocks."""
    list_display  = [
        "subject_name", "scheduled_date",
        "start_time", "end_time",
        "is_completed", "was_rescheduled_by_ai",
    ]
    list_filter   = ["is_completed", "was_rescheduled_by_ai", "scheduled_date"]
    search_fields = ["subject_name", "study_plan__student__full_name"]
    readonly_fields = ["id"]
