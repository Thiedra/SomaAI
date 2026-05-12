"""
users/models.py
User account model for Soma AI.
Uses email as the login field. Supports student and teacher roles.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    Handles creation of regular users and superusers.
    """

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with a hashed password."""
        if not email:
            raise ValueError("Email address is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with full admin access."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Main user account for Soma AI.

    Two roles are supported:
      - student: accesses learning features (notes, quizzes, planner)
      - teacher: monitors students via the dashboard and receives alerts

    Key accessibility fields:
      - is_dyslexic: enables dyslexia-friendly AI simplification
      - learning_style: personalises AI-generated content
      - preferred_language: all AI responses are returned in this language
    """

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"

    class Language(models.TextChoices):
        KINYARWANDA = "kinyarwanda", "Kinyarwanda"
        ENGLISH = "english", "English"
        FRENCH = "french", "French"
        SWAHILI = "swahili", "Swahili"

    class LearningStyle(models.TextChoices):
        VISUAL = "visual", "Visual"          # learns best through images/diagrams
        AUDITORY = "auditory", "Auditory"    # learns best through listening
        READING = "reading", "Reading"       # learns best through reading/writing
        KINESTHETIC = "kinesthetic", "Kinesthetic"  # learns best through doing

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email Address",
        help_text="Used as the login identifier",
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Full Name",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="Account Role",
    )
    preferred_language = models.CharField(
        max_length=20,
        choices=Language.choices,
        default=Language.ENGLISH,
        verbose_name="Preferred Language",
        help_text="Language used for AI-generated content",
    )
    learning_style = models.CharField(
        max_length=20,
        choices=LearningStyle.choices,
        null=True,
        blank=True,
        verbose_name="Learning Style",
        help_text="Set during onboarding — personalises AI content",
    )
    is_dyslexic = models.BooleanField(
        default=False,
        verbose_name="Has Dyslexia",
        help_text="Enables dyslexia-friendly simplification and larger fonts",
    )
    is_premium = models.BooleanField(
        default=False,
        verbose_name="Premium Account",
        help_text="Unlocks AI quizzes and career guidance features",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date Joined",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    @property
    def is_teacher(self):
        """Convenience property to check teacher role."""
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        """Convenience property to check student role."""
        return self.role == self.Role.STUDENT


class ClassEnrollment(models.Model):
    """
    Records a teacher-student connection.

    When a teacher links a student, a ClassEnrollment record is created.
    This controls which students a teacher can monitor on their dashboard.
    A student can be enrolled under multiple teachers.
    """
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrolled_students",
        limit_choices_to={"role": "teacher"},
        verbose_name="Teacher",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrolled_teachers",
        limit_choices_to={"role": "student"},
        verbose_name="Student",
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Enrolled At",
    )

    class Meta:
        verbose_name = "Class Enrollment"
        verbose_name_plural = "Class Enrollments"
        unique_together = ("teacher", "student")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.full_name} enrolled under {self.teacher.full_name}"
