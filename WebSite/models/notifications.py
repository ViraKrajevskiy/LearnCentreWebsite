from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.student_model.student import Student
from WebSite.models.study.lesson import Lesson


class Notification(DateCreate):
    """Уведомление для студента: новости, ДЗ, напоминание об уроке."""
    KIND_NEWS = 'news'
    KIND_HOMEWORK = 'homework'
    KIND_LESSON_SOON = 'lesson_soon'
    KIND_LESSON_STARTED = 'lesson_started'
    KIND_CHOICES = [
        (KIND_NEWS, 'Новость'),
        (KIND_HOMEWORK, 'Домашнее задание'),
        (KIND_LESSON_SOON, 'Урок через 30 мин'),
        (KIND_LESSON_STARTED, 'Урок начался'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True, help_text='URL для перехода по клику')
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, null=True, blank=True,
        related_name='+', help_text='Для lesson_soon/lesson_started — дедупликация',
    )
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'is_read']),
            models.Index(fields=['student', 'lesson', 'kind']),
        ]

    def __str__(self):
        return f'{self.student_id} | {self.get_kind_display()} | {self.title[:50]}'
