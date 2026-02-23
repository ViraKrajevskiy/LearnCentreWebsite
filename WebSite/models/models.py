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
    birth_date = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'surname', 'phone_number']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"