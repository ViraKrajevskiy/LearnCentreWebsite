from datetime import date, timedelta
from functools import wraps
from urllib.parse import urlparse, parse_qs

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
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
from WebSite.models.study.tarif_system import Tariff
from WebSite.models.notifications import Notification
from WebSite.models.news_model import News
from WebSite.models.group.groups import Group, GroupChatMessage
from WebSite.utils.input_validation import sanitize_text_field, validate_int_id


# --- HELPERS / DECORATORS ---

def student_required(view_func):
    @wraps(view_func)
    @login_required(login_url='login')
    def _wrapped(request, *args, **kwargs):
        if request.user.role in ('teacher', 'mentor', 'staff'):
            return redirect('teacher_home')
        if not hasattr(request.user, 'student'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def teacher_required(view_func):
    """Доступ только для учителей, менторов и staff. Редирект на логин при отсутствии прав."""
    @wraps(view_func)
    @login_required(login_url='login')
    def _wrapped(request, *args, **kwargs):
        if request.user.role not in ('teacher', 'mentor', 'staff'):
            if hasattr(request.user, 'student'):
                return redirect('student_home')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _teacher_or_mentor_groups(user):
    """Группы, в которых user является учителем или ментором."""
    teacher_profile = getattr(user, 'teachers', None)
    if not teacher_profile:
        return Group.objects.none()
    return Group.objects.filter(
        Q(teacher=teacher_profile) | Q(mentor=teacher_profile)
    ).select_related('course', 'teacher', 'mentor').distinct()


def _teacher_only_groups(user):
    """Группы, в которых user является именно учителем (для создания уроков)."""
    teacher_profile = getattr(user, 'teachers', None)
    if not teacher_profile:
        return Group.objects.none()
    return Group.objects.filter(teacher=teacher_profile).select_related('course', 'teacher', 'mentor')


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


def _lesson_completed(student, lesson):
    """Урок считается сданным, если есть посещение (Attendance)."""
    return Attendance.objects.filter(student=student, lesson=lesson).exists()


def _get_open_lesson_ids(student, group, learning_mode, now=None):
    """
    Возвращает set id уроков группы, которые открыты студенту.
    - smooth: все уроки открыты.
    - active: последовательно — урок открыт, если сдан предыдущий и наступило scheduled_at этого урока.
    """
    if now is None:
        now = timezone.now()
    lessons = list(Lesson.objects.filter(group=group).order_by('scheduled_at'))
    if not lessons:
        return set()
    if learning_mode == Tariff.LEARNING_SMOOTH:
        return {l.id for l in lessons}
    # active: по порядку — открыт, если наступило время и предыдущий сдан
    open_ids = set()
    for i, lesson in enumerate(lessons):
        if lesson.scheduled_at and lesson.scheduled_at > now:
            break
        if i == 0:
            open_ids.add(lesson.id)
        elif _lesson_completed(student, lessons[i - 1]):
            open_ids.add(lesson.id)
        else:
            break
    return open_ids


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
    groups_with_lessons = list(Group.objects.filter(course_id__in=course_ids).annotate(
        lessons_count=Count('lessons')
    ).prefetch_related(
        Prefetch('lessons', queryset=Lesson.objects.order_by('scheduled_at'))
    ))
    # Количество уроков по курсу (берём у любой группы курса — у аннотированных)
    lessons_count_by_course = {g.course_id: g.lessons_count for g in groups_with_lessons}
    # Подменить группы в groups_by_course на аннотированные с префетчем уроков, где есть
    annotated_by_course = {g.course_id: g for g in groups_with_lessons}
    for cid in course_ids:
        if cid in annotated_by_course:
            groups_by_course[cid] = annotated_by_course[cid]
        elif cid not in groups_by_course and groups_with_lessons:
            for g in groups_with_lessons:
                if g.course_id == cid:
                    groups_by_course[cid] = g
                    break

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
        total = lessons_count_by_course.get(course.id, 0) if group else 0
        attended = attendance_counts.get(course.id, 0)
        next_lesson = None
        first_lesson = None
        learning_mode = getattr(sub.tariff, 'learning_mode', Tariff.LEARNING_SMOOTH)
        open_lesson_ids = _get_open_lesson_ids(student, group, learning_mode) if group else set()
        if group:
            for lesson in group.lessons.all():
                if first_lesson is None:
                    first_lesson = lesson
                # Следующий урок: первый открытый и ещё не сданный
                if lesson.id in open_lesson_ids and lesson.id not in attended_lesson_ids:
                    next_lesson = lesson
                    break
        continue_url = (
            reverse('lesson_detail', args=[next_lesson.id]) if next_lesson else
            (reverse('lesson_detail', args=[first_lesson.id]) if first_lesson and first_lesson.id in open_lesson_ids else None)
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
            'open_lesson_ids': open_lesson_ids,
            'learning_mode': learning_mode,
        })
    return result


