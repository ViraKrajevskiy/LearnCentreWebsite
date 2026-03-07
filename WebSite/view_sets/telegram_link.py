"""
API для получения ссылки привязки Telegram после входа на сайте.
Только для авторизованных пользователей.
"""
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from WebSite.models.telegram_link import TelegramLinkToken, LINK_TOKEN_EXPIRE_MINUTES


class TelegramLinkView(APIView):
    """
    POST (с JWT): создаёт одноразовый токен и возвращает ссылку на бота.
    Пользователь переходит по ссылке в Telegram — бот привязывает chat_id к аккаунту.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        record = TelegramLinkToken.create_for_user(user)
        bot_name = (getattr(settings, 'TELEGRAM_BOT_USERNAME', '') or '').strip().lstrip('@')
        if not bot_name:
            return Response(
                {'error': 'Бот не настроен.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        link = f"https://t.me/{bot_name}?start=link_{record.token}"
        return Response({
            'bot_link': link,
            'expires_minutes': LINK_TOKEN_EXPIRE_MINUTES,
        }, status=status.HTTP_201_CREATED)
