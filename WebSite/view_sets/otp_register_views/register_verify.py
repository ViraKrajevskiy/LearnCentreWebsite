import random
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from WebSite.models.opt_model import UserOTP
from WebSite.serializers.otp_register.otp_registration import RegistrationSerializer, OTPVerifySerializer


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer

    @extend_schema(summary="1. Регистрация и запрос кода в Telegram")
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Генерируем код
        otp_code = str(random.randint(100000, 999999))
        otp_entry = UserOTP.objects.create(
            identifier=user.phone_number,  # Или email
            code=otp_code
        )

        # ТУТ ВЫЗОВ ФУНКЦИИ БОТА (отправка сообщения в телеграм)
        # send_telegram_otp(user.phone_number, otp_code) 

        return Response({
            "session_id": otp_entry.session_id,
            "message": "Код отправлен в Telegram бот"
        }, status=status.HTTP_201_CREATED)


class VerifyOTPView(generics.GenericAPIView):
    serializer_class = OTPVerifySerializer

    @extend_schema(summary="2. Подтверждение кода и активация аккаунта")
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data['session_id']
        code = serializer.validated_data['code']

        try:
            otp = UserOTP.objects.get(session_id=session_id, code=code)
            if not otp.is_valid:
                return Response({"error": "Код просрочен или неверный"}, status=400)

            # Активируем пользователя
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(phone_number=otp.identifier)
            user.is_active = True
            user.save()

            # Помечаем код как использованный
            otp.is_used = True
            otp.save()

            # Генерируем токены
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })

        except UserOTP.DoesNotExist:
            return Response({"error": "Неверная сессия или код"}, status=400)