import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from TelegramBot.bot import bot, dp

try:
    from aiogram.exceptions import TelegramNetworkError
except ImportError:
    TelegramNetworkError = Exception  # fallback

class Command(BaseCommand):
    help = 'Запуск Telegram-бота'

    def handle(self, *args, **options):
        if bot is None:
            self.stdout.write(
                self.style.ERROR(
                    'TELEGRAM_BOT_TOKEN не задан. Добавьте в .env: TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather'
                )
            )
            return
        self.stdout.write(self.style.SUCCESS('Запуск Telegram-бота...'))
        proxy = getattr(settings, 'TELEGRAM_BOT_PROXY', None)
        if proxy:
            self.stdout.write(self.style.WARNING(f'Используется прокси: {proxy[:50]}{"..." if len(proxy) > 50 else ""}'))
        try:
            asyncio.run(_run_polling())
        except TelegramNetworkError as e:
            self.stdout.write(
                self.style.ERROR(
                    'Не удалось подключиться к Telegram (api.telegram.org).\n'
                    'Причина: нет доступа к серверам Telegram с этой сети.\n\n'
                    'Что сделать:\n'
                    '  • Включите VPN или смените сеть (например, мобильный интернет).\n'
                    '  • Либо задайте прокси в .env: TELEGRAM_BOT_PROXY=http://... или socks5://...\n\n'
                    f'Технически: {e}'
                )
            )
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.WARNING('Бот остановлен.'))


async def _run_polling():
    """Проверка связи с Telegram с повторами, затем запуск polling."""
    max_attempts = 3
    delay = 5
    for attempt in range(1, max_attempts + 1):
        try:
            await bot.get_me()
            break
        except TelegramNetworkError:
            if attempt < max_attempts:
                await asyncio.sleep(delay)
            else:
                raise
    await dp.start_polling(bot)
