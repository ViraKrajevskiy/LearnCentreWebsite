from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.student_model.student import Student
from WebSite.models.study.lesson import Lesson, Course

class Attendance(DateCreate):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    is_present = models.BooleanField(default=True)
    reason_of_absence = models.TextField(blank=True, null=True)

class StudentProgress(DateCreate):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    completed_lessons_count = models.PositiveIntegerField(default=0)
    average_grade = models.FloatField(default=0.0)
    finished_course = models.BooleanField(default=False)

