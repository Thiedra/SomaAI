"""
career/tasks.py
Celery task for async AI career matching based on student answers.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_career_paths_task(self, assessment_id: str):
    """
    Celery task: generate 3 ranked career paths using Cohere AI.
    Deletes old recommendations and saves new ones on success.

    Args:
        assessment_id: UUID string of the CareerAssessment to process.
    """
    from .models import CareerAssessment, CareerRecommendation
    from services.ai.cohere_service import CohereService

    try:
        assessment = CareerAssessment.objects.select_related("student").get(
            id=assessment_id
        )
        student = assessment.student

        answers_text = "\n".join(
            f"- {qid}: {answer}"
            for qid, answer in assessment.question_answers.items()
        )

        prompt = f"""
You are a career counselor helping an African student choose a career path.
The student is from Rwanda/Africa.

Student profile:
- Preferred language: {student.preferred_language}
- Learning style: {student.learning_style or "not specified"}
- Has dyslexia: {student.is_dyslexic}

Student answers to career assessment:
{answers_text}

Based on these answers, recommend exactly 3 ranked career paths suitable for this student.
Include local African universities where they can study.

Return ONLY valid JSON:
{{
  "careers": [
    {{
      "rank": 1,
      "career_title": "...",
      "career_description": "...",
      "required_subjects": ["...", "..."],
      "african_universities": [
        {{"name": "...", "location": "...", "duration_years": 4}}
      ],
      "match_score": 92.5
    }}
  ]
}}
"""
        service = CohereService()
        result = service.call(prompt, max_tokens=2000, feature="career")

        # delete old recommendations before saving new ones
        CareerRecommendation.objects.filter(assessment=assessment).delete()

        for career in result.get("careers", []):
            CareerRecommendation.objects.create(
                assessment=assessment,
                career_title=career["career_title"],
                career_description=career["career_description"],
                required_subjects=career.get("required_subjects", []),
                african_universities=career.get("african_universities", []),
                match_score=career.get("match_score", 0.0),
                rank=career["rank"],
            )

        logger.info(f"Career paths generated for {student.full_name}")

    except Exception as exc:
        logger.error(f"generate_career_paths_task failed for {assessment_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
