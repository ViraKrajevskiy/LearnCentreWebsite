from django.conf import settings
from django.db import models
from WebSite.models.models import DateCreate


class Group(DateCreate):
    name = models.CharField(max_length=100)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='groups')
    students = models.ManyToManyField('Student', related_name='study_groups', blank=True)
    teacher = models.ForeignKey(
        'Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teaching_groups',
        help_text='Учитель курса в этой группе',
    )
    mentor = models.ForeignKey(
        'Teacher',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mentoring_groups',
        help_text='Ментор группы',
    )
    start_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.course.title})"


class GroupChatMessage(DateCreate):
    """Сообщение в чате группы: студенты, учитель и ментор могут писать."""
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_chat_messages',
    )
    text = models.TextField(verbose_name='Текст сообщения')

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение чата группы'
        verbose_name_plural = 'Сообщения чатов групп'

    def __str__(self):
        return f"{self.group.name} — {self.author.email[:30]}"