"""
Минимальный набор данных: 1 учитель, 1 ментор, 1 курс, 1 группа, 3 студента, несколько уроков и сдач.
Запуск: python manage.py populate_minimal
Опция: --clear — удалить старые тестовые данные (demo_* и sample_*) перед созданием.

Пароль у всех тестовых пользователей: demo123
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, models

from WebSite.models.worker_model.workers import Teacher
from WebSite.models.study.lesson import Course, Lesson, SubLesson, Task
from WebSite.models.group.groups import Group
from WebSite.models.student_model.student import Student
from WebSite.models.student_model.attandance import Attendance, StudentProgress
from WebSite.models.study.grade_model import Grade
from WebSite.models.study.tarif_system import Tariff
from WebSite.models.pay_system.payment import StudentSubscription, Payment
from WebSite.models.study.submission import TaskSubmission
from WebSite.models.group.groups import GroupChatMessage

User = get_user_model()
PREFIX = 'demo_'
DEMO_VIDEO = 'https://www.youtube.com/watch?v=jNQXAC9IVRw'


def make_phone(n):
    """Уникальный номер: +7999 и 7 цифр (n до 9999999)."""
    return f'+7999{n:07d}' if n < 10_000_000 else f'+7999{n}'


class Command(BaseCommand):
    help = 'Удаляет старые тестовые данные и создаёт минимальный набор: 1 учитель, 1 ментор, 3 студента, 1 курс, уроки, сдачи.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Удалить данные demo_* и sample_* перед созданием')

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get('clear'):
            self._clear()

        self.stdout.write('Создание учителя и ментора...')
        teacher_user, mentor_user = self._create_teacher_and_mentor()
        self.stdout.write('Курс и группа...')
        course, group = self._create_course_and_group(teacher_user, mentor_user)
        self.stdout.write('Студенты (3)...')
        students = self._create_students(course, group)
        self.stdout.write('Уроки, подуроки, задания (типы: на уроке, домашка, контрольная)...')
        lessons, tasks = self._create_lessons_and_tasks(course, group, teacher_user)
        self.stdout.write('Тариф, подписки, платежи...')
        self._create_subscriptions(students, course)
        self.stdout.write('Прогресс и посещаемость...')
        self._create_progress(students, group, lessons)
        self.stdout.write('Сдачи заданий (несколько с оценками)...')
        self._create_submissions(students, tasks, teacher_user)
        self.stdout.write('Сообщения в чате группы...')
        self._create_chat_messages(group, teacher_user, mentor_user, students)

        self.stdout.write(self.style.SUCCESS('Готово.'))
        self.stdout.write('Пароль: demo123')
        self.stdout.write('  Учитель: demo_teacher@example.com')
        self.stdout.write('  Ментор: demo_mentor@example.com')
        self.stdout.write('  Студенты: demo_student1@example.com, demo_student2@example.com, demo_student3@example.com')

    def _clear(self):
        # Тарифы и подписки ссылаются на курс — удаляем их до удаления курсов
        courses_q = models.Q(title__startswith='demo_') | models.Q(title__startswith='sample_')
        course_ids = list(Course.objects.filter(courses_q).values_list('id', flat=True))
        if course_ids:
            tariffs = Tariff.objects.filter(course_id__in=course_ids)
            sub_ids = list(StudentSubscription.objects.filter(tariff__in=tariffs).values_list('id', flat=True))
            Payment.objects.filter(subscription_id__in=sub_ids).delete()
            StudentSubscription.objects.filter(tariff__in=tariffs).delete()
            tariffs.delete()
        Course.objects.filter(courses_q).delete()
        User.objects.filter(
            models.Q(email__startswith='demo_') | models.Q(email__startswith='sample_')
        ).delete()
        Grade.objects.all().delete()
        self.stdout.write('  Удалены тестовые данные (demo_*, sample_*).')

    def _create_teacher_and_mentor(self):
        teacher_user = User.objects.filter(email=f'{PREFIX}teacher@example.com').first()
        if not teacher_user:
            teacher_user = User.objects.create_user(
                email=f'{PREFIX}teacher@example.com',
                password='demo123',
                first_name='Иван',
                surname='Преподавателей',
                phone_number=make_phone(900001),
                role='teacher',
                is_active=True,
            )
            Teacher.objects.create(
                user=teacher_user,
                choices='teacher',
                bio='Преподаватель курса.',
            )
        mentor_user = User.objects.filter(email=f'{PREFIX}mentor@example.com').first()
        if not mentor_user:
            mentor_user = User.objects.create_user(
                email=f'{PREFIX}mentor@example.com',
                password='demo123',
                first_name='Мария',
                surname='Менторова',
                phone_number=make_phone(900002),
                role='mentor',
                is_active=True,
            )
            Teacher.objects.create(
                user=mentor_user,
                choices='mentor',
                bio='Ментор группы.',
            )
        return teacher_user, mentor_user

    def _create_course_and_group(self, teacher_user, mentor_user):
        teacher = Teacher.objects.get(user=teacher_user)
        mentor = Teacher.objects.get(user=mentor_user)
        course = Course.objects.filter(title__startswith=PREFIX).first()
        if not course:
            course = Course.objects.create(
                title=f'{PREFIX}Python для начинающих',
                description='Базовый курс программирования на Python.',
                creator=teacher,
                price=99.99,
            )
        group = course.groups.first()
        if not group:
            group = Group.objects.create(
                name=f'{PREFIX}Группа 1',
                course=course,
                teacher=teacher,
                mentor=mentor,
                start_date=timezone.now().date() - timedelta(days=14),
            )
        else:
            if not group.teacher_id:
                group.teacher = teacher
                group.mentor = mentor
                group.save()
        return course, group

    def _create_students(self, course, group):
        students = []
        for i in range(1, 4):
            email = f'{PREFIX}student{i}@example.com'
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(
                    email=email,
                    password='demo123',
                    first_name=['Алексей', 'Мария', 'Дмитрий'][i - 1],
                    surname=['Иванов', 'Петрова', 'Сидоров'][i - 1],
                    phone_number=make_phone(900010 + i),
                    role='student',
                    is_active=True,
                )
            student, _ = Student.objects.get_or_create(user=user, defaults={'course': course})
            if student not in group.students.all():
                group.students.add(student)
            students.append(student)
        return students

    def _create_lessons_and_tasks(self, course, group, teacher_user):
        teacher = Teacher.objects.get(user=teacher_user)
        base = timezone.now() + timedelta(days=1)
        lessons = []
        all_tasks = []
        for j in range(1, 3):
            lesson, _ = Lesson.objects.get_or_create(
                course=course,
                group=group,
                title=f'{PREFIX}Урок {j}',
                defaults={
                    'scheduled_at': base + timedelta(days=7 * j),
                    'created_by': teacher,
                },
            )
            lessons.append(lesson)
            for k in range(1, 3):
                sub, _ = SubLesson.objects.get_or_create(
                    lesson=lesson,
                    order=k,
                    defaults={
                        'title': f'Часть {k}',
                        'content_link': DEMO_VIDEO,
                    },
                )
                # Разные типы заданий: на уроке, домашка, одна контрольная
                task_type = Task.TaskType.LESSON
                if j == 1 and k == 2:
                    task_type = Task.TaskType.HOMEWORK
                if j == 2 and k == 1:
                    task_type = Task.TaskType.CONTROL
                task, _ = Task.objects.get_or_create(
                    sub_lesson=sub,
                    description=f'Задание по части {k} (урок {j})',
                    defaults={'max_score': 100, 'task_type': task_type},
                )
                all_tasks.append(task)
        return lessons, all_tasks

    def _create_subscriptions(self, students, course):
        tariff, _ = Tariff.objects.get_or_create(
            title=f'{PREFIX}Тариф Базовый',
            course=course,
            defaults={'price': 99.99, 'duration_days': 90},
        )
        for student in students:
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

    def _create_progress(self, students, group, lessons):
        for student in students:
            for lesson in lessons[:1]:
                Attendance.objects.get_or_create(
                    student=student,
                    lesson=lesson,
                    defaults={'is_present': True},
                )
            completed = Attendance.objects.filter(student=student, lesson__group=group).count()
            total = len(lessons)
            StudentProgress.objects.update_or_create(
                student=student,
                course=group.course,
                defaults={
                    'completed_lessons_count': completed,
                    'average_grade': 75.0,
                    'finished_course': False,
                },
            )

    def _create_submissions(self, students, tasks, teacher_user):
        for student in students[:2]:
            for task in tasks[:3]:
                if TaskSubmission.objects.filter(student=student, task=task).exists():
                    continue
                name = f'{getattr(student.user, "surname", "")} {getattr(student.user, "first_name", "")}'.strip() or student.user.email
                sub = TaskSubmission.objects.create(
                    student=student,
                    task=task,
                    text=f'Ответ студента {name} по заданию.',
                )
                # Выставить оценку за первые две сдачи
                if student == students[0] and task == tasks[0]:
                    sub.grade_value = 85
                    sub.graded_at = timezone.now()
                    sub.graded_by = teacher_user
                    sub.save(update_fields=['grade_value', 'graded_at', 'graded_by'])

    def _create_chat_messages(self, group, teacher_user, mentor_user, students):
        if GroupChatMessage.objects.filter(group=group).exists():
            return
        messages = [
            (teacher_user, 'Добрый день! Напоминаю: следующий урок в среду.'),
            (mentor_user, 'Есть вопросы по домашнему заданию — пишите сюда.'),
            (students[0].user, 'Спасибо, тогда до встречи на занятии.'),
        ]
        for author, text in messages:
            GroupChatMessage.objects.create(group=group, author=author, text=text)
