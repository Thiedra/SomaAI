"""
users/serializers.py
Serializers for registration, login, student profile, teacher profile,
and teacher-student enrollment.
"""
from django.utils import timezone
from rest_framework import serializers
from .models import User, ClassEnrollment
from .constants import RWANDAN_SCHOOLS


class RegisterSerializer(serializers.ModelSerializer):
    """
    Register a new student or teacher.
    soma_id is auto-generated — not provided by the client.
    school must be one of the 20 Rwandan schools.
    """
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "email", "full_name", "password", "role",
            "school", "grade", "class_grade",
            "preferred_language", "is_dyslexic", "learning_style",
        ]

    def validate_school(self, value):
        if value and value not in RWANDAN_SCHOOLS:
            raise serializers.ValidationError(
                "Please select a valid school from the list."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """
    Login with soma_id + school + password + role.
    Matches exactly what the frontend login form sends.
    Falls back to email login for admin/superuser access.
    """
    soma_id = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    school = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=["student", "teacher"])

    def validate(self, data):
        soma_id = data.get("soma_id", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password")
        role = data.get("role")
        school = data.get("school", "").strip()

        if not soma_id and not email:
            raise serializers.ValidationError(
                "Provide either soma_id or email to login."
            )

        # look up user by soma_id or email
        try:
            if soma_id:
                user = User.objects.get(soma_id=soma_id)
            else:
                user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        if user.role != role:
            raise serializers.ValidationError(
                f"This account is registered as '{user.role}', not '{role}'."
            )

        if soma_id and school and user.school and user.school != school:
            raise serializers.ValidationError(
                "School does not match this account."
            )

        data["user"] = user
        return data


class StudentProfileSerializer(serializers.ModelSerializer):
    """
    Full student profile — matches the frontend StudentObject shape exactly.
    Fields: id, name, grade, school, role, streak, xp, level,
            weakSubject, badges, dyslexia
    """
    name = serializers.CharField(source="full_name", read_only=True)
    weakSubject = serializers.CharField(source="weak_subject", read_only=True)
    dyslexia = serializers.BooleanField(source="is_dyslexic", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "soma_id", "name", "grade", "school", "role",
            "streak", "xp", "level", "weakSubject", "badges", "dyslexia",
            "preferred_language", "learning_style",
        ]
        read_only_fields = fields


class TeacherProfileSerializer(serializers.ModelSerializer):
    """
    Full teacher profile — matches the frontend TeacherObject shape exactly.
    Fields: id, name, school, role, classGrade, classSize
    """
    name = serializers.CharField(source="full_name", read_only=True)
    classGrade = serializers.CharField(source="class_grade", read_only=True)
    classSize = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "soma_id", "name", "school", "role",
            "classGrade", "classSize",
        ]
        read_only_fields = fields

    def get_classSize(self, obj):
        return obj.enrolled_students.count()


class StudentStatsUpdateSerializer(serializers.ModelSerializer):
    """
    Used by PUT /api/v1/auth/me/stats/ to update gamification fields.
    Frontend sends { streak, xp, level } after activity.
    """
    class Meta:
        model = User
        fields = ["xp", "streak", "level", "weak_subject", "badges"]

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        # always recalculate level from XP to prevent client manipulation
        instance.update_level()
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Generic profile serializer used for PATCH /me/ (update own profile).
    Returns role-appropriate data.
    """
    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role", "school", "grade",
            "class_grade", "preferred_language", "learning_style",
            "is_dyslexic", "is_premium", "date_joined",
        ]
        read_only_fields = ["id", "email", "role", "is_premium", "date_joined"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class EnrollStudentSerializer(serializers.Serializer):
    """Teacher enrolls a student by soma_id or email."""
    student_soma_id = serializers.CharField(required=False, allow_blank=True)
    student_email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, data):
        soma_id = data.get("student_soma_id", "").strip()
        email = data.get("student_email", "").strip()

        if not soma_id and not email:
            raise serializers.ValidationError(
                "Provide either student_soma_id or student_email."
            )
        try:
            if soma_id:
                student = User.objects.get(soma_id=soma_id, role=User.Role.STUDENT)
            else:
                student = User.objects.get(email=email, role=User.Role.STUDENT)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No student account found with those details."
            )
        self.context["student"] = student
        return data


class StudentSummarySerializer(serializers.ModelSerializer):
    """
    Used by teachers to see enrolled students list.
    Includes dyslexia flag needed for teacher dashboard.
    """
    name = serializers.CharField(source="full_name", read_only=True)
    dyslexia = serializers.BooleanField(source="is_dyslexic", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "soma_id", "name", "email", "grade", "school",
            "dyslexia", "preferred_language", "learning_style",
        ]
