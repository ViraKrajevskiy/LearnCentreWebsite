"""
Создаёт уведомления «Урок через 30 мин» и «Урок начался» для студентов групп.
Запуск по крону каждые 10–15 мин: python manage.py create_lesson_notifications
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

from WebSite.models.study.lesson import Lesson
from WebSite.models.notifications import Notification


class Command(BaseCommand):
    help = 'Создаёт уведомления об уроках (через 30 мин и начался)'

    def handle(self, *args, **options):
        now = timezone.now()
        soon_begin = now + timedelta(minutes=25)
        soon_end = now + timedelta(minutes=35)   # окно «через ~30 мин»
        started_begin = now - timedelta(minutes=10)

        created_soon = 0
        created_started = 0

        # Уроки через ~30 мин
        for lesson in Lesson.objects.filter(
            scheduled_at__gte=soon_begin,
            scheduled_at__lte=soon_end,
        ).select_related('group', 'course'):
            link = reverse('lesson_detail', args=[lesson.id])
            title = f'Через 30 мин: {lesson.title}'
            for student in lesson.group.students.all():
                if Notification.objects.filter(
                    student=student,
                    lesson=lesson,
                    kind=Notification.KIND_LESSON_SOON,
                ).exists():
                    continue
                Notification.objects.create(
                    student=student,
                    kind=Notification.KIND_LESSON_SOON,
                    title=title,
                    message=f'Курс: {lesson.course.title}. Группа: {lesson.group.name}',
                    link=link,
                    lesson=lesson,
                )
                created_soon += 1

        # Уроки, которые только что начались (в последние 10 мин)
        for lesson in Lesson.objects.filter(
            scheduled_at__gte=started_begin,
            scheduled_at__lte=now,
        ).select_related('group', 'course'):
            link = reverse('lesson_detail', args=[lesson.id])
            title = f'Начался урок: {lesson.title}'
            for student in lesson.group.students.all():
                if Notification.objects.filter(
                    student=student,
                    lesson=lesson,
                    kind=Notification.KIND_LESSON_STARTED,
                ).exists():
                    continue
                Notification.objects.create(
                    student=student,
                    kind=Notification.KIND_LESSON_STARTED,
                    title=title,
                    message=f'Курс: {lesson.course.title}',
                    link=link,
                    lesson=lesson,
                )
                created_started += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Уведомлений «через 30 мин»: {created_soon}, «урок начался»: {created_started}.'
            )
        )