def _youtube_video_id(url):
    """Извлекает video_id из ссылки YouTube."""
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


_YOUTUBE_EMBED_BASE = 'https://www.youtube-nocookie.com/embed'
_YOUTUBE_EMBED_PARAMS = '?modestbranding=1&rel=0'


def _youtube_embed_url(url):
    """Преобразует ссылку на YouTube в embed-URL."""
    vid = _youtube_video_id(url)
    return f'{_YOUTUBE_EMBED_BASE}/{vid}{_YOUTUBE_EMBED_PARAMS}' if vid else None


# --- MAIN PAGES (GUESTS) ---

def main_home(request):
    return render(request, 'main_pages/home.html')


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
    return render(request, 'login_registration/login.html', {'login_type': 'student'})


def main_staff_login(request):
    return render(request, 'login_registration/login.html', {'login_type': 'staff'})


def main_register(request):
    return render(request, 'main_pages/register.html')


# --- STUDENT VIEWS ---

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

        # optimization: get attendance counts in one query
        att_counts = Attendance.objects.filter(student=student).aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(is_present=True))
        )
        total_att = att_counts['total']
        present_att = att_counts['present']
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


@student_required
def student_my_courses(request):
    courses_data = []
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        courses_data = _get_my_courses_data(student)
    return render(request, 'student/my_courses.html', {'courses_data': courses_data})


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
        Lesson.objects.select_related(
            'course', 'course__creator', 'group', 'group__teacher', 'group__mentor', 'created_by'
        ).prefetch_related(
            'sub_lessons__tasks'
        ),
        pk=lesson_id
    )

    student = request.user.student
    sub = StudentSubscription.objects.filter(
        student=student, tariff__course=lesson.course
    ).select_related('tariff').first()
    if not sub:
        return redirect('my-courses')

    learning_mode = getattr(sub.tariff, 'learning_mode', Tariff.LEARNING_SMOOTH)
    open_lesson_ids = _get_open_lesson_ids(student, lesson.group, learning_mode)
    lesson_locked = lesson.id not in open_lesson_ids
    unlock_at = lesson.scheduled_at if lesson_locked else None

    other_lessons = list(Lesson.objects.filter(group=lesson.group).order_by('scheduled_at'))
    other_lessons_with_lock = [
        {
            'lesson': l,
            'is_locked': l.id not in open_lesson_ids,
            'unlock_at': l.scheduled_at,
        }
        for l in other_lessons
    ]

    try:
        idx = next(i for i, l in enumerate(other_lessons) if l.id == lesson.id)
    except StopIteration:
        idx = 0
    prev_lesson = other_lessons[idx - 1] if idx > 0 else None
    next_lesson = other_lessons[idx + 1] if idx < len(other_lessons) - 1 else None

    attendance = None
    lesson_grades = []
    student_grades = []

    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        attendance = Attendance.objects.filter(student=student, lesson=lesson).first()
        # Grade model has no lesson/student FK; show no per-lesson grades here
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
    lesson_comments = list(
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

    lesson_teacher = getattr(lesson.group, 'teacher', None)
    lesson_mentor = getattr(lesson.group, 'mentor', None)
    lesson_created_by = getattr(lesson, 'created_by', None) or getattr(lesson.course, 'creator', None)

    return render(request, 'student/lesson_detail.html', {
        'lesson': lesson,
        'other_lessons': other_lessons,
        'other_lessons_with_lock': other_lessons_with_lock,
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
        'lesson_teacher': lesson_teacher,
        'lesson_mentor': lesson_mentor,
        'lesson_created_by': lesson_created_by,
        'lesson_locked': lesson_locked,
        'unlock_at': unlock_at,
        'learning_mode': learning_mode,
    })


def _user_can_access_group_chat(user, group):
    """Студент группы, учитель или ментор группы могут писать в чат."""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'student') and user.student and group.students.filter(pk=user.student.pk).exists():
        return True
    if getattr(group, 'teacher', None) and group.teacher and getattr(group.teacher, 'user', None) and group.teacher.user_id == user.pk:
        return True
    if getattr(group, 'mentor', None) and group.mentor and getattr(group.mentor, 'user', None) and group.mentor.user_id == user.pk:
        return True
    return False


