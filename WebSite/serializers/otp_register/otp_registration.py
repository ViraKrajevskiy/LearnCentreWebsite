# WebSite/api/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=50, help_text='Имя')
    surname = serializers.CharField(max_length=50, help_text='Фамилия')
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    phone_number = serializers.CharField(help_text='Номер телефона')
    telegram_username = serializers.CharField(max_length=100, help_text='Тег Telegram (без @)')

    class Meta:
        model = User
        fields = ['first_name', 'surname', 'last_name', 'phone_number', 'telegram_username', 'password']

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Пользователь с таким номером уже зарегистрирован.')
        return value

    def create(self, validated_data):
        validated_data['role'] = 'guest'
        # Генерируем фейковый email для совместимости
        validated_data['email'] = f"{validated_data['phone_number']}@learncentre.local"
        user = User.objects.create_user(**validated_data)
        user.is_active = False # Ждем подтверждения OTP
        user.save()
        return user

class OTPVerifySerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    code = serializers.CharField(max_length=6)