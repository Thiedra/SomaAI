"""
users/models.py
User account model for Soma AI.
"""
import uuid
import random
import string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from .constants import SCHOOL_CHOICES, GRADE_CHOICES


def generate_soma_id():
    """Generate a unique SOMA-XXXX-XXXX style ID."""
    part1 = "".join(random.choices(string.digits, k=4))
    part2 = "".join(random.choices(string.ascii_uppercase, k=4))
    return f"SOMA-{part1}-{part2}"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Main user account for Soma AI.
    Supports student and teacher roles.
    Students log in with soma_id + school + password.
    Teachers log in with soma_id + school + password.
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
        VISUAL = "visual", "Visual"
        AUDITORY = "auditory", "Auditory"
        READING = "reading", "Reading"
        KINESTHETIC = "kinesthetic", "Kinesthetic"

    # ── Core identity ─────────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    soma_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_soma_id,
        verbose_name="Soma ID",
        help_text="Auto-generated login ID in format SOMA-XXXX-XXXX",
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email Address",
    )
    full_name = models.CharField(max_length=255, verbose_name="Full Name")
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name="Account Role",
    )

    # ── School & grade ────────────────────────────────────────────────────────
    school = models.CharField(
        max_length=255,
        choices=SCHOOL_CHOICES,
        blank=True,
        default="",
        verbose_name="School",
        help_text="Selected from the list of Rwandan schools",
    )
    grade = models.CharField(
        max_length=5,
        choices=GRADE_CHOICES,
        blank=True,
        default="",
        verbose_name="Grade",
        help_text="Student grade: P1–P6",
    )

    # ── Teacher-specific ──────────────────────────────────────────────────────
    class_grade = models.CharField(
        max_length=5,
        choices=GRADE_CHOICES,
        blank=True,
        default="",
        verbose_name="Class Grade",
        help_text="The grade this teacher teaches, e.g. P6",
    )

    # ── Gamification (student) ────────────────────────────────────────────────
    xp = models.IntegerField(
        default=0,
        verbose_name="Experience Points",
        help_text="Earned through quizzes, homework, and activities",
    )
    level = models.IntegerField(
        default=1,
        verbose_name="Level",
        help_text="Calculated from XP — levels up every 2500 XP",
    )
    streak = models.IntegerField(
        default=0,
        verbose_name="Login Streak (days)",
        help_text="Consecutive days the student has logged in",
    )
    last_login_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Last Login Date",
        help_text="Used to calculate and reset the streak",
    )
    weak_subject = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Weak Subject",
        help_text="Subject needing most improvement — updated by progress tracking",
    )
    badges = models.JSONField(
        default=list,
        verbose_name="Badges",
        help_text='e.g. ["Reader Star", "Math Brave", "7-Day Streak"]',
    )

    # ── Accessibility & learning ──────────────────────────────────────────────
    preferred_language = models.CharField(
        max_length=20,
        choices=Language.choices,
        default=Language.ENGLISH,
        verbose_name="Preferred Language",
    )
    learning_style = models.CharField(
        max_length=20,
        choices=LearningStyle.choices,
        null=True,
        blank=True,
        verbose_name="Learning Style",
    )
    is_dyslexic = models.BooleanField(
        default=False,
        verbose_name="Has Dyslexia",
    )
    is_premium = models.BooleanField(default=False, verbose_name="Premium Account")

    # ── Django internals ──────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Date Joined")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.role}) — {self.soma_id}"

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    def update_level(self):
        """Recalculate level from current XP. Call after awarding XP."""
        from .constants import XP_PER_LEVEL
        self.level = max(1, self.xp // XP_PER_LEVEL + 1)

    def update_streak(self):
        """
        Call on every login.
        - If last login was yesterday → increment streak.
        - If last login was today → no change.
        - If last login was 2+ days ago → reset streak to 1.
        """
        from django.utils import timezone
        today = timezone.now().date()

        if self.last_login_date is None:
            self.streak = 1
        elif self.last_login_date == today:
            return  # already logged in today — no change
        elif (today - self.last_login_date).days == 1:
            self.streak += 1
        else:
            self.streak = 1  # missed a day — reset

        self.last_login_date = today


class ClassEnrollment(models.Model):
    """Records a teacher-student connection."""
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
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="Enrolled At")

    class Meta:
        verbose_name = "Class Enrollment"
        verbose_name_plural = "Class Enrollments"
        unique_together = ("teacher", "student")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.student.full_name} enrolled under {self.teacher.full_name}"