def _notify_students_about_chat_message(group, author, text):
    """Создаёт уведомления для всех студентов группы о новом сообщении в чате (кроме автора)."""
    author_student_id = getattr(author, 'student_id', None) or (author.student.pk if hasattr(author, 'student') and author.student else None)
    students = group.students.all()
    author_name = (author.get_full_name() or author.email or 'Участник').strip() or 'Участник'
    msg_preview = (text or '').strip()[:120]
    if len((text or '').strip()) > 120:
        msg_preview += '…'
    title = f'Чат: {group.name}'
    message = f'От {author_name}: {msg_preview}' if msg_preview else f'От {author_name}'
    link = reverse('messages') + f'?group={group.pk}'
    for student in students:
        if author_student_id and student.pk == author_student_id:
            continue
        Notification.objects.create(
            student=student,
            kind=Notification.KIND_CHAT_MESSAGE,
            title=title,
            message=message,
            link=link,
        )


@student_required
def student_group_chat(request, group_id):
    """Чат группы: студенты группы + учитель + ментор. Список сообщений, отправка, редактирование и удаление."""
    group = get_object_or_404(
        Group.objects.select_related('course', 'teacher', 'mentor'),
        pk=group_id
    )
    if not _user_can_access_group_chat(request.user, group):
        return redirect('my-courses')
    messages_list = list(
        GroupChatMessage.objects.filter(group=group)
        .select_related('author')
        .order_by('created_at')[:200]
    )
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete':
            msg_id = request.POST.get('message_id')
            if msg_id:
                try:
                    msg = GroupChatMessage.objects.get(pk=int(msg_id), group=group, author=request.user)
                    msg.delete()
                except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                    pass
        elif action == 'edit':
            msg_id = request.POST.get('message_id')
            text = (request.POST.get('text') or '').strip()
            if msg_id and text and len(text) <= 5000:
                try:
                    msg = GroupChatMessage.objects.get(pk=int(msg_id), group=group, author=request.user)
                    msg.text = text
                    msg.save()
                except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                    pass
        else:
            text = (request.POST.get('text') or '').strip()
            if text and len(text) <= 5000:
                GroupChatMessage.objects.create(group=group, author=request.user, text=text)
                _notify_students_about_chat_message(group, request.user, text)
        return redirect('group_chat', group_id=group_id)
    edit_message_id = None
    edit_message_text = None
    edit_param = request.GET.get('edit')
    if edit_param:
        try:
            em = GroupChatMessage.objects.get(pk=int(edit_param), group=group, author=request.user)
            edit_message_id = em.pk
            edit_message_text = em.text
        except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
            pass
    return render(request, 'student/group_chat.html', {
        'group': group,
        'chat_messages': messages_list,
        'edit_message_id': edit_message_id,
        'edit_message_text': edit_message_text or '',
    })


@student_required
@require_POST
def clear_my_group_chat(request, group_id):
    """Удалить все свои сообщения в чате группы. Редирект на next или в личные сообщения."""
    group = get_object_or_404(Group.objects.select_related('course'), pk=group_id)
    if not _user_can_access_group_chat(request.user, group):
        return redirect('my-courses')
    GroupChatMessage.objects.filter(group=group, author=request.user).delete()
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect(reverse('messages') + f'?group={group_id}')


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

    return render(request, 'student/profile.html', {
        'show_proftest_prompt': show_proftest_prompt,
    })


@student_required
def student_payments(request):
    """Отдельная страница: история оплат и загрузка чеков."""
    student = request.user.student
    payment_history = (
        Payment.objects.filter(student=student)
        .select_related('subscription', 'subscription__tariff', 'subscription__tariff__course')
        .order_by('-created_at')[:50]
    )
    return render(request, 'student/payments.html', {
        'payment_history': payment_history,
    })


@student_required
def student_ai_chat(request):
    return render(request, 'student/ai_chat.html')


