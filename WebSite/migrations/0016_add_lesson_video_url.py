# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WebSite', '0015_add_task_type_and_submission_grade'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='video_url',
            field=models.URLField(blank=True, help_text='Ссылка на видео урока (YouTube и т.д.)', max_length=500),
        ),
    ]
