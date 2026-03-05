"""
Сохранение результата профтеста: создание пользователя по email+пароль и запись TestResult.
Для авторизованных: сохранение результата в свой профиль (без повторного ввода email/пароля).
"""
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from WebSite.models import TestResult

User = get_user_model()

VALID_PROFILE_IDS = {'ai_business', 'design_content', 'python_ml', 'analytics'}


def _generate_unique_phone():
    """Генерирует уникальный номер в формате +7999XXXXXXX для регистрации после профтеста."""
    for _ in range(50):
        suffix = str(random.randint(1000000, 9999999))
        phone = f"+7999{suffix}"
        if not User.objects.filter(phone_number=phone).exists():
            return phone
    raise ValueError("Не удалось сгенерировать уникальный телефон")


class ProftestSaveView(APIView):
    """POST: email, password, profile_id → создаёт пользователя и записывает результат теста."""

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password')
        profile_id = (request.data.get('profile_id') or '').strip()
        scores_json = request.data.get('scores_json')

        if not email:
            return Response(
                {'error': 'Укажите email.', 'field': 'email'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not password:
            return Response(
                {'error': 'Укажите пароль.', 'field': 'password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if profile_id not in VALID_PROFILE_IDS:
            return Response(
                {'error': 'Некорректный результат теста.', 'field': 'profile_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {'error': 'Этот email уже зарегистрирован. Войдите в аккаунт.', 'field': 'email'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(password)
        except DjangoValidationError as e:
            return Response(
                {'error': e.messages[0] if e.messages else 'Пароль слишком простой.', 'field': 'password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            phone = _generate_unique_phone()
        except ValueError:
            return Response(
                {'error': 'Попробуйте позже.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name='Участник',
            surname='Профтест',
            phone_number=phone,
            role='guest',
        )
        user.is_active = True
        user.save()

        TestResult.objects.create(
            user=user,
            profile_id=profile_id,
            scores_json=scores_json,
        )

        return Response(
            {
                'message': 'Результат сохранён! Рекомендации по курсам доступны в личном кабинете.',
                'email': user.email,
            },
            status=status.HTTP_201_CREATED
        )


class ProftestSaveToProfileView(APIView):
    """POST: для авторизованного пользователя — сохранить результат профтеста в свой профиль (без email/пароля)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile_id = (request.data.get('profile_id') or '').strip()
        scores_json = request.data.get('scores_json')

        if profile_id not in VALID_PROFILE_IDS:
            return Response(
                {'error': 'Некорректный результат теста.', 'field': 'profile_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        TestResult.objects.create(
            user=request.user,
            profile_id=profile_id,
            scores_json=scores_json,
        )

        return Response(
            {'message': 'Результат сохранён в ваш профиль.'},
            status=status.HTTP_201_CREATED
        )