@student_required
def student_messages(request):
    """Личные сообщения: чаты групп (переписка с учителем/ментором по каждой группе)."""
    student = request.user.student
    purchased_course_ids = StudentSubscription.objects.filter(
        student=student
    ).values_list('tariff__course_id', flat=True).distinct()
    my_groups = list(
        Group.objects.filter(students=student, course_id__in=purchased_course_ids)
        .select_related('course', 'teacher', 'mentor')
        .order_by('-start_date')
    )
    selected_group = None
    chat_messages = []
    group_id_param = request.GET.get('group') or request.POST.get('group_id')
    if request.method == 'POST' and group_id_param:
        try:
            gid = int(group_id_param)
            g = next((g for g in my_groups if g.pk == gid), None)
            if not g:
                pass
            elif request.POST.get('action') == 'delete':
                msg_id = request.POST.get('message_id')
                if msg_id:
                    try:
                        msg = GroupChatMessage.objects.get(pk=int(msg_id), group=g, author=request.user)
                        msg.delete()
                    except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                        pass
                return redirect(reverse('messages') + f'?group={gid}')
            elif request.POST.get('action') == 'edit':
                msg_id = request.POST.get('message_id')
                text = (request.POST.get('text') or '').strip()
                if msg_id and text and len(text) <= 5000:
                    try:
                        msg = GroupChatMessage.objects.get(pk=int(msg_id), group=g, author=request.user)
                        msg.text = text
                        msg.save()
                    except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                        pass
                return redirect(reverse('messages') + f'?group={gid}')
            else:
                text = (request.POST.get('text') or '').strip()
                if text and len(text) <= 5000:
                    GroupChatMessage.objects.create(group=g, author=request.user, text=text)
                    _notify_students_about_chat_message(g, request.user, text)
                return redirect(reverse('messages') + f'?group={gid}')
        except (ValueError, TypeError):
            pass
    edit_message_id = None
    edit_message_text = None
    if group_id_param:
        try:
            gid = int(group_id_param)
            selected_group = next((g for g in my_groups if g.pk == gid), None)
            if selected_group:
                chat_messages = list(
                    GroupChatMessage.objects.filter(group=selected_group)
                    .select_related('author')
                    .order_by('created_at')[:200]
                )
                edit_param = request.GET.get('edit')
                if edit_param:
                    try:
                        em = GroupChatMessage.objects.get(
                            pk=int(edit_param), group=selected_group, author=request.user
                        )
                        edit_message_id = em.pk
                        edit_message_text = em.text
                    except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                        pass
        except (ValueError, TypeError):
            pass
    return render(request, 'student/messages.html', {
        'my_groups': my_groups,
        'selected_group': selected_group,
        'chat_messages': chat_messages,
        'edit_message_id': edit_message_id,
        'edit_message_text': edit_message_text or '',
    })


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


# --- TEACHER / MENTOR VIEWS ---

@teacher_required
def teacher_home(request):
    """Главная кабинета учителя/ментора."""
    my_groups = list(_teacher_or_mentor_groups(request.user).order_by('-start_date')[:10])
    is_mentor = getattr(request.user, 'teachers', None) and getattr(request.user.teachers, 'choices', None) == 'mentor'
    return render(request, 'teacher/home.html', {
        'my_groups': my_groups,
        'is_mentor': is_mentor,
        'today_date': timezone.now().date(),
    })


@teacher_required
def teacher_my_groups(request):
    """Мои группы (где я учитель или ментор)."""
    my_groups = list(_teacher_or_mentor_groups(request.user).order_by('-start_date'))
    is_mentor = getattr(request.user, 'teachers', None) and getattr(request.user.teachers, 'choices', None) == 'mentor'
    return render(request, 'teacher/my_groups.html', {
        'my_groups': my_groups,
        'is_mentor': is_mentor,
    })


