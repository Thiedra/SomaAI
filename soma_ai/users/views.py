"""
users/views.py
API views for authentication, profile management,
and teacher-student enrollment.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsTeacher
from .models import User, ClassEnrollment
from .serializers import (
    RegisterSerializer, LoginSerializer, UserProfileSerializer,
    ChangePasswordSerializer, EnrollStudentSerializer, StudentSummarySerializer,
)


class RegisterView(APIView):
    """Public — register a new student or teacher account."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new account",
        description="Create a student or teacher account. No authentication required.",
        tags=["Auth"],
        request=RegisterSerializer,
        responses={
            201: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error — check field values"),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserProfileSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Public — login and receive JWT access and refresh tokens."""
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login",
        description="Submit email and password to receive JWT tokens.",
        tags=["Auth"],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="JWT access and refresh tokens"),
            400: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response({
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": UserProfileSerializer(user).data,
        })


class MeView(APIView):
    """Authenticated — view or update own profile."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get my profile",
        description="Returns the currently authenticated user's profile.",
        tags=["Auth"],
        responses={200: UserProfileSerializer},
    )
    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    @extend_schema(
        summary="Update my profile",
        description="Update profile fields. Email and role cannot be changed.",
        tags=["Auth"],
        request=UserProfileSerializer,
        responses={
            200: UserProfileSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """Authenticated — change account password."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password",
        description="Provide current password and a new password to update.",
        tags=["Auth"],
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password updated successfully"),
            400: OpenApiResponse(description="Current password is incorrect"),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Password updated successfully."})


class UserDetailView(APIView):
    """Authenticated — get any user's profile by UUID."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get user by ID",
        description=(
            "Returns a user profile by UUID. "
            "Teachers can view their enrolled students. "
            "Students can view their own profile or their teacher's profile."
        ),
        tags=["Auth"],
        responses={
            200: UserProfileSerializer,
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def get(self, request, user_id):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # users can always view their own profile
        if request.user.id == target.id:
            return Response(UserProfileSerializer(target).data)

        # teachers can view their enrolled students
        if request.user.is_teacher:
            is_enrolled = ClassEnrollment.objects.filter(
                teacher=request.user, student=target
            ).exists()
            if is_enrolled:
                return Response(UserProfileSerializer(target).data)

        # students can view their enrolled teacher's profile
        if request.user.is_student:
            is_enrolled = ClassEnrollment.objects.filter(
                teacher=target, student=request.user
            ).exists()
            if is_enrolled:
                return Response(StudentSummarySerializer(target).data)

        return Response(
            {"error": "You do not have permission to view this profile."},
            status=status.HTTP_403_FORBIDDEN,
        )


class EnrollStudentView(APIView):
    """Teacher only — enroll a student by their email address."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Enroll a student",
        description="Teacher enrolls a student into their class using the student's email.",
        tags=["Auth"],
        request=EnrollStudentSerializer,
        responses={
            201: OpenApiResponse(description="Student enrolled successfully"),
            400: OpenApiResponse(description="Student not found or already enrolled"),
            403: OpenApiResponse(description="Only teachers can enroll students"),
        },
    )
    def post(self, request):
        serializer = EnrollStudentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        student = serializer.context["student"]

        _, created = ClassEnrollment.objects.get_or_create(
            teacher=request.user, student=student
        )

        if not created:
            return Response(
                {"detail": f"{student.full_name} is already enrolled in your class."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": f"{student.full_name} has been enrolled successfully."},
            status=status.HTTP_201_CREATED,
        )


class MyStudentsView(APIView):
    """Teacher only — list all enrolled students."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List my students",
        description="Returns all students enrolled in the authenticated teacher's class.",
        tags=["Auth"],
        responses={
            200: StudentSummarySerializer(many=True),
            403: OpenApiResponse(description="Only teachers can access this"),
        },
    )
    def get(self, request):
        students = User.objects.filter(
            enrolled_teachers__teacher=request.user
        )
        return Response(StudentSummarySerializer(students, many=True).data)


class StudentDetailView(APIView):
    """Teacher only — get full profile of a specific enrolled student."""
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get enrolled student by ID",
        description="Returns full profile of a student enrolled in the teacher's class.",
        tags=["Auth"],
        responses={
            200: StudentSummarySerializer,
            403: OpenApiResponse(description="Student not enrolled in your class"),
            404: OpenApiResponse(description="Student not found"),
        },
    )
    def get(self, request, user_id):
        is_enrolled = ClassEnrollment.objects.filter(
            teacher=request.user, student__id=user_id
        ).exists()

        if not is_enrolled:
            return Response(
                {"error": "This student is not enrolled in your class."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            student = User.objects.get(id=user_id, role=User.Role.STUDENT)
        except User.DoesNotExist:
            return Response(
                {"error": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(StudentSummarySerializer(student).data)
