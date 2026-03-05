from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import EmailValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from WebSite.models.managers import CustomUserManager

class DateCreate(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractBaseUser, PermissionsMixin, DateCreate):
    ROLE_CHOICES = [
        ('guest', 'Guest'),
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('mentor', 'Mentor'),
        ('staff', 'Help centre worker'),
    ]

    email = models.EmailField(
        unique=True,
        db_index=True,
        validators=[EmailValidator(message="Введите корректный email адрес.")]
    )
    surname = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    phone_number = PhoneNumberField(unique=True, db_index=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, db_index=True, help_text='Telegram chat_id для бота')
    birth_date = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')
    proftest_offer_shown_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Когда впервые показали предложение пройти профтест в профиле (один раз при первом входе)',
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'surname', 'phone_number']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']

    @property
    def proftest_passed(self):
        """True, если пользователь хотя бы раз проходил профтест (есть запись в TestResult)."""
        return self.proftest_results.exists()

    @property
    def proftest_latest_profile_id(self):
        """ID направления по последнему профтесту или None (использует prefetch при наличии)."""
        results = list(self.proftest_results.all())
        if not results:
            return None
        latest = max(results, key=lambda r: r.created_at)
        return latest.profile_id

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"