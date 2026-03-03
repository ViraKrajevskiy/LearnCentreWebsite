from django.conf import settings
from django.db import models
from WebSite.models.models import DateCreate

class Teacher(DateCreate):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teachers',
        null=True,
        blank=True,
    )
    worker_type = [
        ('teacher', 'teacher'),
        ('mentor', 'mentor')
    ]
    choices = models.CharField(max_length=10, choices=worker_type, default='teacher')
    bio = models.TextField(blank=True,null= True)
    experience_years = models.TextField(null= True,blank=True)
    working_companies = models.TextField(null= True,blank=True)
