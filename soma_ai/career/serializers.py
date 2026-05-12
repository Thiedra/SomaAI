"""
career/serializers.py
Serializers for career questions, answer submission, and career path results.
"""
from rest_framework import serializers
from .models import CareerAssessment, CareerRecommendation
from .constants import REQUIRED_QUESTION_IDS


class CareerQuestionSerializer(serializers.Serializer):
    """Read-only serializer for the 8 hardcoded career questions."""
    id = serializers.CharField()
    text = serializers.CharField()


class CareerAnswerSerializer(serializers.Serializer):
    """
    Input serializer for submitting career assessment answers.
    All 8 questions must be answered — partial submissions are rejected.
    """
    answers = serializers.DictField(child=serializers.CharField())

    def validate_answers(self, value):
        """Ensure all 8 required question IDs are present."""
        missing = REQUIRED_QUESTION_IDS - set(value.keys())
        if missing:
            raise serializers.ValidationError(
                f"Missing answers for questions: {sorted(missing)}"
            )
        return value


class CareerRecommendationSerializer(serializers.ModelSerializer):
    """Serializes a single career recommendation."""
    class Meta:
        model = CareerRecommendation
        fields = [
            "id", "career_title", "career_description",
            "required_subjects", "african_universities",
            "match_score", "rank",
        ]
        read_only_fields = fields


class CareerAssessmentSerializer(serializers.ModelSerializer):
    """
    Serializes a student's career assessment including all 3 ranked recommendations.
    """
    recommendations = CareerRecommendationSerializer(many=True, read_only=True)

    class Meta:
        model = CareerAssessment
        fields = ["id", "question_answers", "created_at", "updated_at", "recommendations"]
        read_only_fields = ["id", "created_at", "updated_at", "recommendations"]