@teacher_required
def teacher_messages(request):
    """Сообщения: чаты групп (учитель/ментор видит те же чаты, что и студенты группы)."""
    my_groups = list(_teacher_or_mentor_groups(request.user).order_by('-start_date'))
    selected_group = None
    chat_messages = []
    group_id_param = request.GET.get('group') or request.POST.get('group_id')
    if request.method == 'POST' and group_id_param:
        try:
            gid = int(group_id_param)
            g = next((g for g in my_groups if g.pk == gid), None)
            if g:
                if request.POST.get('action') == 'delete':
                    msg_id = request.POST.get('message_id')
                    if msg_id:
                        try:
                            msg = GroupChatMessage.objects.get(pk=int(msg_id), group=g, author=request.user)
                            msg.delete()
                        except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                            pass
                    return redirect(reverse('teacher_messages') + f'?group={gid}')
                elif request.POST.get('action') == 'edit':
                    msg_id = request.POST.get('message_id')
                    text = (request.POST.get('text') or '').strip()
                    if msg_id and text and len(text) <= 5000:
                        try:
                            msg = GroupChatMessage.objects.get(pk=int(msg_id), group=g, author=request.user)
                            msg.text = text
                            msg.save()
                        except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                            pass
                    return redirect(reverse('teacher_messages') + f'?group={gid}')
                else:
                    text = (request.POST.get('text') or '').strip()
                    if text and len(text) <= 5000:
                        GroupChatMessage.objects.create(group=g, author=request.user, text=text)
                        _notify_students_about_chat_message(g, request.user, text)
                return redirect(reverse('teacher_messages') + f'?group={gid}')
        except (ValueError, TypeError):
            pass
    edit_message_id = None
    edit_message_text = None
    if group_id_param:
        try:
            gid = int(group_id_param)
            selected_group = next((g for g in my_groups if g.pk == gid), None)
            if selected_group:
                chat_messages = list(
                    GroupChatMessage.objects.filter(group=selected_group)
                    .select_related('author')
                    .order_by('created_at')[:200]
                )
                edit_param = request.GET.get('edit')
                if edit_param:
                    try:
                        em = GroupChatMessage.objects.get(
                            pk=int(edit_param), group=selected_group, author=request.user
                        )
                        edit_message_id = em.pk
                        edit_message_text = em.text
                    except (GroupChatMessage.DoesNotExist, ValueError, TypeError):
                        pass
        except (ValueError, TypeError):
            pass
    return render(request, 'teacher/messages.html', {
        'my_groups': my_groups,
        'selected_group': selected_group,
        'chat_messages': chat_messages,
        'edit_message_id': edit_message_id,
        'edit_message_text': edit_message_text or '',
    })


@teacher_required
def teacher_homework(request):
    """Проверка ДЗ и заданий по группам. Ментор не может выставлять оценку за контрольные."""
    from WebSite.models.study.lesson import Task

    my_groups = list(_teacher_or_mentor_groups(request.user).order_by('-start_date'))
    teacher_profile = getattr(request.user, 'teachers', None)
    is_mentor = teacher_profile and getattr(teacher_profile, 'choices', None) == 'mentor'

    selected_group = None
    submissions = []

    group_id_param = request.GET.get('group') or request.POST.get('group_id')
    if request.method == 'POST' and request.POST.get('action') == 'grade':
        sub_id = request.POST.get('submission_id')
        grade_val = request.POST.get('grade_value')
        redirect_group_id = request.POST.get('group_id') or request.GET.get('group')
        try:
            sub = TaskSubmission.objects.select_related('task', 'task__sub_lesson', 'task__sub_lesson__lesson').get(pk=int(sub_id))
        except (TaskSubmission.DoesNotExist, ValueError, TypeError):
            pass
        else:
            gr = sub.task.sub_lesson.lesson.group
            if gr and any(g.pk == gr.pk for g in my_groups):
                redirect_group_id = str(gr.id)
                can_grade = True
                if sub.task.task_type == Task.TaskType.CONTROL and is_mentor:
                    can_grade = False
                if can_grade and grade_val is not None:
                    try:
                        gv = int(grade_val)
                        max_s = getattr(sub.task, 'max_score', 100) or 100
                        if 0 <= gv <= min(100, max_s):
                            sub.grade_value = gv
                            sub.graded_at = timezone.now()
                            sub.graded_by = request.user
                            sub.save(update_fields=['grade_value', 'graded_at', 'graded_by'])
                    except (ValueError, TypeError):
                        pass
        if redirect_group_id:
            return redirect(reverse('teacher_homework') + f'?group={redirect_group_id}')
        return redirect('teacher_homework')

    if group_id_param:
        try:
            gid = int(group_id_param)
            selected_group = next((g for g in my_groups if g.pk == gid), None)
            if selected_group:
                submissions = list(
                    TaskSubmission.objects
                    .filter(
                        task__sub_lesson__lesson__group=selected_group,
                        student__study_groups=selected_group,
                    )
                    .select_related('student', 'student__user', 'task', 'task__sub_lesson', 'task__sub_lesson__lesson', 'graded_by')
                    .distinct()
                    .order_by('-created_at')
                )
        except (ValueError, TypeError):
            pass

    return render(request, 'teacher/homework.html', {
        'my_groups': my_groups,
        'selected_group': selected_group,
        'submissions': submissions,
        'is_mentor': is_mentor,
    })


@teacher_required
def teacher_submission_detail(request, submission_id):
    """Просмотр сдачи в отдельном окне: полный текст ответа и скачивание файла."""
    sub = get_object_or_404(
        TaskSubmission.objects.select_related(
            'student', 'student__user', 'task', 'task__sub_lesson', 'task__sub_lesson__lesson', 'task__sub_lesson__lesson__group', 'graded_by'
        ),
        pk=submission_id
    )
    group = sub.task.sub_lesson.lesson.group
    my_group_ids = list(_teacher_or_mentor_groups(request.user).values_list('pk', flat=True))
    if group.pk not in my_group_ids:
        return redirect('teacher_homework')
    return render(request, 'teacher/submission_detail.html', {
        'sub': sub,
        'group': group,
    })


