"""
dashboard/apps.py
App configuration for the teacher dashboard.
"""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
