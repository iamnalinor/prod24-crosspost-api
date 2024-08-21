from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import openai


def request_ai(prompt: str) -> str:
    client = openai.Client(
        api_key=settings.AI_PROXY_API_KEY,
        base_url=settings.AI_PROXY_URL,
    )
    chat_completion = client.chat.completions.create(
        messages=[
            {
                'role': 'user',
                'content': prompt,
            }
        ],
        model=settings.AI_MODEL,
    )
    return chat_completion.choices[0].message.content


class AIRequestView(APIView):
    action = None

    def post(self, request, *args, **kwargs) -> Response:
        match self.action:
            case 'generate':
                master_prompt = settings.AI_MASTER_PROMPT
            case 'refactor':
                master_prompt = settings.AI_REFACTOR_PROMPT
            case _:
                raise ValueError(
                    'action must be either "generate" or "refactor"'
                )

        try:
            response = request_ai(
                master_prompt + request.data['text']
            )
        except openai.APIError as exc:
            return Response(
                {'response': exc.response}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response({'response': response}, status=status.HTTP_200_OK)
