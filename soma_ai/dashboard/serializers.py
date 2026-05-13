"""
dashboard/serializers.py
Serializers for teacher dashboard — aligned to frontend data shapes.
"""
from rest_framework import serializers


class ClassStudentSerializer(serializers.Serializer):
    """
    Matches frontend ClassStudent shape exactly:
    { id, name, grade, mastery, dyslexia, lastActive, risk }
    """
    id = serializers.UUIDField()
    name = serializers.CharField()
    grade = serializers.CharField()
    mastery = serializers.FloatField()
    dyslexia = serializers.BooleanField()
    lastActive = serializers.CharField()       # e.g. "2h ago", "1d ago"
    risk = serializers.ChoiceField(choices=["low", "medium", "high"])


class TeacherReportMasterySerializer(serializers.Serializer):
    """Single subject mastery entry for teacher reports."""
    studentId = serializers.CharField()
    subject = serializers.CharField()
    value = serializers.FloatField()


class TeacherReportProgressSerializer(serializers.Serializer):
    """Single weekly progress entry for teacher reports."""
    studentId = serializers.CharField()
    week = serializers.CharField()
    math = serializers.FloatField()
    english = serializers.FloatField()
    science = serializers.FloatField()


class TeacherReportSerializer(serializers.Serializer):
    """
    Matches frontend GET /api/teacher/reports shape:
    { mastery: Mastery[], progress: ProgressData[] }
    """
    mastery = TeacherReportMasterySerializer(many=True)
    progress = TeacherReportProgressSerializer(many=True)


class StudentOverviewSerializer(serializers.Serializer):
    """
    Internal dashboard stats per student — used by overview and struggling views.
    """
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.CharField()
    avg_score_last_7_days = serializers.FloatField()
    total_study_minutes = serializers.IntegerField()
    last_study_date = serializers.DateField(allow_null=True)
    quizzes_completed = serializers.IntegerField()
    is_struggling = serializers.BooleanField()
    struggling_reasons = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class DashboardOverviewSerializer(serializers.Serializer):
    """
    Aggregated class stats shown at the top of the teacher dashboard.
    """
    total_students = serializers.IntegerField()
    struggling_students_count = serializers.IntegerField()
    avg_class_score = serializers.FloatField()
    total_alerts_unread = serializers.IntegerField()
    most_active_student = serializers.CharField(allow_null=True)
    least_active_student = serializers.CharField(allow_null=True)
