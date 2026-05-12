"""
planner/serializers.py
Serializers for study plan creation, exam dates, and daily slot management.
"""
from rest_framework import serializers
from .models import StudyPlan, ExamDate, DailySlot


class ExamDateSerializer(serializers.ModelSerializer):
    """Serializes a single exam date entry."""
    class Meta:
        model = ExamDate
        fields = ["id", "subject", "exam_date", "priority"]
        read_only_fields = ["id"]


class DailySlotSerializer(serializers.ModelSerializer):
    """Serializes a daily study slot."""
    class Meta:
        model = DailySlot
        fields = [
            "id", "date", "start_time", "end_time",
            "subject", "goal", "is_completed", "is_ai_adjusted",
        ]
        read_only_fields = ["id", "is_ai_adjusted"]


class StudyPlanSerializer(serializers.ModelSerializer):
    """
    Serializes a full study plan including exam dates and slots.
    Used for reading plan details.
    """
    exam_dates = ExamDateSerializer(many=True, read_only=True)
    slots = DailySlotSerializer(many=True, read_only=True)

    class Meta:
        model = StudyPlan
        fields = ["id", "is_active", "created_at", "exam_dates", "slots"]
        read_only_fields = ["id", "is_active", "created_at"]


class CreateStudyPlanSerializer(serializers.Serializer):
    """
    Input serializer for creating a new study plan.
    Accepts exam dates and study preferences to pass to the AI.
    """
    exam_dates = ExamDateSerializer(many=True)
    hours_per_day = serializers.FloatField(
        min_value=0.5, max_value=12.0, default=2.0
    )
    weak_subjects = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )

    def validate_exam_dates(self, value):
        """At least one exam date must be provided."""
        if not value:
            raise serializers.ValidationError("At least one exam date is required.")
        return value
