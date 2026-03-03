import asyncio
from django.core.management.base import BaseCommand
from TelegramBot.fucntions import bot
from TelegramBot.fucntions.bot import dp


class Command(BaseCommand):
    help = 'Запуск Telegram-бота (Long Polling)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Запуск Telegram-бота...'))
        try:
            asyncio.run(dp.start_polling(bot))
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.WARNING('Бот остановлен.'))