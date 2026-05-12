"""
users/serializers.py
Serializers for user registration, authentication, profile management,
and teacher-student enrollment.
"""
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User, ClassEnrollment


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles new user registration.
    Password is write-only and must be at least 8 characters.
    """
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "email", "full_name", "password", "role",
            "preferred_language", "is_dyslexic", "learning_style",
        ]

    def create(self, validated_data):
        """Use create_user to ensure password is hashed before saving."""
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials.
    Attaches the authenticated user to validated_data for use in the view.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")
        data["user"] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializes user profile for GET /me/ and PATCH /me/.
    Email and role are read-only after registration.
    """
    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role",
            "preferred_language", "learning_style",
            "is_dyslexic", "is_premium", "date_joined",
        ]
        read_only_fields = ["id", "email", "role", "is_premium", "date_joined"]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Validates password change requests.
    Verifies the current password before allowing a new one.
    """
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class EnrollStudentSerializer(serializers.Serializer):
    """
    Used by teachers to enroll a student by their email address.
    Validates that the email belongs to a student account.
    """
    student_email = serializers.EmailField()

    def validate_student_email(self, value):
        try:
            student = User.objects.get(email=value, role=User.Role.STUDENT)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No student account found with this email address."
            )
        self.context["student"] = student
        return value


class StudentSummarySerializer(serializers.ModelSerializer):
    """
    Read-only serializer for listing enrolled students.
    Used by teachers to view their class list.
    """
    class Meta:
        model = User
        fields = [
            "id", "email", "full_name",
            "preferred_language", "is_dyslexic", "learning_style",
        ]
