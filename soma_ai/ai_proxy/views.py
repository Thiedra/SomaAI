"""
ai_proxy/views.py
Secure server-side proxy for all AI features.
Uses CohereService from services/ai/cohere_service.py.
"""
import json
import logging
import re
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse

from services.ai.cohere_service import CohereService  # Updated import

logger = logging.getLogger(__name__)

# matches the system prompt in the frontend spec exactly
TUTOR_SYSTEM_PROMPT = (
    "You are Soma AI, an encouraging and patient school teacher. "
    "Your job is to answer student questions, provide clear helpful examples, "
    "and help kids have good grammar — especially those with dyslexia. "
    "Always positively and gently correct the student's grammar as your first "
    "sentence, then answer their question warmly with clear examples. "
    "Be supportive, empathetic, and keep your answers educational but concise."
)


def _sse_stream(prompt: str, chat_history: list):
    """
    Generator that wraps CohereService.stream() into SSE format.
    Each token is yielded as: data: {"text": "<token>"}\n\n
    Ends with: data: [DONE]\n\n
    """
    service = CohereService()  # Updated class
    try:
        for token in service.stream(
            prompt=prompt,
            system_prompt=TUTOR_SYSTEM_PROMPT,
            chat_history=chat_history,
        ):
            yield f"data: {json.dumps({'text': token})}\n\n"
    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


class AITutorView(APIView):
    """
    POST /api/v1/ai/tutor/
    Streams AI tutor response as SSE tokens.
    Body: { message, chatHistory: [{ role: "USER"|"CHATBOT", message }] }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="AI Tutor (streaming)",
        description="Streams tutor response via SSE. Body: { message, chatHistory }.",
        tags=["AI"],
        responses={200: OpenApiResponse(description="SSE stream — data: {text}")},
    )
    def post(self, request):
        message      = request.data.get("message", "").strip()
        chat_history = request.data.get("chatHistory", [])

        if not message:
            return Response(
                {"error": "message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = StreamingHttpResponse(
            _sse_stream(message, chat_history),
            content_type="text/event-stream",
        )
        response["Cache-Control"]     = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AISimplifyView(APIView):
    """
    POST /api/v1/ai/simplify/
    Simplifies text for a given grade and subject.
    Body: { text, grade, subject }  →  { simplified }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Simplify text",
        description="Body: { text, grade, subject }. Returns { simplified }.",
        tags=["AI"],
        responses={200: OpenApiResponse(description="{ simplified: string }")},
    )
    def post(self, request):
        text    = request.data.get("text", "").strip()
        grade   = request.data.get("grade", "P6")
        subject = request.data.get("subject", "General")

        if not text:
            return Response(
                {"error": "text is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        system_prompt = (
            "You are Soma AI, a patient and kind tutor for primary school students "
            "in Rwanda. Explain things in the simplest possible way using small words "
            "and clear examples. Be encouraging and gentle."
        )
        prompt = (
            f"Explain this text simply for a slow learner in Grade {grade} ({subject}):\n"
            f"\"{text}\""
        )

        try:
            service = CohereService()  # Updated class
            simplified = service.call_text(
                prompt=prompt,
                system_prompt=system_prompt,
                feature="simplify",
            )
            return Response({"simplified": simplified})
        except Exception as e:
            logger.error(f"Simplify failed: {e}")
            return Response(
                {"error": "Simplification failed. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class AIQuizStartView(APIView):
    """
    POST /api/v1/ai/quiz/start/
    Starts a 3-question AI quiz on a topic.
    Body: { topic, grade }  →  { firstQuestion }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Start AI quiz",
        description="Body: { topic, grade }. Returns { firstQuestion }.",
        tags=["AI"],
        responses={200: OpenApiResponse(description="{ firstQuestion: string }")},
    )
    def post(self, request):
        topic = request.data.get("topic", "").strip()
        grade = request.data.get("grade", "P6")

        if not topic:
            return Response(
                {"error": "topic is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prompt = (
            f"You are a friendly teacher. I want a 3-question quiz about '{topic}' "
            f"for a primary school student in Grade {grade}. "
            f"Ask the FIRST question now. Just the question, nothing else."
        )

        try:
            service = CohereService()  # Updated class
            first_question = service.call_text(prompt=prompt, feature="quiz")
            return Response({"firstQuestion": first_question})
        except Exception as e:
            logger.error(f"Quiz start failed: {e}")
            return Response(
                {"error": "Failed to start quiz. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class AIQuizAnswerView(APIView):
    """
    POST /api/v1/ai/quiz/answer/
    Continues a quiz after the student answers.
    Detects "QUIZ COMPLETE:" to signal the end and extracts score.
    Body: { topic, answer, questionNumber }  →  { feedback, nextQuestion, isComplete, score }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Answer AI quiz question",
        description="Body: { topic, answer, questionNumber }.",
        tags=["AI"],
        responses={200: OpenApiResponse(description="{ feedback, nextQuestion, isComplete, score }")},
    )
    def post(self, request):
        topic           = request.data.get("topic", "").strip()
        answer          = request.data.get("answer", "").strip()
        question_number = request.data.get("questionNumber", 1)

        if not topic or not answer:
            return Response(
                {"error": "topic and answer are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_last = question_number >= 3

        if is_last:
            prompt = (
                f"The student answered: '{answer}'. This was the LAST question "
                f"of our quiz on '{topic}'. Evaluate all their answers, tell them "
                f"their score out of 3, and give an encouraging summary. "
                f"Start your response with 'QUIZ COMPLETE: '"
            )
        else:
            prompt = (
                f"The student answered: '{answer}'. Tell them briefly if they got "
                f"it right or wrong in an encouraging way, then ask the NEXT "
                f"question for our quiz on '{topic}'."
            )

        try:
            service = CohereService()  # Updated class
            ai_response = service.call_text(prompt=prompt, feature="quiz")
        except Exception as e:
            logger.error(f"Quiz answer failed: {e}")
            return Response(
                {"error": "Failed to process answer. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        is_complete = "QUIZ COMPLETE:" in ai_response

        # extract score from "X/3" when quiz ends
        score = None
        if is_complete:
            match = re.search(r"(\d)/3", ai_response)
            score = int(match.group(1)) if match else 0

        return Response({
            "feedback":     ai_response,
            "nextQuestion": None if is_complete else ai_response,
            "isComplete":   is_complete,
            "score":        score,
        })


class AICareerView(APIView):
    """
    POST /api/v1/ai/career/
    Generates career encouragement for a student's recommended stream.
    Body: { answers, recommendedStream }  →  { advice }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get career advice",
        description="Body: { answers: string[], recommendedStream: string }.",
        tags=["AI"],
        responses={200: OpenApiResponse(description="{ advice: string }")},
    )
    def post(self, request):
        answers            = request.data.get("answers", [])
        recommended_stream = request.data.get("recommendedStream", "").strip()

        if not answers or not recommended_stream:
            return Response(
                {"error": "answers and recommendedStream are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prompt = (
            f"A primary school student picked these interests: {', '.join(answers)}. "
            f"I recommended the High School stream '{recommended_stream}'. "
            f"Give them a very encouraging 2-sentence explanation of why this path "
            f"fits them and one cool career they could have."
        )

        try:
            service = CohereService()  # Updated class
            advice = service.call_text(prompt=prompt, feature="career_proxy")
            return Response({"advice": advice})
        except Exception as e:
            logger.error(f"Career advice failed: {e}")
            return Response(
                {"error": "Failed to generate advice. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )