import asyncio
from django.core.management.base import BaseCommand
from TelegramBot.bot import bot, dp

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
        try:
            asyncio.run(dp.start_polling(bot))
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.WARNING('Бот остановлен.'))
