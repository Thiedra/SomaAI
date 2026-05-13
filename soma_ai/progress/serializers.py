"""
progress/serializers.py
"""
from rest_framework import serializers
from .models import SubjectMastery, StudySession, WeeklyProgressSnapshot, TeacherAlert


class SubjectMasterySerializer(serializers.ModelSerializer):
    """
    Matches frontend Mastery shape exactly:
    { studentId, subject, value }
    """
    studentId = serializers.CharField(source="student_id", read_only=True)

    class Meta:
        model = SubjectMastery
        fields = ["studentId", "subject", "value"]
        read_only_fields = fields


class WeeklyProgressFrontendSerializer(serializers.ModelSerializer):
    """
    Matches frontend ProgressData shape exactly:
    { studentId, week, math, english, science }
    week is formatted as W1, W2, ... relative to the student's first snapshot.
    """
    studentId = serializers.CharField(source="student_id", read_only=True)
    week = serializers.SerializerMethodField()
    math = serializers.FloatField(source="math_score")
    english = serializers.FloatField(source="english_score")
    science = serializers.FloatField(source="science_score")

    class Meta:
        model = WeeklyProgressSnapshot
        fields = ["studentId", "week", "math", "english", "science"]

    def get_week(self, obj):
        """Return W1, W2, ... based on position in the queryset."""
        index = self.context.get("index", 0)
        return f"W{index + 1}"


class ProgressSnapshotSerializer(serializers.ModelSerializer):
    """Full snapshot — used internally and for teacher reports."""
    class Meta:
        model = WeeklyProgressSnapshot
        fields = [
            "id", "week_start_date", "average_quiz_score",
            "total_study_minutes", "notes_created_count", "quizzes_completed_count",
            "math_score", "english_score", "science_score",
            "kinyarwanda_score", "social_score",
        ]
        read_only_fields = fields


class StudySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudySession
        fields = ["id", "session_date", "duration_minutes", "activity_type"]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = TeacherAlert
        fields = ["id", "alert_type", "message", "is_read", "created_at", "student_name"]
        read_only_fields = ["id", "alert_type", "message", "created_at", "student_name"]


class ProgressSummarySerializer(serializers.Serializer):
    """Overall summary — used by GET /progress/me/"""
    total_quizzes = serializers.IntegerField()
    avg_quiz_score = serializers.FloatField()
    total_study_minutes = serializers.IntegerField()
    total_notes = serializers.IntegerField()
    last_study_date = serializers.DateField(allow_null=True)
    current_streak_days = serializers.IntegerField()
