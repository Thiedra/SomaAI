"""
progress/alert_urls.py
Separate URL file for alert endpoints under /api/v1/alerts/.
"""
from django.urls import path
from .views import AlertListView, AlertMarkReadView

urlpatterns = [
    path("", AlertListView.as_view(), name="alert-list"),
    path("<uuid:alert_id>/read/", AlertMarkReadView.as_view(), name="alert-read"),
]
