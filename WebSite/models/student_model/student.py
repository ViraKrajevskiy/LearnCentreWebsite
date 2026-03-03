from django.conf import settings
from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.study.lesson import Course


class Student(DateCreate):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student',
        null=True,
        blank=True,
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)