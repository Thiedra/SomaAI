"""
quizzes/tasks.py
Celery task for async AI quiz generation from a simplified note.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_quiz_task(self, quiz_id: str, question_count: int = 5):
    """
    Celery task: generate quiz questions using Cohere AI.
    Saves QuizQuestion objects to the database on success.

    Args:
        quiz_id: UUID string of the Quiz to populate with questions.
        question_count: Number of questions to generate (5-10).
    """
    from .models import Quiz, QuizQuestion
    from services.ai.cohere_service import CohereService

    try:
        quiz = Quiz.objects.select_related(
            "source_note__simplified_version", "student"
        ).get(id=quiz_id)

        # get simplified text — quizzes are generated from the simplified version
        try:
            simplified_text = quiz.source_note.simplified_version.simplified_text
        except Exception:
            raise ValueError(
                f"Note {quiz.source_note.id} has not been simplified yet."
            )

        prompt = f"""
Generate exactly {question_count} multiple-choice questions in {quiz.language} from the text below.
Return ONLY valid JSON:
{{"questions": [{{
    "question_text": "...",
    "option_a": "...",
    "option_b": "...",
    "option_c": "...",
    "option_d": "...",
    "correct_answer": "a",
    "answer_explanation": "..."
}}]}}

Text: {simplified_text}
"""
        service = CohereService()
        result = service.call(prompt, max_tokens=3000, feature="quizzes")

        # delete any existing questions before saving new ones
        quiz.questions.all().delete()

        # save each question returned by Cohere
        questions = result.get("questions", [])
        for q in questions:
            QuizQuestion.objects.create(
                quiz=quiz,
                question_text=q["question_text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_answer=q["correct_answer"],
                answer_explanation=q.get("answer_explanation", ""),
            )

        logger.info(f"Quiz {quiz_id} generated {len(questions)} questions.")

    except Exception as exc:
        logger.error(f"generate_quiz_task failed for {quiz_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
