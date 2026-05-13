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

from core.permissions import IsTeacher, IsStudent
from .models import User, ClassEnrollment
from .serializers import (
    RegisterSerializer, LoginSerializer,
    StudentProfileSerializer, TeacherProfileSerializer,
    UserProfileSerializer, ChangePasswordSerializer,
    EnrollStudentSerializer, StudentSummarySerializer,
    StudentStatsUpdateSerializer,
)


def _profile_serializer(user):
    """Return the correct profile serializer based on role."""
    if user.is_student:
        return StudentProfileSerializer(user).data
    return TeacherProfileSerializer(user).data


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new account",
        description=(
            "Create a student or teacher account. "
            "soma_id is auto-generated and returned in the response. "
            "school must be one of the 20 Rwandan schools."
        ),
        tags=["Auth"],
        request=RegisterSerializer,
        responses={
            201: OpenApiResponse(description="Account created — returns soma_id and profile"),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "user": _profile_serializer(user),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login",
        description=(
            "Login with soma_id + school + password + role. "
            "Returns JWT tokens and the full user profile. "
            "Updates the student's login streak automatically."
        ),
        tags=["Auth"],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="JWT tokens + user profile"),
            400: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # update streak on every login
        user.update_streak()
        user.save(update_fields=["streak", "last_login_date"])

        refresh = RefreshToken.for_user(user)
        return Response({
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": _profile_serializer(user),
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout",
        description="Blacklist the refresh token to invalidate the session.",
        tags=["Auth"],
        responses={
            200: OpenApiResponse(description="Logged out successfully"),
            400: OpenApiResponse(description="Invalid or missing refresh token"),
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": "refresh_token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except Exception:
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get my profile",
        description="Returns the full profile for the authenticated user (student or teacher).",
        tags=["Auth"],
        responses={200: OpenApiResponse(description="Student or Teacher profile object")},
    )
    def get(self, request):
        return Response(_profile_serializer(request.user))

    @extend_schema(
        summary="Update my profile",
        description="Update profile fields like school, grade, language, dyslexia flag.",
        tags=["Auth"],
        request=UserProfileSerializer,
        responses={
            200: OpenApiResponse(description="Updated profile"),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(_profile_serializer(request.user))


class StudentStatsUpdateView(APIView):
    """
    PUT /api/v1/auth/me/stats/
    Frontend calls this to sync XP, streak, level, badges after activity.
    Level is always recalculated server-side from XP — never trusted from client.
    """
    permission_classes = [IsStudent]

    @extend_schema(
        summary="Update student gamification stats",
        description=(
            "Update xp, streak, level, weak_subject, badges. "
            "Level is recalculated server-side from XP."
        ),
        tags=["Auth"],
        request=StudentStatsUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Updated student profile"),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def put(self, request):
        serializer = StudentStatsUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(StudentProfileSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password",
        tags=["Auth"],
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password updated"),
            400: OpenApiResponse(description="Current password incorrect"),
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
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get user by ID",
        tags=["Auth"],
        responses={
            200: OpenApiResponse(description="User profile"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def get(self, request, user_id):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.user.id == target.id:
            return Response(_profile_serializer(target))

        if request.user.is_teacher:
            if ClassEnrollment.objects.filter(teacher=request.user, student=target).exists():
                return Response(_profile_serializer(target))

        if request.user.is_student:
            if ClassEnrollment.objects.filter(teacher=target, student=request.user).exists():
                return Response(TeacherProfileSerializer(target).data)

        return Response(
            {"error": "You do not have permission to view this profile."},
            status=status.HTTP_403_FORBIDDEN,
        )


class EnrollStudentView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Enroll a student",
        description="Teacher enrolls a student by soma_id or email.",
        tags=["Auth"],
        request=EnrollStudentSerializer,
        responses={
            201: OpenApiResponse(description="Student enrolled"),
            400: OpenApiResponse(description="Already enrolled or not found"),
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
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="List my students",
        tags=["Auth"],
        responses={200: StudentSummarySerializer(many=True)},
    )
    def get(self, request):
        students = User.objects.filter(enrolled_teachers__teacher=request.user)
        return Response(StudentSummarySerializer(students, many=True).data)


class StudentDetailView(APIView):
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Get enrolled student by ID",
        tags=["Auth"],
        responses={
            200: StudentSummarySerializer,
            404: OpenApiResponse(description="Not found or not enrolled"),
        },
    )
    def get(self, request, user_id):
        if not ClassEnrollment.objects.filter(
            teacher=request.user, student__id=user_id
        ).exists():
            return Response(
                {"error": "This student is not enrolled in your class."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            student = User.objects.get(id=user_id, role=User.Role.STUDENT)
        except User.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(StudentSummarySerializer(student).data)
