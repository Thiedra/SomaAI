"""
homework/serializers.py

Serializers for the Homework and Assignment endpoints.

HomeworkSerializer        — student-facing homework list (GET /homework/).
                            Maps xp_reward → xpReward to match frontend shape.

AssignmentSerializer      — teacher-facing assignment list.
                            Computes `count` from related homework records.

AssignmentCreateSerializer — input serializer for POST /assignments/.
                             Validates required fields before creation.
"""
from rest_framework import serializers
from .models import Homework, Assignment


class HomeworkSerializer(serializers.ModelSerializer):
    """
    Serializes a Homework record for the student dashboard.

    Frontend shape:
        { id, title, subject, due, status, xpReward }

    `xpReward` uses camelCase to match the frontend Homework type exactly.
    `student` and `assigned_by` are excluded — not needed by the frontend.
    """
    xpReward = serializers.IntegerField(
        source="xp_reward",
        read_only=True,
        help_text="XP awarded to the student on completion.",
    )

    class Meta:
        model = Homework
        fields = ["id", "title", "subject", "due", "status", "xpReward"]
        read_only_fields = ["id", "xpReward"]


class AssignmentSerializer(serializers.ModelSerializer):
    """
    Serializes an Assignment for the teacher dashboard.

    Frontend shape:
        { id, title, subject, due, classId, count, status }

    `count` is computed as the number of Homework records linked to
    this assignment — i.e. how many students were assigned this task.
    `classId` maps to the model's `class_id` field.
    """
    classId = serializers.CharField(
        source="class_id",
        read_only=True,
        help_text="The class this assignment targets (e.g. 'P6').",
    )
    count = serializers.SerializerMethodField(
        help_text="Number of students this assignment was distributed to.",
    )

    class Meta:
        model = Assignment
        fields = ["id", "title", "subject", "due", "classId", "count", "status"]
        read_only_fields = ["id", "count", "classId"]

    def get_count(self, obj):
        """Return the number of homework records generated from this assignment."""
        return obj.homework_items.count()


class AssignmentCreateSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/v1/assignments/.

    Accepts the four fields the frontend sends when a teacher creates
    an assignment. The `created_by` field is injected server-side from
    request.user — the client never sends it.
    """
    title    = serializers.CharField(max_length=255)
    subject  = serializers.CharField(max_length=100)
    due      = serializers.DateField(
        help_text="Due date in YYYY-MM-DD format.",
    )
    classId  = serializers.CharField(
        max_length=50,
        help_text="Target class identifier, e.g. 'P6'.",
    )
