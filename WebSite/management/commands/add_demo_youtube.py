"""
Проставляет демо-видео YouTube всем подурокам (по кругу из списка).
Запуск: python manage.py add_demo_youtube
Удобно, если данные уже созданы и нужно просто добавить видосики всем объектам.
"""
from django.core.management.base import BaseCommand
from WebSite.models.study.lesson import SubLesson


# Ролик с разрешённым встраиванием (музыка/часть популярных дают "Video unavailable")
DEMO_YOUTUBE_URLS = [
    'https://www.youtube.com/watch?v=jNQXAC9IVRw',  # Me at the zoo — всегда разрешает embed
]


class Command(BaseCommand):
    help = 'Проставляет демо-видео YouTube всем подурокам'

    def handle(self, *args, **options):
        subs = list(SubLesson.objects.order_by('id'))
        if not subs:
            self.stdout.write(self.style.WARNING('Нет ни одного подурока. Запустите: python manage.py populate_models'))
            return
        for i, sub in enumerate(subs):
            sub.content_link = DEMO_YOUTUBE_URLS[i % len(DEMO_YOUTUBE_URLS)]
            sub.save()
        self.stdout.write(self.style.SUCCESS(f'Обновлено подуроков: {len(subs)}. У всех проставлены демо-видео YouTube.'))
