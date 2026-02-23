import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from WebSite.models.opt_model import UserOTP
from WebSite.serializers.otp_register.otp_registration import RegistrationSerializer, OTPVerifySerializer

User = get_user_model()


class RegisterView(APIView):
    @extend_schema(
        tags=['Регистрация и Авторизация'],
        summary="Шаг 1: Регистрация и получение ссылки на бота",
        description="Принимает данные юзера. Возвращает session_id и ссылку-deep_link на Telegram бота.",
        request=RegistrationSerializer,
        responses={
            201: inline_serializer(
                name='RegisterSuccessResponse',
                fields={
                    'message': serializers.CharField(),
                    'session_id': serializers.UUIDField(),
                    'bot_link': serializers.URLField(),
                }
            ),
            400: OpenApiResponse(description='Ошибка валидации (например, номер уже занят)'),
        }
    )
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            code = str(random.randint(100000, 999999))

            otp_record = UserOTP.objects.create(
                identifier=user.phone_number,
                code=code
            )

            bot_link = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={otp_record.session_id}"

            return Response({
                "message": "Пользователь создан. Перейдите в Telegram-бота для получения кода.",
                "session_id": otp_record.session_id,
                "bot_link": bot_link
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    @extend_schema(
        tags=['Регистрация и Авторизация'],
        summary="Шаг 2: Подтверждение OTP кода из бота",
        description="Принимает session_id и 6-значный код. Если код верный, активирует аккаунт и выдает JWT токены (access/refresh).",
        request=OTPVerifySerializer,
        responses={
            200: inline_serializer(
                name='VerifyOTPSuccessResponse',
                fields={
                    'message': serializers.CharField(),
                    'access': serializers.CharField(),
                    'refresh': serializers.CharField(),
                }
            ),
            400: OpenApiResponse(description='Неверный код или сессия истекла'),
            404: OpenApiResponse(description='Сессия не найдена'),
        }
    )

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data['session_id']
            code = serializer.validated_data['code']

            try:
                otp = UserOTP.objects.get(session_id=session_id)
            except UserOTP.DoesNotExist:
                return Response({"error": "Сессия не найдена"}, status=status.HTTP_404_NOT_FOUND)

            if not otp.is_valid:
                return Response({"error": "Код истек или уже использован"}, status=status.HTTP_400_BAD_REQUEST)

            if otp.code != code:
                otp.attempts += 1
                otp.save()
                return Response({"error": "Неверный код"}, status=status.HTTP_400_BAD_REQUEST)

            otp.is_used = True
            otp.save()

            try:
                user = User.objects.get(phone_number=otp.identifier)
                user.is_active = True
                user.save()

                refresh = RefreshToken.for_user(user)
                return Response({
                    "message": "Регистрация успешно завершена",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)