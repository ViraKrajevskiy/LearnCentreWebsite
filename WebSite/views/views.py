from datetime import date, timedelta

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from WebSite.models.student_model.attandance import Attendance, StudentProgress
from WebSite.models.study.grade_model import Grade
from WebSite.models.study.lesson import Course, Lesson, SubLesson, Task
from WebSite.models.pay_system.payment import StudentSubscription

def _get_next_lesson_for_student(student, course):
    student_groups = student.study_groups.filter(course=course)
    attended_lesson_ids = set(
        Attendance.objects.filter(student=student).values_list('lesson_id', flat=True)
    )
    for group in student_groups:
        for lesson in group.lessons.order_by('scheduled_at'):
            if lesson.id not in attended_lesson_ids:
                return lesson
    return None


def _get_my_courses_data(student):
    """
    Возвращает только купленные курсы студента — по подпискам (StudentSubscription).
    Студент видит в личном кабинете только те курсы, на которые у него есть подписка.
    """
    result = []
    subscriptions = (
        StudentSubscription.objects
        .filter(student=student)
        .select_related('tariff__course')
        .order_by('-start_date')
    )
    seen_course_ids = set()
    for sub in subscriptions:
        course = sub.tariff.course
        if course.id in seen_course_ids:
            continue
        seen_course_ids.add(course.id)
        group = student.study_groups.filter(course=course).first() or course.groups.first()
        total = group.lessons.count() if group else 0
        attended = (
            Attendance.objects.filter(student=student, lesson__group__course=course).count()
            if group else 0
        )
        next_lesson = _get_next_lesson_for_student(student, course)
        first_lesson = group.lessons.order_by('scheduled_at').first() if group else None
        continue_url = (
            reverse('lesson', args=[next_lesson.id]) if next_lesson else
            (reverse('lesson', args=[first_lesson.id]) if first_lesson else None)
        )
        result.append({
            'course': course,
            'group': group,
            'total_lessons': total,
            'completed': attended,
            'percent': round(100 * attended / total) if total else 0,
            'next_lesson': next_lesson,
            'continue_url': continue_url,
            'subscription': sub,
        })
    return result


def main_home(request):
    return render(request, 'main_pages/index.html')

def main_courses(request):
    return render(request, 'main_pages/courses.html')

def main_about(request):
    return render(request, 'main_pages/about.html')

def main_contact(request):
    return render(request, 'main_pages/contact.html')

def main_faq(request):
    return render(request, 'main_pages/faq.html')

def main_invite(request):
    return render(request, 'main_pages/invite.html')

def main_login(request):
    return render(request, 'main_pages/login.html', {'login_type': 'student'})


def main_staff_login(request):
    return render(request, 'main_pages/login.html', {'login_type': 'staff'})

def main_register(request):
    return render(request, 'main_pages/register.html')

