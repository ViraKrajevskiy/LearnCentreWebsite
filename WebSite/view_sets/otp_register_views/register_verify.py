import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, login
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers

from WebSite.models.opt_model import UserOTP
from WebSite.models.student_model.student import Student
from WebSite.utils.telegram import send_telegram_message
from WebSite.serializers.otp_register.otp_registration import (
    RegistrationSerializer, OTPVerifySerializer, LoginSerializer,
    ProfileSerializer, ChangePasswordSerializer, UpdateProfileSerializer
)

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
                if otp.telegram_chat_id:
                    user.telegram_chat_id = otp.telegram_chat_id
                user.save()

                if otp.telegram_chat_id:
                    send_telegram_message(
                        otp.telegram_chat_id,
                        "✅ <b>Регистрация успешно завершена!</b>\n\n"
                        "Ваш аккаунт активирован. Теперь вы можете войти на сайт.",
                    )

                Student.objects.get_or_create(user=user, defaults={'course': None})
                login(request, user)
                refresh = RefreshToken.for_user(user)
                return Response({
                    "message": "Регистрация успешно завершена",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    @extend_schema(
        tags=['Регистрация и Авторизация'],
        summary='Логин',
        description='Вход по номеру телефона и паролю. Возвращает JWT токены.',
        request=LoginSerializer,
        responses={
            200: inline_serializer(
                name='LoginSuccessResponse',
                fields={
                    'message': serializers.CharField(),
                    'access': serializers.CharField(),
                    'refresh': serializers.CharField(),
                }
            ),
            400: OpenApiResponse(description='Неверный номер или пароль'),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response({"error": "Неверный номер телефона или пароль"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return Response({"error": "Неверный номер телефона или пароль"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({"error": "Аккаунт не активирован. Завершите регистрацию через OTP."}, status=status.HTTP_400_BAD_REQUEST)

        login_type = serializer.validated_data.get('login_type', 'student')
        staff_roles = ['teacher', 'mentor', 'staff']
        if login_type == 'staff' and user.role not in staff_roles:
            return Response(
                {"error": "Вход для сотрудников. Ваш аккаунт не имеет прав доступа."},
                status=status.HTTP_403_FORBIDDEN
            )
        if login_type == 'student' and user.role in staff_roles:
            return Response(
                {"error": "Вход для студентов. Сотрудникам — используйте страницу входа для персонала."},
                status=status.HTTP_403_FORBIDDEN
            )

        if login_type == 'student':
            Student.objects.get_or_create(user=user, defaults={'course': None})
        login(request, user)
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Вход выполнен",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)


class ProfileView(APIView):
    """Просмотр и обновление своих данных (по JWT)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Регистрация и Авторизация'],
        summary='Мой профиль',
        description='Возвращает данные текущего пользователя. Требует Bearer токен.',
        responses={200: ProfileSerializer},
    )
    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        tags=['Регистрация и Авторизация'],
        summary='Обновить профиль',
        description='Изменить email, телефон, Telegram, имя, фамилию. Требует Bearer токен.',
        request=UpdateProfileSerializer,
        responses={200: ProfileSerializer, 400: OpenApiResponse(description='Ошибка валидации')},
    )
    def put(self, request):
        serializer = UpdateProfileSerializer(instance=request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ProfileSerializer(request.user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    patch = put


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Регистрация и Авторизация'],
        summary='Смена пароля',
        description='Требует Bearer токен. Старый и новый пароль.',
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description='Пароль успешно изменён')},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({"message": "Пароль успешно изменён"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)