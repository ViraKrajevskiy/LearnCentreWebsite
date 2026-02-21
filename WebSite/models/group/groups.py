from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.student_model.student import Student
from WebSite.models.study.lesson import Course
from WebSite.models.worker_model.workers import Mentor


class Group(DateCreate):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='groups')
    mentor = models.ForeignKey(Mentor, on_delete=models.SET_NULL, null=True)
    students = models.ManyToManyField(Student, related_name='study_groups')
    start_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.course.title})"