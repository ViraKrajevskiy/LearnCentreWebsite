from datetime import date, timedelta
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from WebSite.models.student_model.attandance import Attendance, StudentProgress
from WebSite.models.study.grade_model import Grade
from WebSite.models.study.lesson import Course, Lesson, SubLesson, Task
from WebSite.models.study.lesson_comment import LessonComment
from WebSite.models.study.submission import TaskSubmission
from WebSite.models.pay_system.payment import StudentSubscription
from WebSite.models.notifications import Notification


def student_required(view_func):
    @wraps(view_func)
    @login_required(login_url='login')
    def _wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'student'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped

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

@student_required
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

@student_required
def student_courses(request):
    return render(request, 'student/courses.html')

# Параметры embed: без иконки канала, без посторонних рекомендаций
_YOUTUBE_EMBED_PARAMS = '?modestbranding=1&rel=0'


def _youtube_embed_url(url):
    """Преобразует ссылку на YouTube в embed-URL для просмотра прямо на сайте."""
    if not url:
        return None
    url = (url or '').strip()
    base_embed = 'https://www.youtube.com/embed'
    vid = None
    # youtu.be/VIDEO_ID
    if 'youtu.be/' in url:
        vid = url.split('youtu.be/')[-1].split('?')[0].split('/')[0]
    # youtube.com/embed/VIDEO_ID
    elif 'youtube.com/embed/' in url:
        vid = url.split('youtube.com/embed/')[-1].split('?')[0].split('/')[0]
    # youtube.com/watch?v=VIDEO_ID или m.youtube.com/...
    elif 'youtube.com' in url and 'v=' in url:
        from urllib.parse import urlparse, parse_qs
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            vid = (qs.get('v') or [None])[0]
        except Exception:
            pass
        if not vid:
            for part in url.split('?')[-1].split('&'):
                if part.startswith('v='):
                    vid = part[2:].split('#')[0]
                    break
    if not vid:
        return None
    return f'{base_embed}/{vid}{_YOUTUBE_EMBED_PARAMS}'


@student_required
def student_lesson_redirect(request, lesson_id):
    """Legacy redirect — use lesson_detail instead."""
    return redirect('lesson_detail', lesson_id=lesson_id)


