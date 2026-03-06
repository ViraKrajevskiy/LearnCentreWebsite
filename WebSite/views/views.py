from datetime import date, timedelta
from functools import wraps
from urllib.parse import urlparse, parse_qs

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
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
from WebSite.models.pay_system.payment import StudentSubscription, Payment
from WebSite.models.notifications import Notification
from WebSite.models.news_model import News
from WebSite.models.group.groups import Group


def student_required(view_func):
    @wraps(view_func)
    @login_required(login_url='login')
    def _wrapped(request, *args, **kwargs):
        if not hasattr(request.user, 'student'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped

def _get_my_courses_data(student):
    """
    Возвращает только купленные курсы студента — по подпискам (StudentSubscription).
    Оптимизировано: минимум запросов к БД (batch prefetch).
    """
    subscriptions = (
        StudentSubscription.objects
        .filter(student=student)
        .select_related('tariff__course')
        .order_by('-start_date')
    )
    seen_course_ids = set()
    courses_order = []
    for sub in subscriptions:
        course = sub.tariff.course
        if course.id in seen_course_ids:
            continue
        seen_course_ids.add(course.id)
        courses_order.append((course, sub))

    if not courses_order:
        return []

    course_ids = list(seen_course_ids)

    # Один запрос: группы студента по этим курсам
    student_groups = list(
        student.study_groups.filter(course_id__in=course_ids).select_related('course')
    )
    groups_by_course = {g.course_id: g for g in student_groups}

    # Один запрос: все группы курсов с количеством уроков и префетчем уроков по порядку
    groups_with_lessons = Group.objects.filter(course_id__in=course_ids).annotate(
        lessons_count=Count('lessons')
    ).prefetch_related(
        Prefetch('lessons', queryset=Lesson.objects.order_by('scheduled_at'))
    )
    for g in groups_with_lessons:
        if g.course_id not in groups_by_course:
            groups_by_course[g.course_id] = g
    # Для курсов без группы студента — первая группа курса
    first_group_per_course = {}
    for g in groups_with_lessons:
        if g.course_id not in first_group_per_course:
            first_group_per_course[g.course_id] = g
    for cid in course_ids:
        if cid not in groups_by_course and cid in first_group_per_course:
            groups_by_course[cid] = first_group_per_course[cid]

    # Один запрос: посещённые уроки студента по этим курсам
    attended_lesson_ids = set(
        Attendance.objects.filter(
            student=student, lesson__group__course_id__in=course_ids
        ).values_list('lesson_id', flat=True)
    )

    # Один запрос: количество посещений по курсам
    attendance_counts = {
        row['lesson__group__course_id']: row['cnt']
        for row in Attendance.objects.filter(
            student=student, lesson__group__course_id__in=course_ids
        ).values('lesson__group__course_id').annotate(cnt=Count('id'))
    }

    result = []
    for course, sub in courses_order:
        group = groups_by_course.get(course.id)
        total = group.lessons_count if group else 0
        attended = attendance_counts.get(course.id, 0)
        next_lesson = None
        first_lesson = None
        if group:
            for lesson in group.lessons.all():
                if first_lesson is None:
                    first_lesson = lesson
                if lesson.id not in attended_lesson_ids:
                    next_lesson = lesson
                    break
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

        # Prefetch course and groups with lessons_count to avoid N+1
        progress = (
            StudentProgress.objects
            .filter(student=student, course_id__in=purchased_course_ids)
            .select_related('course')
            .prefetch_related(
                Prefetch(
                    'course__groups',
                    queryset=Group.objects.annotate(lessons_count=Count('lessons'))
                )
            )
            .first()
        )

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

        # attendance calendar (last 28 days) — один запрос вместо 28
        today = date.today()
        date_from = today - timedelta(days=28)
        attendance_list = list(
            Attendance.objects.filter(
                student=student, date__gte=date_from, date__lte=today
            ).order_by('date').values_list('date', 'is_present')
        )
        attendance_by_date = {}
        for d, is_present in attendance_list:
            if d not in attendance_by_date:
                attendance_by_date[d] = is_present
        calendar = []
        for i in range(27, -1, -1):
            d = today - timedelta(days=i)
            is_present = attendance_by_date.get(d)
            if is_present is not None:
                status = 'present' if is_present else 'absent'
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
            progress_group = next((g for g in groups if g.course_id == course.id), None)
            if not progress_group and course:
                progress_group = next(iter(course.groups.all()), None)
            if progress_group:
                total_lessons = getattr(progress_group, 'lessons_count', None) or progress_group.lessons.count()
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
    courses = (
        Course.objects.all()
        .annotate(lessons_count=Count('lessons'))
        .select_related('creator')
        .order_by('-created_at')
    )
    return render(request, 'student/courses.html', {'courses': courses})


def _youtube_video_id(url):
    """Извлекает video_id из ссылки YouTube (один раз парсим, переиспользуем)."""
    if not url:
        return None
    url = (url or '').strip()
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0].split('/')[0]
    if 'youtube.com/embed/' in url:
        return url.split('youtube.com/embed/')[-1].split('?')[0].split('/')[0]
    if 'youtube.com' in url and 'v=' in url:
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            return (qs.get('v') or [None])[0]
        except Exception:
            pass
        for part in url.split('?')[-1].split('&'):
            if part.startswith('v='):
                return part[2:].split('#')[0]
    return None


