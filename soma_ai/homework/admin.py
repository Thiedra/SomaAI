"""
homework/admin.py

Admin configuration for Homework and Assignment models.

Homework   — view and manage individual student homework items.
             Filter by status, subject, and due date.

Assignment — view and manage class-wide assignments created by teachers.
             Inline shows all homework records generated from each assignment.
"""
from django.contrib import admin
from .models import Homework, Assignment


class HomeworkInline(admin.TabularInline):
    """
    Shows all homework records generated from an assignment
    directly on the Assignment admin page.
    """
    model = Homework
    fk_name = "assignment"
    extra = 0
    readonly_fields = ["student", "status", "completed_at", "xp_reward"]
    fields = ["student", "status", "xp_reward", "completed_at"]
    verbose_name = "Student Homework Record"
    verbose_name_plural = "Student Homework Records"


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """Admin view for class-wide assignments."""
    list_display  = ["title", "subject", "due", "class_id", "created_by", "status"]
    list_filter   = ["status", "subject", "due"]
    search_fields = ["title", "created_by__full_name", "class_id"]
    ordering      = ["due"]
    readonly_fields = ["id", "created_at"]
    inlines       = [HomeworkInline]

    fieldsets = (
        ("Assignment Details", {
            "fields": ("id", "title", "subject", "due", "class_id", "status")
        }),
        ("Ownership", {
            "fields": ("created_by", "created_at")
        }),
    )


@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    """Admin view for individual student homework items."""
    list_display  = [
        "student", "title", "subject",
        "due", "status", "xp_reward", "completed_at",
    ]
    list_filter   = ["status", "subject", "due"]
    search_fields = [
        "student__full_name", "student__soma_id",
        "title", "assigned_by__full_name",
    ]
    ordering      = ["due"]
    readonly_fields = ["id", "created_at", "completed_at"]

    fieldsets = (
        ("Homework Details", {
            "fields": ("id", "title", "subject", "due", "xp_reward")
        }),
        ("Assignment", {
            "fields": ("assignment", "student", "assigned_by")
        }),
        ("Status", {
            "fields": ("status", "completed_at", "created_at")
        }),
    )
