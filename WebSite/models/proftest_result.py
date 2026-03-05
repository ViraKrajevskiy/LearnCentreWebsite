from django.conf import settings
from django.db import models

from WebSite.models.models import DateCreate


class TestResult(DateCreate):
    """Результат профориентационного теста, привязанный к пользователю."""
    PROFILE_CHOICES = [
        ('ai_business', 'AI для бизнеса'),
        ('design_content', 'Контент и дизайн'),
        ('python_ml', 'Python и машинное обучение'),
        ('analytics', 'Аналитика и данные'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='proftest_results',
    )
    profile_id = models.CharField(
        max_length=32,
        choices=PROFILE_CHOICES,
        db_index=True,
    )
    # Опционально: сохранить сырые баллы для аналитики
    scores_json = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Результат профтеста'
        verbose_name_plural = 'Результаты профтестов'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.profile_id} ({self.created_at.date()})"