@teacher_required
def teacher_lessons_panel(request):
    """Отдел «Урок»: три панели — создание урока, домашнее задание к уроку, задание для урока (только учитель)."""
    teacher_profile_obj = getattr(request.user, 'teachers', None)
    is_teacher = teacher_profile_obj and getattr(teacher_profile_obj, 'choices', None) == 'teacher'
    if not is_teacher:
        return redirect('teacher_home')

    teaching_groups = list(_teacher_only_groups(request.user).order_by('-start_date'))
    teaching_group_ids = [g.pk for g in teaching_groups]
    lessons = list(
        Lesson.objects.filter(group_id__in=teaching_group_ids)
        .select_related('group', 'group__course')
        .prefetch_related(Prefetch('sub_lessons', queryset=SubLesson.objects.order_by('order')))
        .order_by('-scheduled_at')
    )
    lessons_list = [{'id': l.id, 'title': l.title, 'group_name': l.group.name} for l in lessons]
    sub_lessons_by_lesson = {}
    for l in lessons:
        sub_lessons_by_lesson[l.id] = [{'id': s.id, 'title': s.title} for s in l.sub_lessons.all()]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_lesson':
            group_id = request.POST.get('group_id')
            title = (request.POST.get('title') or '').strip()
            scheduled = request.POST.get('scheduled_at')
            video_url = (request.POST.get('lesson_video_url') or '').strip()
            group = next((g for g in teaching_groups if str(g.pk) == group_id), None)
            if not group or not title:
                return render(request, 'teacher/lessons_panel.html', {
                    'teaching_groups': teaching_groups,
                    'lessons_list': lessons_list,
                    'sub_lessons_by_lesson': sub_lessons_by_lesson,
                    'error': 'Выберите группу и введите название урока.',
                })
            try:
                from datetime import datetime
                scheduled_at = timezone.make_aware(datetime.fromisoformat(scheduled.replace('Z', '+00:00'))) if scheduled else timezone.now() + timedelta(days=7)
            except Exception:
                scheduled_at = timezone.now() + timedelta(days=7)
            lesson = Lesson.objects.create(
                course=group.course,
                group=group,
                title=title,
                scheduled_at=scheduled_at,
                video_url=video_url,
                created_by=teacher_profile_obj,
            )
            return redirect('teacher_lesson_edit', lesson_id=lesson.pk)
        if action in ('add_homework_task', 'add_lesson_task'):
            lesson_id = request.POST.get('lesson_id')
            sub_lesson_id = request.POST.get('sub_lesson_id')
            desc = (request.POST.get('description') or '').strip()
            max_score = int(request.POST.get('max_score') or 100)
            task_video_url = (request.POST.get('task_video_url') or '').strip()
            task_file = request.FILES.get('task_attachment')
            task_type = Task.TaskType.HOMEWORK if action == 'add_homework_task' else Task.TaskType.LESSON
            if not lesson_id or not sub_lesson_id or not desc:
                return render(request, 'teacher/lessons_panel.html', {
                    'teaching_groups': teaching_groups,
                    'lessons_list': lessons_list,
                    'sub_lessons_by_lesson': sub_lessons_by_lesson,
                    'error': 'Выберите урок и подурок, введите описание задания.',
                })
            lesson = get_object_or_404(Lesson, pk=lesson_id)
            if lesson.group_id not in teaching_group_ids:
                return redirect('teacher_home')
            sub = get_object_or_404(SubLesson, pk=sub_lesson_id, lesson=lesson)
            task = Task(sub_lesson=sub, description=desc, max_score=max_score, task_type=task_type, video_url=task_video_url)
            if task_file:
                task.attachment = task_file
            task.save()
            return redirect('teacher_lesson_edit', lesson_id=lesson.id)

    return render(request, 'teacher/lessons_panel.html', {
        'teaching_groups': teaching_groups,
        'lessons_list': lessons_list,
        'sub_lessons_by_lesson': sub_lessons_by_lesson,
    })


