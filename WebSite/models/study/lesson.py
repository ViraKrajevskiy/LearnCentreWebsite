from django.db import models
from WebSite.models.models import DateCreate
from WebSite.models.group.groups import Group
from WebSite.models.worker_model.workers import Teacher

class Course(DateCreate):
    title = models.CharField(max_length=255)
    description = models.TextField()
    creator = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.title

class Lesson(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content_link = models.URLField()
    scheduled_at = models.DateTimeField()
