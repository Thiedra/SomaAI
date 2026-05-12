"""
dashboard/serializers.py
Serializers for teacher dashboard overview, student list, and struggling student detection.
"""
from rest_framework import serializers


class StudentOverviewSerializer(serializers.Serializer):
    """
    Summary stats for a single student shown in the teacher dashboard.
    Includes activity, scores, and struggling flag.
    """
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.CharField()
    avg_score_last_7_days = serializers.FloatField()
    total_study_minutes = serializers.IntegerField()
    last_study_date = serializers.DateField(allow_null=True)
    quizzes_completed = serializers.IntegerField()
    is_struggling = serializers.BooleanField()
    # reasons why the student is flagged as struggling
    struggling_reasons = serializers.ListField(
        child=serializers.CharField(), required=False
    )


class DashboardOverviewSerializer(serializers.Serializer):
    """
    Aggregated stats across ALL of the teacher's linked students.
    Shown at the top of the teacher dashboard.
    """
    total_students = serializers.IntegerField()
    struggling_students_count = serializers.IntegerField()
    avg_class_score = serializers.FloatField()
    total_alerts_unread = serializers.IntegerField()
    most_active_student = serializers.CharField(allow_null=True)
    least_active_student = serializers.CharField(allow_null=True)
