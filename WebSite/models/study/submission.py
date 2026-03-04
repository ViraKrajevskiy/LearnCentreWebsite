from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.student_model.student import Student
from WebSite.models.study.lesson import Task


class TaskSubmission(DateCreate):
    """Сдача задания: текст ответа и/или файл."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='task_submissions')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    text = models.TextField(blank=True, help_text='Текстовый ответ')
    file = models.FileField(upload_to='submissions/%Y/%m/', blank=True, null=True, help_text='Прикреплённый файл')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сдача задания'
        verbose_name_plural = 'Сдачи заданий'

    def __str__(self):
        return f'{self.student} — {self.task}'