# Параметры embed: без иконки канала, без посторонних рекомендаций.
_YOUTUBE_EMBED_BASE = 'https://www.youtube-nocookie.com/embed'
_YOUTUBE_EMBED_PARAMS = '?modestbranding=1&rel=0'


def _youtube_embed_url(url):
    """Преобразует ссылку на YouTube в embed-URL."""
    vid = _youtube_video_id(url)
    return f'{_YOUTUBE_EMBED_BASE}/{vid}{_YOUTUBE_EMBED_PARAMS}' if vid else None


@student_required
def student_course_detail(request, course_id):
    course = get_object_or_404(
        Course.objects.annotate(lessons_count=Count('lessons')).select_related('creator'),
        pk=course_id
    )
    trailer_url = getattr(course, 'trailer_video_url', None)
    trailer_video_id = _youtube_video_id(trailer_url) if trailer_url else None
    trailer_embed_url = f'{_YOUTUBE_EMBED_BASE}/{trailer_video_id}{_YOUTUBE_EMBED_PARAMS}' if trailer_video_id else None
    student_group = None
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student_group = request.user.student.study_groups.filter(course=course).first()
    return render(request, 'student/course_detail.html', {
        'course': course,
        'lessons_count': course.lessons_count,
        'trailer_embed_url': trailer_embed_url,
        'trailer_video_id': trailer_video_id,
        'student_group': student_group,
    })


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
def student_performance(request):
    """Страница успеваемости: оценки по курсам, сдал/не сдал по заданиям. С пагинацией."""
    from django.core.paginator import Paginator
    performance_data = []
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        progress_list = list(
            StudentProgress.objects.filter(student=student).select_related('course')
        )
        if progress_list:
            course_ids = [p.course_id for p in progress_list]
            student_groups = list(
                student.study_groups.filter(course_id__in=course_ids).select_related('course')
            )
            groups_by_course = {g.course_id: g for g in student_groups}
            submitted_task_ids = set(
                TaskSubmission.objects.filter(student=student).values_list('task_id', flat=True).distinct()
            )
            all_tasks = list(
                Task.objects.filter(sub_lesson__lesson__course_id__in=course_ids)
                .select_related('sub_lesson__lesson')
                .order_by('sub_lesson__lesson__scheduled_at', 'sub_lesson__order', 'id')
            )
            tasks_by_course = {}
            for t in all_tasks:
                cid = t.sub_lesson.lesson.course_id
                tasks_by_course.setdefault(cid, []).append(t)
            for progress in progress_list:
                course = progress.course
                student_group = groups_by_course.get(course.id)
                tasks_in_course = tasks_by_course.get(course.id, [])
                tasks_with_status = [
                    {'task': t, 'submitted': t.id in submitted_task_ids}
                    for t in tasks_in_course
                ]
                performance_data.append({
                    'course': course,
                    'progress': progress,
                    'student_group': student_group,
                    'tasks_total': len(tasks_in_course),
                    'tasks_submitted': sum(1 for tw in tasks_with_status if tw['submitted']),
                    'tasks_with_status': tasks_with_status,
                })
    paginator = Paginator(performance_data, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'student/performance.html', {'page_obj': page_obj, 'performance_data': page_obj.object_list})