@student_required
def student_lesson_detail(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related('course', 'group').prefetch_related(
            'sub_lessons__tasks'
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
        lesson_grades = []
        student_grades = []

    sub_lessons = list(lesson.sub_lessons.all())
    sub_lessons_videos = []
    for sub in sub_lessons:
        embed = _youtube_embed_url(sub.content_link) if sub.content_link else None
        sub_lessons_videos.append({
            'sub': sub,
            'content_link': sub.content_link or '',
            'embed_url': embed,
        })
    first_video = sub_lessons_videos[0] if sub_lessons_videos else None
    lesson_tasks = [(task, sub) for sub in sub_lessons for task in sub.tasks.all()]
    lesson_comments = (
        LessonComment.objects.filter(lesson=lesson)
        .select_related('student', 'student__user')
        .order_by('-created_at')
    )
    student_submissions_by_task = {}
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        task_ids = [t.id for t, _ in lesson_tasks]
        if task_ids:
            subs = (
                TaskSubmission.objects.filter(student=student, task_id__in=task_ids)
                .order_by('-created_at')
            )
            for s in subs:
                student_submissions_by_task.setdefault(s.task_id, []).append(s)
        for t, _ in lesson_tasks:
            student_submissions_by_task.setdefault(t.id, [])

    lesson_tasks_with_subs = [
        (task, sub, student_submissions_by_task.get(task.id, []))
        for task, sub in lesson_tasks
    ]

    return render(request, 'student/lesson_detail.html', {
        'lesson': lesson,
        'other_lessons': other_lessons,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'attendance': attendance,
        'lesson_grades': lesson_grades,
        'student_grades': student_grades,
        'sub_lessons_videos': sub_lessons_videos,
        'first_video': first_video,
        'lesson_tasks': lesson_tasks,
        'lesson_tasks_with_subs': lesson_tasks_with_subs,
        'lesson_comments': lesson_comments,
    })


@student_required
def student_my_courses(request):
    courses_data = []
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        courses_data = _get_my_courses_data(student)
    return render(request, 'student/my_courses.html', {'courses_data': courses_data})

@student_required
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

@student_required
def student_profile(request):
    return render(request, 'student/profile.html')

@student_required
def student_ai_chat(request):
    return render(request, 'student/ai_chat.html')

@student_required
def student_messages(request):
    return render(request, 'student/messages.html')

@student_required
def student_news(request):
    return render(request, 'student/news.html')


@student_required
def student_attendance(request):
    """Страница посещаемости студента по урокам."""
    attendance_list = []
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        purchased_course_ids = StudentSubscription.objects.filter(
            student=student
        ).values_list('tariff__course_id', flat=True).distinct()
        attendance_list = (
            Attendance.objects.filter(student=student, lesson__course_id__in=purchased_course_ids)
            .select_related('lesson', 'lesson__course', 'lesson__group')
            .order_by('-lesson__scheduled_at')
        )
    return render(request, 'student/attendance.html', {'attendance_list': attendance_list})


@require_POST
def submit_task_view(request, task_id):
    """Приём сдачи задания: текст и/или файл. Требует авторизации."""
    if not request.user.is_authenticated or not hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Войдите в аккаунт'}, status=401)
    task = get_object_or_404(Task.objects.select_related('sub_lesson__lesson'), pk=task_id)
    student = request.user.student
    has_access = StudentSubscription.objects.filter(
        student=student, tariff__course=task.sub_lesson.lesson.course
    ).exists()
    if not has_access:
        return JsonResponse({'error': 'Нет доступа к курсу'}, status=403)
    submission_count = TaskSubmission.objects.filter(student=student, task=task).count()
    if submission_count >= 3:
        return JsonResponse({'error': 'Достигнут лимит пересдач (максимум 3)'}, status=400)
    text = (request.POST.get('text') or '').strip()
    file_obj = request.FILES.get('file')
    if not text and not file_obj:
        return JsonResponse({'error': 'Добавьте текст или файл'}, status=400)
    TaskSubmission.objects.create(student=student, task=task, text=text, file=file_obj or None)
    return JsonResponse({'ok': True, 'message': 'Ответ отправлен!', 'attempts_left': 2 - submission_count})


@require_POST
def submit_lesson_comment_view(request, lesson_id):
    """Добавить комментарий к уроку (текст и/или файл). Только студенты с доступом к курсу."""
    if not request.user.is_authenticated or not hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Войдите в аккаунт'}, status=401)
    lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
    student = request.user.student
    has_access = StudentSubscription.objects.filter(
        student=student, tariff__course=lesson.course
    ).exists()
    if not has_access:
        return JsonResponse({'error': 'Нет доступа к курсу'}, status=403)
    text = (request.POST.get('text') or '').strip()
    file_obj = request.FILES.get('file')
    if not text and not file_obj:
        return JsonResponse({'error': 'Напишите комментарий или прикрепите файл'}, status=400)
    LessonComment.objects.create(lesson=lesson, student=student, text=text or '', file=file_obj or None)
    return JsonResponse({'ok': True, 'message': 'Комментарий добавлен!'})


def notifications_list_api(request):
    """Список уведомлений студента (JSON). Только для авторизованного студента."""
    if not request.user.is_authenticated or not hasattr(request.user, 'student'):
        return JsonResponse({'notifications': [], 'unread_count': 0})
    student = request.user.student
    qs = Notification.objects.filter(student=student).order_by('-created_at')[:50]
    unread_count = Notification.objects.filter(student=student, is_read=False).count()
    data = {
        'notifications': [
            {
                'id': n.id,
                'kind': n.kind,
                'title': n.title,
                'message': n.message,
                'link': n.link or '',
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat() if n.created_at else None,
            }
            for n in qs
        ],
        'unread_count': unread_count,
    }
    return JsonResponse(data)


@require_POST
def notification_mark_read_api(request):
    """Отметить уведомление прочитанным (JSON: notification_id) или все (пустой body)."""
    if not request.user.is_authenticated or not hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Войдите в аккаунт'}, status=401)
    student = request.user.student
    try:
        body = request.json() if hasattr(request, 'json') else {}
    except Exception:
        body = {}
    if not body:
        import json
        try:
            body = json.loads(request.body.decode() or '{}')
        except Exception:
            body = {}
    nid = body.get('notification_id')
    if nid:
        Notification.objects.filter(student=student, pk=nid).update(is_read=True)
    else:
        Notification.objects.filter(student=student).update(is_read=True)
    return JsonResponse({'ok': True})