@teacher_required
def teacher_lesson_create(request):
    """Создать урок (только учитель). Выбор группы, название, дата — затем переход к добавлению подуроков и заданий."""
    teacher_profile_obj = getattr(request.user, 'teachers', None)
    is_teacher = teacher_profile_obj and getattr(teacher_profile_obj, 'choices', None) == 'teacher'
    if not is_teacher:
        return redirect('teacher_home')

    teaching_groups = list(_teacher_only_groups(request.user).order_by('-start_date'))
    if not teaching_groups:
        return render(request, 'teacher/lesson_create.html', {'teaching_groups': [], 'error': 'Вам не назначены группы как учителю.'})

    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        title = (request.POST.get('title') or '').strip()
        scheduled = request.POST.get('scheduled_at')
        group = next((g for g in teaching_groups if str(g.pk) == group_id), None)
        if not group or not title:
            return render(request, 'teacher/lesson_create.html', {
                'teaching_groups': teaching_groups,
                'error': 'Выберите группу и введите название урока.',
            })
        try:
            from datetime import datetime
            scheduled_at = timezone.make_aware(datetime.fromisoformat(scheduled.replace('Z', '+00:00'))) if scheduled else timezone.now() + timedelta(days=7)
        except Exception:
            scheduled_at = timezone.now() + timedelta(days=7)
        lesson = Lesson.objects.create(
            course=group.course,
            group=group,
            title=title,
            scheduled_at=scheduled_at,
            created_by=teacher_profile_obj,
        )
        return redirect('teacher_lesson_edit', lesson_id=lesson.pk)

    return render(request, 'teacher/lesson_create.html', {
        'teaching_groups': teaching_groups,
    })


@teacher_required
def teacher_lesson_edit(request, lesson_id):
    """Редактирование урока: подуроки и задания (только учитель)."""
    from WebSite.models.study.lesson import Task

    teacher_profile_obj = getattr(request.user, 'teachers', None)
    is_teacher = teacher_profile_obj and getattr(teacher_profile_obj, 'choices', None) == 'teacher'
    if not is_teacher:
        return redirect('teacher_home')

    lesson = get_object_or_404(
        Lesson.objects.select_related('course', 'group', 'created_by'),
        pk=lesson_id
    )
    teaching_group_ids = list(_teacher_only_groups(request.user).values_list('pk', flat=True))
    if lesson.group_id not in teaching_group_ids:
        return redirect('teacher_lesson_create')

    sub_lessons = list(lesson.sub_lessons.all().order_by('order'))
    sub_lessons_data = []
    for sub in sub_lessons:
        tasks = list(sub.tasks.all().order_by('id'))
        sub_lessons_data.append((sub, tasks))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_lesson':
            title = (request.POST.get('lesson_title') or '').strip()
            video_url = (request.POST.get('lesson_video_url') or '').strip()
            scheduled_raw = request.POST.get('lesson_scheduled_at') or ''
            if title:
                lesson.title = title
            if scheduled_raw:
                try:
                    from django.utils.dateparse import parse_datetime
                    parsed = parse_datetime(scheduled_raw)
                    if parsed:
                        lesson.scheduled_at = parsed
                except Exception:
                    pass
            lesson.video_url = video_url
            lesson.save(update_fields=['title', 'scheduled_at', 'video_url'])
            return redirect('teacher_lesson_edit', lesson_id=lesson_id)
        if action == 'update_sublesson':
            sub_id = request.POST.get('sub_lesson_id')
            stitle = (request.POST.get('sub_title') or '').strip()
            slink = (request.POST.get('content_link') or '').strip()
            sub = next((s for s, _ in sub_lessons_data if str(s.pk) == sub_id), None)
            if sub:
                if stitle:
                    sub.title = stitle
                if slink:
                    sub.content_link = slink
                sub.save(update_fields=['title', 'content_link'])
            return redirect('teacher_lesson_edit', lesson_id=lesson_id)
        if action == 'add_sublesson':
            stitle = (request.POST.get('sub_title') or '').strip()
            slink = (request.POST.get('content_link') or '').strip()
            order = int(request.POST.get('order') or len(sub_lessons_data) + 1)
            if stitle and slink:
                SubLesson.objects.create(lesson=lesson, title=stitle, content_link=slink, order=order)
            return redirect('teacher_lesson_edit', lesson_id=lesson_id)
        if action == 'add_task':
            sub_id = request.POST.get('sub_lesson_id')
            desc = (request.POST.get('description') or '').strip()
            task_type = request.POST.get('task_type') or Task.TaskType.LESSON
            max_score = int(request.POST.get('max_score') or 100)
            task_video_url = (request.POST.get('task_video_url') or '').strip()
            task_file = request.FILES.get('task_attachment')
            sub = next((s for s, _ in sub_lessons_data if str(s.pk) == sub_id), None)
            if sub and desc:
                task = Task(
                    sub_lesson=sub,
                    description=desc,
                    max_score=max_score,
                    task_type=task_type,
                    video_url=task_video_url or '',
                )
                if task_file:
                    task.attachment = task_file
                task.save()
            return redirect('teacher_lesson_edit', lesson_id=lesson_id)

    return render(request, 'teacher/lesson_edit.html', {
        'lesson': lesson,
        'sub_lessons_data': sub_lessons_data,
    })


