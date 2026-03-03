from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.student_model.student import Student
from WebSite.models.study.tarif_system import Tariff
from django.utils import timezone
from datetime import timedelta

class StudentSubscription(DateCreate):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):

        if not self.end_date:
            self.end_date = timezone.now() + timedelta(days=self.tariff.duration_days)
        super().save(*args, **kwargs)

    def check_status(self):
        if self.end_date and self.end_date < timezone.now():
            self.is_active = False
            self.save()
        return self.is_active

class Payment(DateCreate):
    PAYMENT_METHODS = [
        ('card', 'Карта/Онлайн'),
        ('cash', 'Наличные'),
        ('transfer', 'Перевод/Инвойс'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subscription = models.ForeignKey(StudentSubscription, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    receipt = models.FileField(upload_to='receipts/%Y/%m/', blank=True)
    is_confirmed = models.BooleanField(default=False)
    confirmed_by_name = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if self.is_confirmed and self.subscription:
            self.subscription.is_active = True
            self.subscription.save()
        super().save(*args, **kwargs)