def student_home(request):
    today = date.today()
    ctx = {
        'today_date': timezone.now().date(),
        'progress': None,
        'progress_group': None,
        'upcoming_lessons': [],
        'attendance_rate': None,
        'pending_tasks': [],
        'recent_grades': [],
        'attendance_calendar': [{'label': (today - timedelta(days=i)).strftime('%d.%m'), 'status': 'empty'} for i in range(27, -1, -1)],
        'total_lessons': 0,
        'course_percent': 0,
    }

    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        purchased_course_ids = StudentSubscription.objects.filter(
            student=student
        ).values_list('tariff__course_id', flat=True).distinct()

        progress = StudentProgress.objects.filter(
            student=student, course_id__in=purchased_course_ids
        ).select_related('course').first()

        groups = student.study_groups.filter(course_id__in=purchased_course_ids)

        now = timezone.now()
        upcoming = Lesson.objects.filter(
            group__in=groups, scheduled_at__gte=now
        ).select_related('course', 'group').prefetch_related('sub_lessons').order_by('scheduled_at')[:5]

        total_att = Attendance.objects.filter(student=student).count()
        present_att = Attendance.objects.filter(student=student, is_present=True).count()
        att_rate = round(present_att / total_att * 100) if total_att else 0

        pending_tasks = Task.objects.filter(
            sub_lesson__lesson__group__in=groups
        ).select_related('sub_lesson__lesson__course')[:6]

        # recent grades
        recent_grades = Grade.objects.order_by('-created_at')[:4]

        # attendance calendar (last 28 days)
        today = date.today()
        calendar = []
        for i in range(27, -1, -1):
            d = today - timedelta(days=i)
            att = Attendance.objects.filter(student=student, date=d).first()
            if att:
                status = 'present' if att.is_present else 'absent'
            elif d == today:
                status = 'today'
            else:
                status = 'empty'
            calendar.append({'label': d.strftime('%d.%m'), 'status': status})

        total_lessons = 0
        course_percent = 0
        progress_group = None
        if progress:
            course = progress.course
            progress_group = student.study_groups.filter(course=course).first()
            if progress_group:
                total_lessons = progress_group.lessons.count()
                course_percent = round(progress.completed_lessons_count / total_lessons * 100) if total_lessons else 0

        ctx.update({
            'progress': progress,
            'progress_group': progress_group,
            'upcoming_lessons': upcoming,
            'attendance_rate': att_rate,
            'pending_tasks': pending_tasks,
            'recent_grades': recent_grades,
            'attendance_calendar': calendar,
            'total_lessons': total_lessons,
            'course_percent': course_percent,
        })

    return render(request, 'student/home.html', ctx)

def student_courses(request):
    return render(request, 'student/courses.html')

def student_lesson_redirect(request, lesson_id):
    """Legacy redirect — use lesson_detail instead."""
    return redirect('lesson_detail', lesson_id=lesson_id)


def student_lesson_detail(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related('course', 'group').prefetch_related(
            'sub_lessons__tasks', 'attendances'
        ),
        pk=lesson_id
    )

    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        has_access = StudentSubscription.objects.filter(
            student=student, tariff__course=lesson.course
        ).exists()
        if not has_access:
            return redirect('my-courses')

    other_lessons = Lesson.objects.filter(
        group=lesson.group
    ).order_by('scheduled_at')

    prev_lesson = other_lessons.filter(scheduled_at__lt=lesson.scheduled_at).order_by('-scheduled_at').first()
    next_lesson = other_lessons.filter(scheduled_at__gt=lesson.scheduled_at).order_by('scheduled_at').first()

    attendance = None
    lesson_grades = []
    student_grades = []

    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        attendance = Attendance.objects.filter(student=student, lesson=lesson).first()
        lesson_grades = Grade.objects.filter(
            # grades for this lesson's tasks
        ).order_by('-created_at')
        student_grades = list(Grade.objects.values('grade_value'))  # placeholder

    return render(request, 'student/lesson_detail.html', {
        'lesson': lesson,
        'other_lessons': other_lessons,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'attendance': attendance,
        'lesson_grades': lesson_grades,
        'student_grades': student_grades,
    })


def student_my_courses(request):
    courses_data = []
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        courses_data = _get_my_courses_data(student)
    return render(request, 'student/my_courses.html', {'courses_data': courses_data})

def student_assignments(request):
    tasks_data = []
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        purchased_course_ids = StudentSubscription.objects.filter(
            student=student
        ).values_list('tariff__course_id', flat=True).distinct()
        groups = student.study_groups.filter(course_id__in=purchased_course_ids)
        tasks_data = list(
            Task.objects.filter(sub_lesson__lesson__group__in=groups)
            .select_related('sub_lesson__lesson__course', 'sub_lesson__lesson__group')
            .order_by('-sub_lesson__lesson__scheduled_at')
        )
    return render(request, 'student/assignments.html', {'tasks_data': tasks_data})

def student_profile(request):
    return render(request, 'student/profile.html')

def student_ai_chat(request):
    return render(request, 'student/ai_chat.html')

def student_messages(request):
    return render(request, 'student/messages.html')

def student_news(request):
    return render(request, 'student/news.html')