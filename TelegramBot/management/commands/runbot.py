import asyncio
from django.core.management.base import BaseCommand
from TelegramBot.bot import bot, dp

class Command(BaseCommand):
    help = 'Запуск Telegram-бота'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Запуск Telegram-бота...'))
        try:
            asyncio.run(dp.start_polling(bot))
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.WARNING('Бот остановлен.'))
