from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from WebSite.models.student_model.attandance import Attendance
from WebSite.models.study.lesson import Course, Lesson

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
    return render(request, 'student/home.html')

def student_courses(request):
    return render(request, 'student/courses.html')

def student_lesson_redirect(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    if request.user.is_authenticated and hasattr(request.user, 'student'):
        student = request.user.student
        if student.study_groups.filter(pk=lesson.group_id).exists():
            return redirect(lesson.content_link)
        if student.course_id and lesson.group.course_id == student.course_id:
            return redirect(lesson.content_link)
    return redirect('my-courses')


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