@teacher_required
def teacher_news(request):
    """Новости для учителя и ментора (тот же список, что и у студентов)."""
    news_list = News.objects.filter(is_published=True).order_by('-created_at')[:50]
    return render(request, 'teacher/news.html', {'news_list': news_list})


@teacher_required
def teacher_news_detail(request, pk):
    """Просмотр одной новости."""
    news_item = get_object_or_404(News.objects.filter(is_published=True), pk=pk)
    return render(request, 'teacher/news_detail.html', {'news_item': news_item})


@teacher_required
def teacher_profile(request):
    """Профиль преподавателя/ментора (роль, личные данные, смена пароля). Оба видят свои данные."""
    user = request.user
    teacher_profile_obj = getattr(user, 'teachers', None)
    is_mentor = teacher_profile_obj and getattr(teacher_profile_obj, 'choices', None) == 'mentor'
    role_display = 'Ментор' if is_mentor else 'Учитель'
    profile_data = {
        'first_name': getattr(user, 'first_name', '') or '',
        'surname': getattr(user, 'surname', '') or '',
        'email': getattr(user, 'email', '') or '',
        'phone_number': getattr(user, 'phone_number', '') or '',
        'telegram_username': (getattr(user, 'telegram_username', '') or '').strip().lstrip('@'),
        'role_display': role_display,
    }
    return render(request, 'teacher/profile.html', {
        'is_mentor': is_mentor,
        'role_display': role_display,
        'profile_data': profile_data,
    })


# --- ACTIONS (POST ONLY) ---

@student_required
def upload_receipt_view(request, payment_id):
    """Загрузка чека об оплате."""
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
    """Приём сдачи задания."""
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
    text = sanitize_text_field(request.POST.get('text'))
    file_obj = request.FILES.get('file')
    if not text and not file_obj:
        return JsonResponse({'error': 'Добавьте текст или файл'}, status=400)
    TaskSubmission.objects.create(student=student, task=task, text=text or '', file=file_obj or None)
    # Отметить урок как посещённый (для тарифа «активное обучение» — следующий откроется после сдачи)
    lesson = task.sub_lesson.lesson
    Attendance.objects.get_or_create(student=student, lesson=lesson, defaults={'is_present': True})
    return JsonResponse({'ok': True, 'message': 'Ответ отправлен!', 'attempts_left': 2 - submission_count})


@require_POST
def submit_lesson_comment_view(request, lesson_id):
    """Добавить комментарий к уроку."""
    if not request.user.is_authenticated or not hasattr(request.user, 'student'):
        return JsonResponse({'error': 'Войдите в аккаунт'}, status=401)
    lesson = get_object_or_404(Lesson.objects.select_related('course'), pk=lesson_id)
    student = request.user.student
    has_access = StudentSubscription.objects.filter(
        student=student, tariff__course=lesson.course
    ).exists()
    if not has_access:
        return JsonResponse({'error': 'Нет доступа к курсу'}, status=403)
    text = sanitize_text_field(request.POST.get('text'))
    file_obj = request.FILES.get('file')
    if not text and not file_obj:
        return JsonResponse({'error': 'Напишите комментарий или прикрепите файл'}, status=400)
    LessonComment.objects.create(lesson=lesson, student=student, text=text or '', file=file_obj or None)
    return JsonResponse({'ok': True, 'message': 'Комментарий добавлен!'})


# --- API VIEWS ---

def notifications_list_api(request):
    """Список уведомлений студента (JSON)."""
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
    """Отметить уведомление прочитанным."""
    student = _get_student_from_request(request)
    if not student:
        return JsonResponse({'error': 'Войдите в аккаунт'}, status=401)
    import json
    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        body = {}
    nid = validate_int_id(body.get('notification_id'))
    if nid is not None:
        Notification.objects.filter(student=student, pk=nid).update(is_read=True)
    else:
        Notification.objects.filter(student=student).update(is_read=True)
    return JsonResponse({'ok': True})
