from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from WebSite.models.news_model import News
from WebSite.models.notifications import Notification
from WebSite.models.study.lesson import Task


@receiver(post_save, sender=News)
def on_news_created(sender, instance, created, **kwargs):
    if not created or not instance.is_published:
        return
    from WebSite.models.student_model.student import Student
    url = reverse('news')
    msg = (instance.content[:200] + '…') if len(instance.content or '') > 200 else (instance.content or '')
    for student in Student.objects.all():
        Notification.objects.create(
            student=student,
            kind=Notification.KIND_NEWS,
            title=instance.title,
            message=msg,
            link=url,
        )


@receiver(post_save, sender=Task)
def on_task_created(sender, instance, created, **kwargs):
    if not created:
        return
    lesson = instance.sub_lesson.lesson
    group = lesson.group
    url = reverse('lesson_detail', args=[lesson.id])
    title = f'Новое задание: {instance.sub_lesson.title}'
    for student in group.students.all():
        Notification.objects.create(
            student=student,
            kind=Notification.KIND_HOMEWORK,
            title=title,
            message=instance.description[:200] if instance.description else '',
            link=url,
        )
