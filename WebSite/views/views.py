from datetime import date, timedelta

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from WebSite.models.student_model.attandance import Attendance, StudentProgress
from WebSite.models.study.grade_model import Grade
from WebSite.models.study.lesson import Course, Lesson, SubLesson, Task

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
    seen_course_ids = set()
    result = []
    for group in student.study_groups.select_related('course').prefetch_related('lessons'):
        course = group.course
        if course.id in seen_course_ids:
            continue
        seen_course_ids.add(course.id)
        total = group.lessons.count()
        attended = Attendance.objects.filter(student=student, lesson__group=group).count()
        next_lesson = _get_next_lesson_for_student(student, course)
        first_lesson = group.lessons.order_by('scheduled_at').first()
        continue_url = reverse('lesson', args=[next_lesson.id]) if next_lesson else (
            reverse('lesson', args=[first_lesson.id]) if first_lesson else None
        )
        result.append({
            'course': course,
            'group': group,
            'total_lessons': total,
            'completed': attended,
            'percent': round(100 * attended / total) if total else 0,
            'next_lesson': next_lesson,
            'continue_url': continue_url,
        })
    if student.course and student.course.id not in seen_course_ids:
        course = student.course
        group = student.study_groups.filter(course=course).first() or course.groups.first()
        total = group.lessons.count() if group else 0
        attended = Attendance.objects.filter(student=student, lesson__group__course=course).count()
        next_lesson = _get_next_lesson_for_student(student, course)
        first_lesson = group.lessons.order_by('scheduled_at').first() if group else None
        continue_url = reverse('lesson', args=[next_lesson.id]) if next_lesson else (
            reverse('lesson', args=[first_lesson.id]) if first_lesson else None
        )
        result.append({
            'course': course,
            'group': group,
            'total_lessons': total,
            'completed': attended,
            'percent': round(100 * attended / total) if total else 0,
            'next_lesson': next_lesson,
            'continue_url': continue_url,
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
    ctx = {
        'today_date': timezone.now().date(),
        'fallback_lessons': [
            {'time':'14:00','day':'Сегодня','title':'Python: Работа с API','course':'Программирование на Python','color':'linear-gradient(135deg,#6366f1,#8b5cf6)'},
            {'time':'10:00','day':'Завтра','title':'Машинное обучение: Введение','course':'AI и ML','color':'linear-gradient(135deg,#8b5cf6,#a855f7)'},
            {'time':'16:00','day':'Чт','title':'FastAPI: Роутинг','course':'FastAPI: Веб-разработка','color':'linear-gradient(135deg,#0ea5e9,#6366f1)'},
        ],
        'fallback_grades': [
            {'label':'Домашняя работа №5','date':'28.02.2026','value':92,'bg':'rgba(16,185,129,.15)','color':'#10b981'},
            {'label':'Тест по Python','date':'25.02.2026','value':85,'bg':'rgba(16,185,129,.15)','color':'#10b981'},
            {'label':'Проект API','date':'20.02.2026','value':74,'bg':'rgba(245,158,11,.15)','color':'#f59e0b'},
            {'label':'Контрольная работа №2','date':'14.02.2026','value':58,'bg':'rgba(239,68,68,.15)','color':'#ef4444'},
        ],
    }

    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        progress = StudentProgress.objects.filter(student=student).select_related('course').first()

        # upcoming lessons from student groups
        now = timezone.now()
        groups = student.study_groups.all()
        upcoming = Lesson.objects.filter(
            group__in=groups, scheduled_at__gte=now
        ).select_related('course', 'group').prefetch_related('sub_lessons').order_by('scheduled_at')[:5]

        # attendance rate
        total_att = Attendance.objects.filter(student=student).count()
        present_att = Attendance.objects.filter(student=student, is_present=True).count()
        att_rate = round(present_att / total_att * 100) if total_att else 0

        # pending tasks (tasks from upcoming lessons without submitted grade)
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

        # total lessons and percent
        total_lessons = 0
        course_percent = 0
        if progress:
            course = progress.course
            group = student.study_groups.filter(course=course).first()
            if group:
                total_lessons = group.lessons.count()
                course_percent = round(progress.completed_lessons_count / total_lessons * 100) if total_lessons else 0

        ctx.update({
            'progress': progress,
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

    # Other lessons in the same course/group
    other_lessons = Lesson.objects.filter(
        group=lesson.group
    ).order_by('scheduled_at')

    # Prev / next
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
    return render(request, 'student/assignments.html')

def student_profile(request):
    return render(request, 'student/profile.html')

def student_ai_chat(request):
    return render(request, 'student/ai_chat.html')

def student_messages(request):
    return render(request, 'student/messages.html')

def student_news(request):
    return render(request, 'student/news.html')