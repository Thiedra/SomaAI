"""
homework/views.py

API views for the Homework and Assignment features.

Student endpoints:
  GET  /api/v1/homework/                  — list all homework for the student
  PUT  /api/v1/homework/<id>/complete/    — mark a homework item as done
                                            awards XP to the student

Teacher endpoints:
  GET    /api/v1/assignments/             — list all assignments created by the teacher
  POST   /api/v1/assignments/             — create an assignment and distribute
                                            homework to all enrolled students
  DELETE /api/v1/assignments/<id>/        — delete an assignment and all linked homework
  PUT    /api/v1/assignments/<id>/submit/ — manually mark a student's submission
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsStudent, IsTeacher
from users.models import User, ClassEnrollment
from .models import Homework, Assignment
from .serializers import (
    HomeworkSerializer,
    AssignmentSerializer,
    AssignmentCreateSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# Student endpoints
# ─────────────────────────────────────────────────────────────────────────────

class HomeworkListView(APIView):
    """
    GET /api/v1/homework/

    Returns all homework items assigned to the authenticated student,
    ordered by due date (soonest first).

    The frontend previously showed an empty state here because the
    HOMEWORK array was hardcoded as []. This endpoint populates it.
    """
    permission_classes = [IsStudent]

    @extend_schema(
        summary="List my homework",
        description=(
            "Returns all homework assigned to the authenticated student, "
            "ordered by due date. Includes both pending and completed items."
        ),
        tags=["Homework"],
        responses={200: HomeworkSerializer(many=True)},
    )
    def get(self, request):
        homework = Homework.objects.filter(student=request.user)
        return Response(HomeworkSerializer(homework, many=True).data)


class HomeworkCompleteView(APIView):
    """
    PUT /api/v1/homework/<id>/complete/

    Marks a homework item as completed and awards the configured XP
    to the student. The XP is added to the student's total and the
    level is recalculated server-side.

    Returns { done: true } as specified by the frontend contract.
    """
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Mark homework as complete",
        description=(
            "Marks a homework item as done and awards XP to the student. "
            "Returns { done: true } on success."
        ),
        tags=["Homework"],
        responses={
            200: OpenApiResponse(description="{ done: true }"),
            400: OpenApiResponse(description="Homework already completed"),
            404: OpenApiResponse(description="Homework not found"),
        },
    )
    def put(self, request, homework_id):
        try:
            homework = Homework.objects.get(
                id=homework_id,
                student=request.user,
            )
        except Homework.DoesNotExist:
            return Response(
                {"error": "Homework not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if homework.status == Homework.Status.COMPLETED:
            return Response(
                {"error": "This homework has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # mark as done and record the completion timestamp
        homework.status = Homework.Status.COMPLETED
        homework.completed_at = timezone.now()
        homework.save(update_fields=["status", "completed_at"])

        # award XP to the student and recalculate their level
        student = request.user
        student.xp += homework.xp_reward
        student.update_level()
        student.save(update_fields=["xp", "level"])

        return Response({"done": True})


# ─────────────────────────────────────────────────────────────────────────────
# Teacher endpoints
# ─────────────────────────────────────────────────────────────────────────────

class AssignmentListCreateView(APIView):
    """
    GET  /api/v1/assignments/  — list all assignments created by the teacher.
    POST /api/v1/assignments/  — create a new assignment and distribute
                                  homework to every enrolled student.

    On POST, the view:
      1. Creates the Assignment record.
      2. Fetches all students enrolled under the teacher.
      3. Creates one Homework record per student linked to the assignment.
    This ensures the student's GET /homework/ endpoint is immediately populated.
    """
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List my assignments",
        description="Returns all assignments created by the authenticated teacher.",
        tags=["Assignments"],
        responses={200: AssignmentSerializer(many=True)},
    )
    def get(self, request):
        assignments = Assignment.objects.filter(
            created_by=request.user
        ).prefetch_related("homework_items")
        return Response(AssignmentSerializer(assignments, many=True).data)

    @extend_schema(
        summary="Create an assignment",
        description=(
            "Creates a new assignment and automatically generates a Homework "
            "record for every student enrolled in the teacher's class."
        ),
        tags=["Assignments"],
        request=AssignmentCreateSerializer,
        responses={
            201: AssignmentSerializer,
            400: OpenApiResponse(description="Validation error — check field values"),
        },
    )
    def post(self, request):
        serializer = AssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # create the assignment record
        assignment = Assignment.objects.create(
            title=data["title"],
            subject=data["subject"],
            due=data["due"],
            class_id=data["classId"],
            created_by=request.user,
        )

        # distribute homework to every enrolled student
        enrolled_students = User.objects.filter(
            enrolled_teachers__teacher=request.user,
            role="student",
        )

        homework_records = [
            Homework(
                assignment=assignment,
                student=student,
                assigned_by=request.user,
                title=assignment.title,
                subject=assignment.subject,
                due=assignment.due,
                xp_reward=50,   # default XP per frontend spec
            )
            for student in enrolled_students
        ]

        # bulk_create for efficiency — avoids N individual INSERT queries
        Homework.objects.bulk_create(homework_records)

        return Response(
            AssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class AssignmentDeleteView(APIView):
    """
    DELETE /api/v1/assignments/<id>/

    Permanently deletes an assignment and all linked Homework records
    (via CASCADE). Only the teacher who created the assignment can delete it.
    """
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Delete an assignment",
        description=(
            "Permanently deletes an assignment and all associated homework records. "
            "Only the teacher who created the assignment can delete it."
        ),
        tags=["Assignments"],
        responses={
            200: OpenApiResponse(description="{ success: true }"),
            403: OpenApiResponse(description="You did not create this assignment"),
            404: OpenApiResponse(description="Assignment not found"),
        },
    )
    def delete(self, request, assignment_id):
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # only the creating teacher can delete their own assignments
        if assignment.created_by != request.user:
            return Response(
                {"error": "You do not have permission to delete this assignment."},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment.delete()
        return Response({"success": True})


class AssignmentSubmitView(APIView):
    """
    
    Marks a specific student's homework as submitted/completed on behalf
    of the teacher. Used when a teacher manually records a student's
    offline submission.

    Request body: { studentId: "<uuid>" }
    """
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Submit assignment for a student",
        description=(
            "Marks a student's homework as completed for this assignment. "
            "Used when recording offline or manual submissions."
        ),
        tags=["Assignments"],
        responses={
            200: OpenApiResponse(description="{ success: true }"),
            404: OpenApiResponse(description="Assignment or homework record not found"),
        },
    )
    def put(self, request, assignment_id):
        student_id = request.data.get("studentId")

        if not student_id:
            return Response(
                {"error": "studentId is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assignment = Assignment.objects.get(
                id=assignment_id,
                created_by=request.user,
            )
        except Assignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            homework = Homework.objects.get(
                assignment=assignment,
                student__id=student_id,
            )
        except Homework.DoesNotExist:
            return Response(
                {"error": "No homework record found for this student."},
                status=status.HTTP_404_NOT_FOUND,
            )

        homework.status = Homework.Status.COMPLETED
        homework.completed_at = timezone.now()
        homework.save(update_fields=["status", "completed_at"])

        return Response({"success": True})
