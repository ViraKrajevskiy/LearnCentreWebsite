from django.db import models
from WebSite.models.models import DateCreate

class Teacher(DateCreate):
    worker_type = [
        ('teacher', 'teacher'),
        ('mentor', 'mentor')
    ]
    choices = models.CharField(max_length=10, choices=worker_type, default='teacher')
    bio = models.TextField(blank=True,null= True)
    experience_years = models.TextField(null= True,blank=True)
    working_companies = models.TextField(null= True,blank=True)
