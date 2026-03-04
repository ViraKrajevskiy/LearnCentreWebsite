from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    import phonenumbers
    def normalize_phone_e164(raw):
        raw = (raw or '').strip()
        if not raw:
            return raw
        if not raw.startswith('+'):
            raw = '+' + raw
        try:
            parsed = phonenumbers.parse(raw, None)
            if not phonenumbers.is_valid_number(parsed):
                return None
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            return None
except ImportError:
    def normalize_phone_e164(raw):
        raw = (raw or '').strip().replace(' ', '').replace('-', '')
        if not raw.startswith('+'):
            raw = '+' + raw
        return raw if raw and raw != '+' else None


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
        normalized = normalize_phone_e164(value)
        if not normalized:
            raise serializers.ValidationError('Введите корректный номер телефона (например +7 999 123-45-67).')
        if User.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError('Пользователь с таким номером уже зарегистрирован.')
        return normalized

    def create(self, validated_data):
        validated_data['role'] = 'guest'
        validated_data['email'] = f"{validated_data['phone_number']}@learncentre.local"
        user = User.objects.create_user(**validated_data)
        user.is_active = False
        user.save()
        return user

class OTPVerifySerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    code = serializers.CharField(max_length=6)


class LoginSerializer(serializers.Serializer):
    """Логин по телефону и паролю."""
    phone_number = serializers.CharField(help_text='Номер телефона')
    password = serializers.CharField(write_only=True, help_text='Пароль')
    login_type = serializers.ChoiceField(
        choices=[('student', 'Студент'), ('staff', 'Сотрудник')],
        required=False,
        default='student',
        help_text='student — вход для студентов, staff — для сотрудников (учителя, менторы, персонал)'
    )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Неверный текущий пароль.')
        return value


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'surname', 'last_name', 'phone_number', 'telegram_username', 'role', 'created_at']
        read_only_fields = fields


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Редактирование профиля: email, телефон, Telegram username, имя, фамилия."""
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=50)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'surname', 'last_name', 'phone_number', 'telegram_username']

    def validate_email(self, value):
        value = (value or '').strip().lower()
        if not value:
            raise serializers.ValidationError('Email не может быть пустым.')
        if User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('Этот email уже занят.')
        return value

    def validate_phone_number(self, value):
        normalized = normalize_phone_e164(value)
        if not normalized:
            raise serializers.ValidationError('Введите корректный номер телефона (например +7 999 123-45-67).')
        if User.objects.filter(phone_number=normalized).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('Этот номер уже занят.')
        return normalized

    def validate_telegram_username(self, value):
        if value is None:
            return ''
        value = (value or '').strip().lstrip('@')
        return value[:100] if value else ''