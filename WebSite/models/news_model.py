from django.db import models
from WebSite.models.models import DateCreate


class News(DateCreate):
    """Новость для ленты; при создании студентам создаются уведомления (сигнал)."""
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return self.title[:60]
