from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from WebSite.models.models import DateCreate
from WebSite.models.student_model.student import Student
from WebSite.models.study.lesson import Task


class TaskSubmission(DateCreate):
    """Сдача задания: текст ответа и/или файл. Оценку выставляет учитель или ментор."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='task_submissions')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    text = models.TextField(blank=True, help_text='Текстовый ответ')
    file = models.FileField(upload_to='submissions/%Y/%m/', blank=True, null=True, help_text='Прикреплённый файл')
    # Оценка за сдачу (выставляет учитель/ментор)
    grade_value = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Балл',
    )
    graded_at = models.DateTimeField(null=True, blank=True, verbose_name='Когда выставлена оценка')
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions',
        verbose_name='Кто выставил оценку',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сдача задания'
        verbose_name_plural = 'Сдачи заданий'

    def __str__(self):
        return f'{self.student} — {self.task}'
