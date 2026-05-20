# Generated manually for Notification and News

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('WebSite', '0004_add_lesson_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('content', models.TextField(blank=True)),
                ('is_published', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Новость',
                'verbose_name_plural': 'Новости',
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(choices=[('news', 'Новость'), ('homework', 'Домашнее задание'), ('lesson_soon', 'Урок через 30 мин'), ('lesson_started', 'Урок начался')], db_index=True, max_length=20)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField(blank=True)),
                ('link', models.CharField(blank=True, help_text='URL для перехода по клику', max_length=500)),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('lesson', models.ForeignKey(blank=True, help_text='Для lesson_soon/lesson_started — дедупликация', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='WebSite.lesson')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='WebSite.student')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['student', 'is_read'], name='notif_student_read_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['student', 'lesson', 'kind'], name='notif_student_lesson_kind_idx'),
        ),
    ]
