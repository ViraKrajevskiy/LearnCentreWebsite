from WebSite.models.models import DateCreate
from django.db import models

class Grade(DateCreate):
    grade_type = [
        ('lesson_grade', 'grade_lesson'),
        ('control_work_grade','grade_control_work'),
        ('home_work_grade','grade_home_work')
    ]
    grade = models.CharField(max_length=30, choices=grade_type,default='lesson_grade')
    grade_value = models.IntegerField(null=True, blank=True)