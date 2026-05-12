"""
planner/tasks.py
Celery tasks for AI study schedule generation and auto-adjustment of missed slots.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_plan_task(self, plan_id: str, hours_per_day: float, weak_subjects: list):
    """
    Celery task: generate daily study slots using Claude AI.
    Saves DailySlot objects to the database on success.

    Args:
        plan_id: UUID string of the StudyPlan to populate.
        hours_per_day: How many hours the student wants to study per day.
        weak_subjects: List of subjects the student struggles with.
    """
    from .models import StudyPlan, DailySlot, ExamDate
    from simplifier.services.ai.claude_service import ClaudeService


    import json

    try:
        plan = StudyPlan.objects.select_related("student").get(id=plan_id)
        student = plan.student

        # build exam dates JSON for the prompt
        exam_dates = ExamDate.objects.filter(plan=plan)
        exam_dates_json = json.dumps([
            {
                "subject": e.subject,
                "exam_date": str(e.exam_date),
                "priority": e.priority,
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
        service = ClaudeService()
        result = service.call(prompt, max_tokens=4000, feature="planner")

        # delete existing slots before saving new ones
        plan.slots.all().delete()

        # save each slot returned by Claude
        slots_data = result.get("slots", [])
        for slot in slots_data:
            DailySlot.objects.create(
                plan=plan,
                date=slot["date"],
                start_time=slot["start_time"],
                end_time=slot["end_time"],
                subject=slot["subject"],
                goal=slot["goal"],
            )

        logger.info(f"Plan {plan_id} generated {len(slots_data)} slots.")

    except Exception as exc:
        logger.error(f"generate_plan_task failed for {plan_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def auto_adjust_missed_slots():
    """
    Celery beat task — runs daily.
    Finds all active plans with missed (incomplete past) slots
    and regenerates the forward schedule using AI.
    """
    from .models import StudyPlan, DailySlot

    today = timezone.now().date()

    # get all active plans that have missed slots
    active_plans = StudyPlan.objects.filter(is_active=True)

    for plan in active_plans:
        missed = DailySlot.objects.filter(
            plan=plan,
            date__lt=today,         # past slots
            is_completed=False,     # not completed
        )

        if not missed.exists():
            continue  # no missed slots — nothing to adjust

        # get exam dates for this plan
        exam_dates = plan.exam_dates.filter(exam_date__gte=today)
        if not exam_dates.exists():
            continue  # all exams passed — no need to adjust

        # queue a new generation task for this plan
        # mark future slots as ai_adjusted before regenerating
        DailySlot.objects.filter(
            plan=plan, date__gte=today
        ).update(is_ai_adjusted=True)

        # get weak subjects from missed slots
        weak_subjects = list(
            missed.values_list("subject", flat=True).distinct()
        )

        generate_plan_task.delay(
            str(plan.id),
            hours_per_day=2.0,  # default — could be stored on the plan
            weak_subjects=weak_subjects,
        )
        logger.info(f"Auto-adjusting plan {plan.id} for {plan.student.full_name}")
