"""
progress/serializers.py
Serializers for study sessions, progress snapshots, and teacher alerts.
"""
from rest_framework import serializers
from .models import StudySession, WeeklyProgressSnapshot, TeacherAlert


class StudySessionSerializer(serializers.ModelSerializer):
    """Serializes a single study session record."""
    class Meta:
        model = StudySession
        fields = ["id", "session_date", "duration_minutes", "activity_type"]
        read_only_fields = fields


class ProgressSnapshotSerializer(serializers.ModelSerializer):
    """Serializes a weekly progress snapshot for graph data."""
    class Meta:
        model = WeeklyProgressSnapshot
        fields = [
            "id", "week_start_date", "average_quiz_score",
            "total_study_minutes", "notes_created_count", "quizzes_completed_count",
        ]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):
    """
    Serializes an alert for the teacher's alert list.
    Includes student name for easy display.
    """
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = TeacherAlert
        fields = [
            "id", "alert_type", "message",
            "is_read", "created_at", "student_name",
        ]
        read_only_fields = ["id", "alert_type", "message", "created_at", "student_name"]


class ProgressSummarySerializer(serializers.Serializer):
    """
    Summary serializer for GET /progress/me/.
    Aggregates the student's overall stats in one response.
    """
    total_quizzes = serializers.IntegerField()
    avg_quiz_score = serializers.FloatField()
    total_study_minutes = serializers.IntegerField()
    total_notes = serializers.IntegerField()
    last_study_date = serializers.DateField(allow_null=True)
    current_streak_days = serializers.IntegerField()
