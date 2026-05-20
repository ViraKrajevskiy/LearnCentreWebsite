# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WebSite', '0016_add_lesson_video_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='video_url',
            field=models.URLField(blank=True, help_text='Видеоинструкция к заданию (YouTube и т.д.)', max_length=500, verbose_name='Ссылка на видео'),
        ),
        migrations.AddField(
            model_name='task',
            name='attachment',
            field=models.FileField(blank=True, help_text='Файл с формулировкой задания (PDF, документ и т.д.)', null=True, upload_to='task_attachments/%Y/%m/', verbose_name='Прикреплённый файл задания'),
        ),
    ]
