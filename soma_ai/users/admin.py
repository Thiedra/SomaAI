"""
users/admin.py
Admin configuration for User and ClassEnrollment models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ClassEnrollment


class ClassEnrollmentInline(admin.TabularInline):
    """Show enrolled students directly on the teacher's admin page."""
    model = ClassEnrollment
    fk_name = "teacher"
    extra = 0
    readonly_fields = ["enrolled_at"]
    verbose_name = "Enrolled Student"
    verbose_name_plural = "Enrolled Students"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "full_name", "role", "preferred_language", "is_premium", "is_active"]
    list_filter = ["role", "preferred_language", "is_dyslexic", "is_premium", "is_active"]
    search_fields = ["email", "full_name"]
    readonly_fields = ["id", "date_joined"]
    inlines = [ClassEnrollmentInline]

    fieldsets = (
        ("Account", {"fields": ("id", "email", "password")}),
        ("Personal Info", {"fields": ("full_name", "role", "preferred_language")}),
        ("Learning Profile", {"fields": ("learning_style", "is_dyslexic", "is_premium")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("date_joined",)}),
    )
    add_fieldsets = (
        (None, {
            "fields": (
                "email", "full_name", "password1", "password2", "role",
            )
        }),
    )


@admin.register(ClassEnrollment)
class ClassEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "teacher", "enrolled_at"]
    list_filter = ["enrolled_at"]
    search_fields = ["teacher__email", "student__email", "teacher__full_name", "student__full_name"]
    readonly_fields = ["enrolled_at"]
