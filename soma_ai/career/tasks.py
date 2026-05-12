"""
career/tasks.py
Celery task for async AI career matching based on student answers.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_career_paths_task(self, profile_id: str):
    """
    Celery task: generate 3 ranked career paths using Claude AI.
    Deletes old career paths and saves new ones on success.

    Args:
        profile_id: UUID string of the CareerProfile to process.
    """
    from .models import CareerProfile, CareerPath
    from simplifier.services.ai.claude_service import ClaudeService
    import json

    try:
        profile = CareerProfile.objects.select_related("student").get(id=profile_id)
        student = profile.student

        # format answers for the prompt
        answers_text = "\n".join(
            f"- {qid}: {answer}"
            for qid, answer in profile.answers.items()
        )

        prompt = f"""
You are a career counselor helping an African student choose a career path.
The student is from Rwanda/Africa.

Student profile:
- Language: {student.language}
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
      "title": "...",
      "description": "...",
      "required_subjects": ["...", "..."],
      "universities": [
        {{"name": "...", "location": "...", "duration_years": 4}}
      ],
      "match_score": 92.5
    }}
  ]
}}
"""
        service = ClaudeService()
        result = service.call(prompt, max_tokens=2000, feature="career")

        # delete old career paths before saving new ones
        CareerPath.objects.filter(profile=profile).delete()

        # save the 3 ranked career paths
        for career in result.get("careers", []):
            CareerPath.objects.create(
                profile=profile,
                title=career["title"],
                description=career["description"],
                required_subjects=career.get("required_subjects", []),
                universities=career.get("universities", []),
                match_score=career.get("match_score", 0.0),
                rank=career["rank"],
            )

        logger.info(f"Career paths generated for {student.full_name}")

    except Exception as exc:
        logger.error(f"generate_career_paths_task failed for {profile_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
