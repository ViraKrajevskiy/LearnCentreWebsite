from django.utils import timezone
from datetime import timedelta
import uuid
from django.db import models

class UserOTP(models.Model):
    identifier = models.CharField(max_length=255, db_index=True)
    code = models.CharField(max_length=6)

    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, help_text='Telegram chat_id для отправки уведомления об успехе')

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'OTP код'
        verbose_name_plural = 'OTP коды'
        indexes = [
            models.Index(fields=['identifier', 'code', 'is_used']),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at and self.attempts < 5