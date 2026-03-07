from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.study import Course


class Tariff(DateCreate):
    LEARNING_ACTIVE = 'active'   # Последовательно: сдал урок — следующий откроется в своё время
    LEARNING_SMOOTH = 'smooth'   # Плавное: уроки открыты по расписанию или все сразу
    LEARNING_MODES = [
        (LEARNING_ACTIVE, 'Активное (последовательно)'),
        (LEARNING_SMOOTH, 'Плавное'),
    ]

    title = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(help_text="На сколько дней дается доступ")
    learning_mode = models.CharField(
        max_length=20,
        choices=LEARNING_MODES,
        default=LEARNING_SMOOTH,
        help_text='Активное: следующий урок открывается после сдачи предыдущего и в назначенное время. Плавное: уроки открыты по расписанию.',
    )

    def __str__(self):
        return f"{self.title} - {self.course.title}"

