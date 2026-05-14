"""
homework/apps.py

App configuration for the Homework and Assignment feature.
"""
from django.apps import AppConfig


class HomeworkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "homework"
    verbose_name = "Homework & Assignments"
