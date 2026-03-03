from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from WebSite.models.models import DateCreate

class Grade(DateCreate):
    class GradeType(models.TextChoices):
        LESSON = 'lesson_grade', 'Оценка за урок'
        CONTROL = 'control_work_grade', 'Контрольная работа'
        HOMEWORK = 'home_work_grade', 'Домашнее задание'

    grade = models.CharField(
        max_length=30,
        choices=GradeType.choices,
        default=GradeType.LESSON
    )

    grade_value = models.IntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )

    def clean(self):
        super().clean()
        if self.grade_value is not None:
            if self.grade_value < 0 or self.grade_value > 100:
                raise ValidationError({
                    'grade_value': "Значение должно быть в диапазоне от 0 до 100"
                })

    def __str__(self):
        return f"{self.get_grade_display()}: {self.grade_value}"