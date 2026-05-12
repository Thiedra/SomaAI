"""
quizzes/serializers.py
Serializers for quiz generation, question display, attempt submission, and results.
"""
from rest_framework import serializers
from .models import Quiz, QuizQuestion, QuizSubmission


class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializes a question for display.
    correct_answer is excluded — never sent to the student during the quiz.
    """
    class Meta:
        model = QuizQuestion
        fields = ["id", "question_text", "option_a", "option_b", "option_c", "option_d"]


class QuestionResultSerializer(serializers.ModelSerializer):
    """
    Serializes a question including the correct answer and explanation.
    Used only in the results endpoint after the attempt is submitted.
    """
    class Meta:
        model = QuizQuestion
        fields = [
            "id", "question_text",
            "option_a", "option_b", "option_c", "option_d",
            "correct_answer", "answer_explanation",
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Serializes a quiz with its questions (without answers)."""
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "source_note", "language", "created_at", "questions"]
        read_only_fields = ["id", "created_at", "questions"]


class GenerateQuizSerializer(serializers.Serializer):
    """
    Input serializer for quiz generation.
    Accepts a note_id and optional question count (5-10).
    """
    note_id = serializers.UUIDField()
    question_count = serializers.IntegerField(min_value=5, max_value=10, default=5)


class AttemptSubmitSerializer(serializers.Serializer):
    """
    Input serializer for submitting quiz answers.
    answers must be a dict mapping question UUID strings to option letters.
    """
    answers = serializers.DictField(
        child=serializers.ChoiceField(choices=["a", "b", "c", "d"])
    )
    duration_seconds = serializers.IntegerField(min_value=0, default=0)


class QuizSubmissionSerializer(serializers.ModelSerializer):
    """Serializes a completed quiz submission with score."""
    class Meta:
        model = QuizSubmission
        fields = ["id", "score_percentage", "submitted_answers", "duration_seconds", "submitted_at"]
        read_only_fields = fields


class QuizResultSerializer(serializers.ModelSerializer):
    """Full results serializer — includes questions with correct answers."""
    questions = QuestionResultSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "language", "created_at", "questions"]
