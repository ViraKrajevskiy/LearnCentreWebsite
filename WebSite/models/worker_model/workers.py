from django.db import models

from WebSite.models.models import DateCreate


class Teacher(DateCreate):
    bio = models.TextField(blank=True)

class Mentor(DateCreate):
    pass
