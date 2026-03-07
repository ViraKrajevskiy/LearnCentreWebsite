"""
Одноразовый токен для привязки Telegram к аккаунту после входа на сайте.
Пользователь после логина получает ссылку t.me/BOT?start=link_TOKEN;
бот по токену находит user и сохраняет chat_id.
"""
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone

LINK_TOKEN_EXPIRE_MINUTES = 15


class TelegramLinkToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telegram_link_tokens',
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Токен привязки Telegram'
        verbose_name_plural = 'Токены привязки Telegram'
        ordering = ['-created_at']

    @classmethod
    def create_for_user(cls, user):
        cls.objects.filter(user=user).delete()
        token = secrets.token_urlsafe(32)
        return cls.objects.create(user=user, token=token)

    @property
    def is_expired(self):
        delta = timezone.now() - self.created_at
        return delta.total_seconds() > LINK_TOKEN_EXPIRE_MINUTES * 60