@student_required
def student_profile(request):
    user = request.user
    show_proftest_prompt = user.proftest_offer_shown_at is None
    if show_proftest_prompt:
        from django.utils import timezone
        user.proftest_offer_shown_at = timezone.now()
        user.save(update_fields=['proftest_offer_shown_at'])

    payment_history = []
    performance_data = []
    if hasattr(user, 'student'):
        student = user.student
        payment_history = (
            Payment.objects.filter(student=student)
            .select_related('subscription', 'subscription__tariff', 'subscription__tariff__course')
            .order_by('-created_at')[:50]
        )
        # Успеваемость: по каждому курсу — прогресс и сданные/несданные задания (batch)
        progress_list = list(
            StudentProgress.objects.filter(student=student).select_related('course')
        )
        if progress_list:
            course_ids = [p.course_id for p in progress_list]
            tasks_total_by_course = dict(
                Task.objects.filter(sub_lesson__lesson__course_id__in=course_ids)
                .values('sub_lesson__lesson__course_id')
                .annotate(total=Count('id'))
                .values_list('sub_lesson__lesson__course_id', 'total')
            )
            submitted_by_course = dict(
                TaskSubmission.objects.filter(
                    student=student,
                    task__sub_lesson__lesson__course_id__in=course_ids
                )
                .values('task__sub_lesson__lesson__course_id')
                .annotate(cnt=Count('task', distinct=True))
                .values_list('task__sub_lesson__lesson__course_id', 'cnt')
            )
            for progress in progress_list:
                cid = progress.course_id
                performance_data.append({
                    'course': progress.course,
                    'progress': progress,
                    'tasks_total': tasks_total_by_course.get(cid, 0),
                    'tasks_submitted': submitted_by_course.get(cid, 0),
                })

    return render(request, 'student/profile.html', {
        'show_proftest_prompt': show_proftest_prompt,
        'payment_history': payment_history,
        'performance_data': performance_data,
    })

@student_required
def student_ai_chat(request):
    return render(request, 'student/ai_chat.html')

@student_required
def student_messages(request):
    return render(request, 'student/messages.html')

@student_required
def student_news(request):
    news_list = News.objects.filter(is_published=True).order_by('-created_at')[:50]
    return render(request, 'student/news.html', {'news_list': news_list})


@student_required
def student_news_detail(request, pk):
    news_item = get_object_or_404(News.objects.filter(is_published=True), pk=pk)
    return render(request, 'student/news_detail.html', {'news_item': news_item})


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


@student_required
def upload_receipt_view(request, payment_id):
    """Загрузка чека об оплате. POST: file (чек). Платёж должен принадлежать студенту."""
    if request.method != 'POST':
        return redirect('profile')
    payment = get_object_or_404(Payment, pk=payment_id)
    if payment.student_id != request.user.student.id:
        return JsonResponse({'error': 'Нет доступа к этому платежу'}, status=403)
    file_obj = request.FILES.get('receipt') or request.FILES.get('file')
    if not file_obj:
        return JsonResponse({'error': 'Выберите файл чека'}, status=400)
    payment.receipt = file_obj
    payment.save(update_fields=['receipt'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax'):
        return JsonResponse({'ok': True, 'message': 'Чек загружен', 'receipt_url': payment.receipt.url if payment.receipt else None})
    return redirect('profile')


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


def _get_student_from_request(request):
    """Возвращает студента из request: сессия или JWT (Bearer)."""
    if request.user.is_authenticated and getattr(request.user, 'student', None):
        return request.user.student
    auth = request.META.get('HTTP_AUTHORIZATION') or ''
    if auth.startswith('Bearer '):
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth import get_user_model
        try:
            token = AccessToken(auth[7:])
            user = get_user_model().objects.get(pk=token['user_id'])
            if hasattr(user, 'student'):
                return user.student
        except Exception:
            pass
    return None


def notifications_list_api(request):
    """Список уведомлений студента (JSON). Поддержка сессии и JWT (Bearer)."""
    student = _get_student_from_request(request)
    if not student:
        return JsonResponse({'notifications': [], 'unread_count': 0})
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
    """Отметить уведомление прочитанным (JSON: notification_id) или все (пустой body). Сохраняется в БД."""
    student = _get_student_from_request(request)
    if not student:
        return JsonResponse({'error': 'Войдите в аккаунт'}, status=401)
    import json
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        body = {}
    nid = body.get('notification_id')
    if nid:
        Notification.objects.filter(student=student, pk=nid).update(is_read=True)
    else:
        Notification.objects.filter(student=student).update(is_read=True)
    return JsonResponse({'ok': True})
