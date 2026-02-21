from WebSite.models.models import DateCreate
from WebSite.models.study.lesson import Course
from django.db import models

class Student(DateCreate):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)