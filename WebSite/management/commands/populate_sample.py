"""
Заполнение БД: по ~20 объектов каждого класса (курсы, студенты, новости, платежи и т.д.).
Запуск: python manage.py populate_sample
Опция: --clear — удалить объекты с префиксом sample_ перед заполнением.
Пароль тестовых пользователей: demo123
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
from WebSite.models.news_model import News
from WebSite.models.course_application import CourseApplication
from WebSite.models.study.submission import TaskSubmission

User = get_user_model()
PREFIX = 'sample_'
COUNT = 20
DEMO_VIDEO = 'https://www.youtube.com/watch?v=jNQXAC9IVRw'


def make_phone(n):
    return f'+7999{n:07d}'


class Command(BaseCommand):
    help = 'Заполняет БД: по 20 объектов каждого класса (курсы, студенты, новости, чеки и т.д.)'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Удалить sample_ данные перед заполнением')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self._clear()

        self.stdout.write('Преподаватели...')
        teachers, teacher_user = self._create_teachers()
        self.stdout.write('Курсы и группы (по 20)...')
        courses_data = self._create_courses_and_groups(teachers)
        self.stdout.write('Студенты (20)...')
        students = self._create_students()
        self.stdout.write('Уроки, подуроки, задания...')
        self._create_lessons_tasks(courses_data)
        self.stdout.write('Привязка студентов к группам...')
        self._link_students_groups(students, courses_data)
        self.stdout.write('Тарифы, подписки, платежи (часть с чеками)...')
        self._create_tariffs_payments(students, courses_data)
        self.stdout.write('Новости (20)...')
        self._create_news()
        self.stdout.write('Заявки на курсы (20)...')
        self._create_course_applications(courses_data)
        self.stdout.write('Результаты профтестов...')
        self._create_test_results(students)
        self.stdout.write('Прогресс и посещаемость...')
        self._create_progress_attendance(students, courses_data)
        self.stdout.write('Сдачи заданий и оценки...')
        self._create_submissions_grades(students, courses_data)

        self.stdout.write(self.style.SUCCESS('Готово. БД заполнена (по ~20 объектов каждого класса).'))
        self.stdout.write('Пароль тестовых пользователей: demo123')
        self.stdout.write('Студенты: sample_student1@example.com … sample_student20@example.com')

    def _clear(self):
        User.objects.filter(email__startswith=PREFIX).delete()
        Course.objects.filter(title__startswith=PREFIX).delete()
        News.objects.filter(title__startswith=PREFIX).delete()
        CourseApplication.objects.filter(name__startswith=PREFIX).delete()
        self.stdout.write('  Удалены sample_ данные.')

    def _create_teachers(self):
        teachers = []
        teacher_user = User.objects.filter(email=f'{PREFIX}teacher@example.com').first()
        if not teacher_user:
            teacher_user = User.objects.create_user(
                email=f'{PREFIX}teacher@example.com',
                password='demo123',
                first_name='Преподаватель',
                surname='Sample',
                phone_number=make_phone(1),
                role='teacher',
                is_active=True,
            )
            t = Teacher.objects.create(
                user=teacher_user,
                choices='teacher',
                bio='Опытный преподаватель.',
                experience_years='5',
            )
            teachers.append(t)
        else:
            teachers.append(Teacher.objects.get(user=teacher_user))
        for i in range(2, 6):
            email = f'{PREFIX}teacher{i}@example.com'
            if User.objects.filter(email=email).exists():
                continue
            u = User.objects.create_user(
                email=email,
                password='demo123',
                first_name=f'Преподаватель{i}',
                surname='Sample',
                phone_number=make_phone(i),
                role='teacher',
                is_active=True,
            )
            teachers.append(Teacher.objects.create(user=u, choices='teacher', bio=f'Преподаватель {i}'))
        return teachers, teacher_user

    def _create_courses_and_groups(self, teachers):
        courses_data = []
        base = timezone.now().date() - timedelta(days=60)
        for i in range(1, COUNT + 1):
            teacher = teachers[(i - 1) % len(teachers)]
            title = f'{PREFIX}Курс {i}'
            if Course.objects.filter(title=title).exists():
                c = Course.objects.get(title=title)
                g = c.groups.first()
                if g:
                    courses_data.append({'course': c, 'group': g})
                continue
            c = Course.objects.create(
                title=title,
                description=f'Описание курса {i}. Программа обучения, практика, проекты.',
                creator=teacher,
                price=5000 + i * 500,
                duration_months=3 + (i % 6),
                modules_description=f'1 месяц — введение; 2 месяц — практика; 3 месяц — проект.' if i <= 10 else '',
                trailer_video_url=DEMO_VIDEO if i % 3 == 0 else '',
            )
            g = Group.objects.create(
                name=f'{PREFIX}Группа {i}-1',
                course=c,
                start_date=base + timedelta(days=i * 7),
            )
            courses_data.append({'course': c, 'group': g})
        return courses_data

    def _create_students(self):
        students = []
        first_names = ['Алексей', 'Мария', 'Дмитрий', 'Анна', 'Сергей', 'Елена', 'Игорь', 'Ольга', 'Никита', 'Татьяна',
                       'Павел', 'Юлия', 'Андрей', 'Наталья', 'Михаил', 'Катерина', 'Роман', 'Светлана', 'Артём', 'Виктория']
        surnames = ['Иванов', 'Петрова', 'Сидоров', 'Козлова', 'Николаев', 'Морозова', 'Волков', 'Соколова', 'Лебедев', 'Кузнецова',
                    'Попов', 'Новикова', 'Федоров', 'Михайлова', 'Егоров', 'Андреева', 'Козлов', 'Орлова', 'Семёнов', 'Павлова']
        for i in range(1, COUNT + 1):
            email = f'{PREFIX}student{i}@example.com'
            if User.objects.filter(email=email).exists():
                students.append(Student.objects.get(user=User.objects.get(email=email)))
                continue
            u = User.objects.create_user(
                email=email,
                password='demo123',
                first_name=first_names[(i - 1) % len(first_names)],
                surname=surnames[(i - 1) % len(surnames)],
                phone_number=make_phone(100 + i),
                role='student',
                is_active=True,
            )
            s = Student.objects.create(user=u, course=None)
            students.append(s)
        return students

    def _create_lessons_tasks(self, courses_data):
        base_time = timezone.now() + timedelta(days=1)
        for idx, data in enumerate(courses_data[:COUNT]):
            course, group = data['course'], data['group']
            for j in range(1, 6):
                s_at = base_time + timedelta(days=7 * j + idx * 2)
                lesson, _ = Lesson.objects.get_or_create(
                    course=course,
                    group=group,
                    title=f'{PREFIX}Урок {j}',
                    defaults={'scheduled_at': s_at},
                )
                if lesson.scheduled_at != s_at:
                    lesson.scheduled_at = s_at
                    lesson.save()
                for k in range(1, 4):
                    sub, _ = SubLesson.objects.get_or_create(
                        lesson=lesson,
                        order=k,
                        defaults={'title': f'Часть {k}', 'content_link': DEMO_VIDEO},
                    )
                    Task.objects.get_or_create(
                        sub_lesson=sub,
                        description=f'Задание по части {k} (урок {j})',
                        defaults={'max_score': 100},
                    )

    def _link_students_groups(self, students, courses_data):
        for i, data in enumerate(courses_data[:COUNT]):
            group = data['group']
            student = students[i % len(students)]
            if student not in group.students.all():
                group.students.add(student)
            if (i + 1) < len(students) and students[(i + 1) % len(students)] not in group.students.all():
                group.students.add(students[(i + 1) % len(students)])

    def _create_tariffs_payments(self, students, courses_data):
        for i, data in enumerate(courses_data[:COUNT]):
            course = data['course']
            tariff, _ = Tariff.objects.get_or_create(
                title=f'{PREFIX}Тариф курса {course.id}',
                course=course,
                defaults={'price': course.price or 10000, 'duration_days': 90},
            )
            for student in students[:min(10, len(students))]:
                sub, _ = StudentSubscription.objects.get_or_create(
                    student=student,
                    tariff=tariff,
                    defaults={'is_active': True},
                )
                pay, created = Payment.objects.get_or_create(
                    student=student,
                    subscription=sub,
                    defaults={'amount': tariff.price, 'method': 'card', 'is_confirmed': i % 3 != 0},
                )
                if not created and i % 2 == 0:
                    pay.is_confirmed = True
                    pay.confirmed_by_name = 'Менеджер'
                    pay.save()

    def _create_news(self):
        for i in range(1, COUNT + 1):
            title = f'{PREFIX}Новость {i}'
            if News.objects.filter(title=title).exists():
                continue
            News.objects.create(
                title=title,
                content=f'Текст новости {i}. Важная информация для студентов и преподавателей. Обновления платформы.',
                is_published=True,
            )

    def _create_course_applications(self, courses_data):
        for i in range(1, COUNT + 1):
            if CourseApplication.objects.filter(name=f'{PREFIX}Заявка {i}').exists():
                continue
            data = courses_data[(i - 1) % len(courses_data)]
            CourseApplication.objects.create(
                course=data['course'],
                name=f'{PREFIX}Заявка {i}',
                telegram=f'user{i}',
                tag=f'tag{i}',
                status='pending' if i % 2 else 'contacted',
            )

    def _create_test_results(self, students):
        from WebSite.models.proftest_result import TestResult
        profiles = ['ai_business', 'design_content', 'python_ml', 'analytics']
        for i, student in enumerate(students[:COUNT]):
            if not hasattr(student, 'user') or not student.user:
                continue
            if TestResult.objects.filter(user=student.user).exists():
                continue
            TestResult.objects.create(
                user=student.user,
                profile_id=profiles[i % len(profiles)],
                scores_json={'scores': [1, 2, 3]},
            )

    def _create_progress_attendance(self, students, courses_data):
        for data in courses_data[:COUNT]:
            course, group = data['course'], data['group']
            lessons = list(Lesson.objects.filter(course=course, group=group).order_by('scheduled_at')[:4])
            for student in group.students.all()[:5]:
                for lesson in lessons[:3]:
                    Attendance.objects.get_or_create(student=student, lesson=lesson, defaults={'is_present': True})
                total = Lesson.objects.filter(course=course, group=group).count()
                completed = min(Attendance.objects.filter(student=student, lesson__course=course).count(), total)
                StudentProgress.objects.update_or_create(
                    student=student,
                    course=course,
                    defaults={
                        'completed_lessons_count': completed,
                        'average_grade': 70.0 + (student.id % 30),
                        'finished_course': completed >= total and total > 0,
                    },
                )

    def _create_submissions_grades(self, students, courses_data):
        for data in courses_data[:5]:
            course = data['course']
            tasks = list(Task.objects.filter(sub_lesson__lesson__course=course)[:10])
            for student in students[:8]:
                for task in tasks[:3]:
                    if not TaskSubmission.objects.filter(student=student, task=task).exists():
                        TaskSubmission.objects.create(student=student, task=task, text=f'Ответ студента {student.id}')
        for gtype in [Grade.GradeType.LESSON, Grade.GradeType.CONTROL, Grade.GradeType.HOMEWORK]:
            for v in [72, 78, 85, 90, 95]:
                Grade.objects.create(grade=gtype, grade_value=v)
