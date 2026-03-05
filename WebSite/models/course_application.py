from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.study.lesson import Course
from WebSite.models.student_model.student import Student


class CourseApplication(DateCreate):
    """Заявка на курс: имя, Telegram, тег; менеджеры обрабатывают после оплаты."""

    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('contacted', 'Связались'),
        ('paid', 'Оплачено'),
        ('rejected', 'Отклонено'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(
        Student, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='course_applications',
        help_text='Если пользователь был авторизован при подаче заявки',
    )
    name = models.CharField(max_length=255, verbose_name='Имя')
    telegram = models.CharField(max_length=128, verbose_name='Telegram', help_text='Username или контакт')
    tag = models.CharField(max_length=128, blank=True, verbose_name='Тег / псевдоним')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True,
    )

    class Meta:
        verbose_name = 'Заявка на курс'
        verbose_name_plural = 'Заявки на курсы'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} — {self.course.title} ({self.get_status_display()})"
