from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.study import Course


class Tariff(DateCreate):
    title = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(help_text="На сколько дней дается доступ")

    def __str__(self):
        return f"{self.title} - {self.course.title}"

