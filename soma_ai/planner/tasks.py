"""
planner/tasks.py
Celery tasks for AI study schedule generation and auto-adjustment of missed slots.
"""
import json
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_plan_task(self, plan_id: str, hours_per_day: float, weak_subjects: list):
    """
    Celery task: generate daily study blocks using Cohere AI.
    Saves DailyStudyBlock objects to the database on success.

    Args:
        plan_id: UUID string of the StudyPlan to populate.
        hours_per_day: How many hours the student wants to study per day.
        weak_subjects: List of subjects the student struggles with.
    """
    from .models import StudyPlan, DailyStudyBlock, UpcomingExam
    from services.ai.cohere_service import CohereService

    try:
        plan = StudyPlan.objects.select_related("student").get(id=plan_id)
        student = plan.student

        # build exam dates JSON for the prompt
        exam_dates = UpcomingExam.objects.filter(study_plan=plan)
        exam_dates_json = json.dumps([
            {
                "subject": e.subject_name,
                "exam_date": str(e.exam_date),
                "priority": e.priority_level,
            }
            for e in exam_dates
        ])

        today = timezone.now().date()
        learning_style = student.learning_style or "general"

        prompt = f"""
Build a study schedule.
Exam dates: {exam_dates_json}
Weak subjects: {weak_subjects}
Study hours per day: {hours_per_day}
Learning style: {learning_style}
Today: {today}

Rules:
- Prioritise nearest exams and weak subjects
- No Sundays
- Each slot has a specific study goal
- Maximum slot length is 45 minutes then a 10-minute break
Return ONLY valid JSON:
{{"slots": [{{"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", "subject": "...", "goal": "..."}}]}}
"""
        service = CohereService()
        result = service.call(prompt, max_tokens=4000, feature="planner")

        # delete existing blocks before saving new ones
        plan.daily_blocks.all().delete()

        # save each block returned by Cohere
        slots_data = result.get("slots", [])
        for slot in slots_data:
            DailyStudyBlock.objects.create(
                study_plan=plan,
                scheduled_date=slot["date"],
                start_time=slot["start_time"],
                end_time=slot["end_time"],
                subject_name=slot["subject"],
                study_goal=slot["goal"],
            )

        logger.info(f"Plan {plan_id} generated {len(slots_data)} blocks.")

    except Exception as exc:
        logger.error(f"generate_plan_task failed for {plan_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def auto_adjust_missed_slots():
    """
    Celery beat task — runs daily.
    Finds all active plans with missed incomplete blocks
    and regenerates the forward schedule using AI.
    """
    from .models import StudyPlan, DailyStudyBlock

    today = timezone.now().date()

    active_plans = StudyPlan.objects.filter(is_active=True)

    for plan in active_plans:
        missed = DailyStudyBlock.objects.filter(
            study_plan=plan,
            scheduled_date__lt=today,
            is_completed=False,
        )

        if not missed.exists():
            continue

        # check if any upcoming exams still exist
        exam_dates = plan.upcoming_exams.filter(exam_date__gte=today)
        if not exam_dates.exists():
            continue

        # mark future blocks as ai rescheduled before regenerating
        DailyStudyBlock.objects.filter(
            study_plan=plan,
            scheduled_date__gte=today,
        ).update(was_rescheduled_by_ai=True)

        # get weak subjects from missed blocks
        weak_subjects = list(
            missed.values_list("subject_name", flat=True).distinct()
        )

        generate_plan_task.delay(
            str(plan.id),
            hours_per_day=2.0,
            weak_subjects=weak_subjects,
        )
        logger.info(f"Auto-adjusting plan {plan.id} for {plan.student.full_name}")
