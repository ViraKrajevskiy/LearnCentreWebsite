from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.group.groups import Group
from WebSite.models.worker_model.workers import Teacher

class Course(DateCreate):
    title = models.CharField(max_length=255)
    description = models.TextField()
    creator = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # Длительность и модули (например: "1 месяц — Python, 2 месяц — SQL, ...")
    duration_months = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Длительность курса в месяцах (например: 7)'
    )
    modules_description = models.TextField(
        blank=True,
        help_text='Краткое описание модулей по месяцам, например: 1 месяц — Python; 2 месяц — SQL; 3 месяц — Backend'
    )
    # Ссылка на видео (трейлер или обзор курса)
    trailer_video_url = models.URLField(
        max_length=500, blank=True,
        help_text='Ссылка на видео (YouTube и т.д.) — трейлер или обзор курса'
    )

    def __str__(self):
        return self.title

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField()
    video_url = models.URLField(
        max_length=500, blank=True,
        help_text='Ссылка на видео урока (YouTube и т.д.)',
    )
    created_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_lessons',
        help_text='Кто создал урок (учитель/ментор)',
    )

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class SubLesson(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='sub_lessons')
    title = models.CharField(max_length=255)
    content_link = models.URLField(help_text="Ссылка на видео или материал")
    order = models.PositiveIntegerField(default=1, help_text="Порядок мини-урока")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.lesson.title} | Часть: {self.title}"

class Task(models.Model):
    """Задание: на уроке, домашка или контрольная. Контрольные проверяет только учитель."""
    class TaskType(models.TextChoices):
        LESSON = 'lesson', 'Задание на уроке'
        HOMEWORK = 'homework', 'Домашнее задание'
        CONTROL = 'control', 'Контрольная работа'

    sub_lesson = models.ForeignKey(SubLesson, on_delete=models.CASCADE, related_name='tasks')
    description = models.TextField(verbose_name="Описание задания")
    max_score = models.IntegerField(default=100)
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.LESSON,
        verbose_name='Тип задания',
        help_text='Контрольные может проверять только учитель.',
    )
    video_url = models.URLField(
        max_length=500, blank=True,
        verbose_name='Ссылка на видео',
        help_text='Видеоинструкция к заданию (YouTube и т.д.)',
    )
    attachment = models.FileField(
        upload_to='task_attachments/%Y/%m/',
        blank=True, null=True,
        verbose_name='Прикреплённый файл задания',
        help_text='Файл с формулировкой задания (PDF, документ и т.д.)',
    )

    def __str__(self):
        return f"Задание для {self.sub_lesson.title}"