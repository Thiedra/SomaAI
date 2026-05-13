"""
users/admin.py
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ClassEnrollment


class ClassEnrollmentInline(admin.TabularInline):
    model = ClassEnrollment
    fk_name = "teacher"
    extra = 0
    readonly_fields = ["enrolled_at"]
    verbose_name = "Enrolled Student"
    verbose_name_plural = "Enrolled Students"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = [
        "soma_id", "email", "full_name", "role",
        "school", "grade", "xp", "level", "streak", "is_active",
    ]
    list_filter = [
        "role", "school", "grade", "is_dyslexic", "is_premium", "is_active",
    ]
    search_fields = ["soma_id", "email", "full_name", "school"]
    readonly_fields = ["id", "soma_id", "date_joined", "last_login_date"]
    inlines = [ClassEnrollmentInline]

    fieldsets = (
        ("Account", {
            "fields": ("id", "soma_id", "email", "password")
        }),
        ("Personal Info", {
            "fields": ("full_name", "role", "school", "grade", "class_grade")
        }),
        ("Gamification", {
            "fields": ("xp", "level", "streak", "last_login_date", "weak_subject", "badges")
        }),
        ("Learning Profile", {
            "fields": ("preferred_language", "learning_style", "is_dyslexic", "is_premium")
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser")
        }),
        ("Dates", {
            "fields": ("date_joined",)
        }),
    )

    add_fieldsets = (
        (None, {
            "fields": (
                "email", "full_name", "password1", "password2",
                "role", "school", "grade",
            )
        }),
    )


@admin.register(ClassEnrollment)
class ClassEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "teacher", "enrolled_at"]
    list_filter = ["enrolled_at"]
    search_fields = [
        "teacher__soma_id", "student__soma_id",
        "teacher__full_name", "student__full_name",
    ]
    readonly_fields = ["enrolled_at"]
