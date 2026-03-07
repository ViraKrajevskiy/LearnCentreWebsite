"""
Команда для заполнения моделей тестовыми данными.
Запуск: python manage.py populate_models
Опции: --clear — удалить созданные этой командой данные перед заполнением (по тегу).

Пароль у всех тестовых пользователей: demo123
Студенты: demo_student1@example.com … demo_student5@example.com
Преподаватель: demo_teacher@example.com
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from WebSite.models.worker_model.workers import Teacher
from WebSite.models.study.lesson import Course, Lesson, SubLesson, Task
from WebSite.models.group.groups import Group
from WebSite.models.student_model.student import Student
from WebSite.models.student_model.attandance import Attendance, StudentProgress
from WebSite.models.study.grade_model import Grade
from WebSite.models.study.tarif_system import Tariff
from WebSite.models.pay_system.payment import StudentSubscription, Payment

User = get_user_model()

# Тег для поиска созданных командой записей (по email/именам)
DEMO_PREFIX = 'demo_'


def make_phone(n):
    return f'+998901234{n:02d}'


class Command(BaseCommand):
    help = 'Заполняет модели тестовыми данными (пользователи, курсы, группы, студенты, уроки и т.д.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Сначала удалить тестовые данные (пользователи с email demo_*), затем заполнить заново',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self._clear_demo_data()

        self.stdout.write('Создание пользователей и преподавателей...')
        teacher_user, students_data = self._create_users_and_teachers()

        self.stdout.write('Создание курсов и групп...')
        courses_data = self._create_courses_and_groups(teacher_user)

        self.stdout.write('Создание студентов и привязка к группам...')
        students = self._create_students(students_data, courses_data)

        self.stdout.write('Создание уроков, подуроков и заданий...')
        self._create_lessons_sublessons_tasks(courses_data)

        self.stdout.write('Создание тарифов, подписок и платежей...')
        self._create_tariffs_subscriptions_payments(courses_data, students)

        self.stdout.write('Создание посещаемости и прогресса...')
        self._create_attendance_and_progress(courses_data, students)

        self.stdout.write('Создание оценок...')
        self._create_grades(students)

        self.stdout.write(self.style.SUCCESS('Готово. Модели заполнены тестовыми данными.'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Пароль у всех тестовых пользователей: demo123'))
        self.stdout.write('  Студенты: demo_student1@example.com … demo_student5@example.com')
        self.stdout.write('  Преподаватель: demo_teacher@example.com')
        self.stdout.write('')
        self.stdout.write('Проверка видео на сайте: войдите на сайт как студент (логин/пароль выше),')
        self.stdout.write('  Мои курсы → откройте первый курс → нажмите «Продолжить» у первого урока')
        self.stdout.write('  или перейдите в «Домашняя работа» и откройте урок из списка.')

    def _clear_demo_data(self):
        """Удаляет пользователей с email, начинающимся с demo_."""
        to_delete = User.objects.filter(email__startswith=DEMO_PREFIX)
        count = to_delete.count()
        to_delete.delete()
        self.stdout.write(f'  Удалено пользователей (demo): {count}')
        # Каскадно удалятся Student, Teacher и связанные данные

    def _create_users_and_teachers(self):
        teacher_user = User.objects.filter(email=f'{DEMO_PREFIX}teacher@example.com').first()
        if not teacher_user:
            teacher_user = User.objects.create_user(
                email=f'{DEMO_PREFIX}teacher@example.com',
                password='demo123',
                first_name='Иван',
                surname='Преподавателей',
                last_name='Петрович',
                phone_number=make_phone(1),
                role='teacher',
                is_active=True,
            )
            Teacher.objects.get_or_create(
                user=teacher_user,
                defaults={
                    'choices': 'teacher',
                    'bio': 'Опытный преподаватель по программированию и AI.',
                    'experience_years': '10',
                    'working_companies': '101 school, Тинькофф',
                },
            )
            self.stdout.write('  Создан преподаватель: demo_teacher@example.com')

        students_data = []
        for i in range(1, 6):
            email = f'{DEMO_PREFIX}student{i}@example.com'
            if User.objects.filter(email=email).exists():
                continue
            students_data.append({
                'email': email,
                'first_name': ['Алексей', 'Мария', 'Дмитрий', 'Анна', 'Сергей'][i - 1],
                'surname': ['Иванов', 'Петрова', 'Сидоров', 'Козлова', 'Николаев'][i - 1],
                'phone': make_phone(i + 10),
            })

        for d in students_data:
            User.objects.create_user(
                email=d['email'],
                password='demo123',
                first_name=d['first_name'],
                surname=d['surname'],
                phone_number=d['phone'],
                role='student',
                is_active=True,
            )
        self.stdout.write(f'  Создано/пропущено студентов: {len(students_data)}')
        return teacher_user, students_data

    def _create_courses_and_groups(self, teacher_user):
        teacher = Teacher.objects.get(user=teacher_user)
        courses_data = []

        for idx, (title, desc) in enumerate([
            ('Python для начинающих', 'Базовый курс программирования на Python.'),
            ('ИИ и машинное обучение', 'Введение в нейросети и ML.'),
        ], 1):
            course, _ = Course.objects.get_or_create(
                title=f'{DEMO_PREFIX}{title}',
                defaults={
                    'description': desc,
                    'creator': teacher,
                    'price': 99.99 * idx,
                },
            )
            start = timezone.now().date() - timedelta(days=30)
            group, _ = Group.objects.get_or_create(
                name=f'{DEMO_PREFIX}Группа {idx}-1',
                course=course,
                defaults={'start_date': start},
            )
            courses_data.append({'course': course, 'group': group})
        self.stdout.write(f'  Курсов/групп: {len(courses_data)}')
        return courses_data

    def _create_students(self, students_data, courses_data):
        students = []
        for d in students_data:
            user = User.objects.get(email=d['email'])
            student, _ = Student.objects.get_or_create(
                user=user,
                defaults={'course': courses_data[0]['course'] if courses_data else None},
            )
            students.append(student)
            if courses_data:
                g = courses_data[0]['group']
                if student not in g.students.all():
                    g.students.add(student)
                if len(courses_data) > 1 and student not in courses_data[1]['group'].students.all():
                    courses_data[1]['group'].students.add(student)
        return students

    # Один ролик с разрешённым встраиванием — иначе YouTube показывает "Video unavailable"
    EMBEDDABLE_VIDEO = 'https://www.youtube.com/watch?v=jNQXAC9IVRw'  # Me at the zoo
    DEMO_YOUTUBE_URLS = [EMBEDDABLE_VIDEO]  # один и тот же для всех подуроков

    def _create_lessons_sublessons_tasks(self, courses_data):
        base_time = timezone.now() + timedelta(days=1)
        video_index = 0
        for idx, data in enumerate(courses_data):
            course, group = data['course'], data['group']
            for j in range(1, 4):
                s_at = base_time + timedelta(days=7 * j + idx * 3)
                lesson, _ = Lesson.objects.get_or_create(
                    course=course,
                    group=group,
                    title=f'{DEMO_PREFIX}Урок {j}',
                    scheduled_at=s_at,
                    defaults={},
                )
                for k in range(1, 3):
                    content_link = self.DEMO_YOUTUBE_URLS[video_index % len(self.DEMO_YOUTUBE_URLS)]
                    video_index += 1
                    sub, created = SubLesson.objects.get_or_create(
                        lesson=lesson,
                        order=k,
                        defaults={
                            'title': f'Часть {k}',
                            'content_link': content_link,
                        },
                    )
                    if sub.content_link != content_link:
                        sub.content_link = content_link
                        sub.save()
                    Task.objects.get_or_create(
                        sub_lesson=sub,
                        description=f'Задание по части {k}',
                        defaults={'max_score': 100},
                    )
        self.stdout.write('  Уроки, подуроки и задания созданы.')
        self.stdout.write('  У всех подуроков проставлены демо-видео YouTube.')

    def _create_tariffs_subscriptions_payments(self, courses_data, students):
        for data in courses_data:
            course = data['course']
            tariff, _ = Tariff.objects.get_or_create(
                title=f'{DEMO_PREFIX}Тариф {course.title[:20]}',
                course=course,
                defaults={'price': 99.99, 'duration_days': 90},
            )
            for student in students[:3]:
                sub, _ = StudentSubscription.objects.get_or_create(
                    student=student,
                    tariff=tariff,
                    defaults={'is_active': True},
                )
                Payment.objects.get_or_create(
                    student=student,
                    subscription=sub,
                    amount=tariff.price,
                    method='card',
                    defaults={'is_confirmed': True, 'confirmed_by_name': 'Админ'},
                )
        self.stdout.write('  Тарифы, подписки и платежи созданы.')

    def _create_attendance_and_progress(self, courses_data, students):
        for data in courses_data:
            course, group = data['course'], data['group']
            lessons = list(Lesson.objects.filter(course=course, group=group).order_by('scheduled_at')[:2])
            for student in students[:4]:
                for lesson in lessons:
                    Attendance.objects.get_or_create(
                        student=student,
                        lesson=lesson,
                        defaults={'is_present': True},
                    )
                completed = Attendance.objects.filter(student=student, lesson__course=course).count()
                total = Lesson.objects.filter(course=course, group=group).count()
                avg = 75.0
                StudentProgress.objects.update_or_create(
                    student=student,
                    course=course,
                    defaults={
                        'completed_lessons_count': completed,
                        'average_grade': avg,
                        'finished_course': completed >= total and total > 0,
                    },
                )
        self.stdout.write('  Посещаемость и прогресс созданы.')

    def _create_grades(self, students):
        # Модель Grade без FK на student/lesson — создаём тестовые оценки
        for gtype in [Grade.GradeType.LESSON, Grade.GradeType.CONTROL, Grade.GradeType.HOMEWORK]:
            for value in [72, 85, 90]:
                Grade.objects.create(grade=gtype, grade_value=value)
        self.stdout.write('  Оценки созданы.')
