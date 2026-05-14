import uuid
from django.db import models


class Video(models.Model):
    """
    A YouTube video resource for students.
    Frontend filters by ?subject= and ?level=
    The `youtube_id` is used to build the embed URL on the frontend.
    """

    SUBJECT_CHOICES = [
        ("Math", "Math"),
        ("English", "English"),
        ("Science", "Science"),
        ("Kinyarwanda", "Kinyarwanda"),
        ("Social", "Social"),
    ]
    LEVEL_CHOICES = [
        ("P1", "P1"), ("P2", "P2"), ("P3", "P3"),
        ("P4", "P4"), ("P5", "P5"), ("P6", "P6"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    youtube_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="YouTube video ID used to build the embed URL.",
    )
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    level = models.CharField(max_length=5, choices=LEVEL_CHOICES)
    duration = models.CharField(
        max_length=20,
        help_text="Human-readable duration, e.g. '9m'.",
    )
    teacher_recommended = models.BooleanField(
        default=False,
        help_text="Highlighted on the frontend when True.",
    )

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        ordering = ["-teacher_recommended", "title"]

    def __str__(self):
        return f"{self.title} ({self.level} — {self.subject})"


class Book(models.Model):
    """
    A PDF book from the Rwandan primary school curriculum.
    Frontend filters by ?grade=, ?type=, ?subject=
    `file_url` is the path to the PDF served from /media/ or a CDN.
    """

    GRADE_CHOICES = [
        ("P1", "P1"), ("P2", "P2"), ("P3", "P3"),
        ("P4", "P4"), ("P5", "P5"), ("P6", "P6"),
    ]

    TYPE_CHOICES = [
        ("PB", "Pupil Book"),
        ("TG", "Teacher's Guide"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file_url = models.CharField(
        max_length=500,
        help_text="URL path to the PDF file, e.g. /media/library/P6_Math_PB.pdf",
    )
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES)
    book_type = models.CharField(
        max_length=5,
        choices=TYPE_CHOICES,
        help_text="PB = Pupil Book, TG = Teacher's Guide.",
    )
    subject = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["grade", "subject", "book_type"]

    def __str__(self):
        return f"{self.title} ({self.grade} — {self.book_type})"
