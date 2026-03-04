from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.student_model.student import Student
from WebSite.models.study.lesson import Lesson


class LessonComment(DateCreate):
    """Комментарий студента под уроком. Описание урока и задания добавляют только ментор/учитель."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='comments')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='lesson_comments')
    text = models.TextField(verbose_name='Текст комментария')
    file = models.FileField(upload_to='lesson_comments/%Y/%m/', blank=True, null=True, verbose_name='Прикреплённый файл')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Комментарий к уроку'
        verbose_name_plural = 'Комментарии к урокам'

    def __str__(self):
        return f'{self.student} — {self.lesson.title}'
