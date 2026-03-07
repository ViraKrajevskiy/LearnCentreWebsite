from django.urls import path

from WebSite.views.views import (
    # Guest / Main Pages
    main_home, main_courses, main_about, main_contact, main_faq, main_invite,
    main_login, main_staff_login, main_register,

    # Student Pages
    student_home, student_courses, student_course_detail, student_my_courses,
    student_lesson_redirect, student_lesson_detail, student_group_chat, clear_my_group_chat, student_assignments,
    student_performance, student_profile, student_payments, student_attendance,
    student_ai_chat, student_messages, student_news, student_news_detail,

    # Teacher / Mentor Pages
    teacher_home, teacher_my_groups, teacher_messages, teacher_homework, teacher_submission_detail,
    teacher_lessons_panel, teacher_lesson_create, teacher_lesson_edit, teacher_profile,

    # Actions / API
    upload_receipt_view, submit_task_view, submit_lesson_comment_view,
    notifications_list_api, notification_mark_read_api,
)

urlpatterns = [
    # Main / Guest
    path('', main_home, name='home'),
    path('courses/', main_courses, name='courses'),
    path('about/', main_about, name='about'),
    path('contact/', main_contact, name='contact'),
    path('faq/', main_faq, name='faq'),
    path('invite/', main_invite, name='invite'),
    path('login/', main_login, name='login'),
    path('register/', main_register, name='register'),
    path('staff/login/', main_staff_login, name='staff_login'),

    # Student Platform
    path('student/', student_home, name='student_home'),
    path('student/courses/', student_courses, name='student_courses'),
    path('student/courses/<int:course_id>/', student_course_detail, name='student_course_detail'),
    path('student/my-courses/', student_my_courses, name='my-courses'),
    path('student/lesson/<int:lesson_id>/', student_lesson_redirect, name='lesson'),
    path('student/lesson/<int:lesson_id>/detail/', student_lesson_detail, name='lesson_detail'),
    path('student/group/<int:group_id>/chat/', student_group_chat, name='group_chat'),
    path('student/group/<int:group_id>/chat/clear/', clear_my_group_chat, name='group_chat_clear'),
    path('student/assignments/', student_assignments, name='assignments'),
    path('student/performance/', student_performance, name='performance'),
    path('student/attendance/', student_attendance, name='attendance'),
    path('student/profile/', student_profile, name='profile'),
    path('student/payments/', student_payments, name='payments'),
    path('student/ai-chat/', student_ai_chat, name='ai-chat'),
    path('student/messages/', student_messages, name='messages'),
    path('student/news/', student_news, name='news'),
    path('student/news/<int:pk>/', student_news_detail, name='news_detail'),

    # Teacher / Mentor Platform
    path('teacher/', teacher_home, name='teacher_home'),
    path('teacher/my-groups/', teacher_my_groups, name='teacher_my_groups'),
    path('teacher/messages/', teacher_messages, name='teacher_messages'),
    path('teacher/homework/', teacher_homework, name='teacher_homework'),
    path('teacher/homework/submission/<int:submission_id>/', teacher_submission_detail, name='teacher_submission_detail'),
    path('teacher/lessons/', teacher_lessons_panel, name='teacher_lessons_panel'),
    path('teacher/lesson/create/', teacher_lesson_create, name='teacher_lesson_create'),
    path('teacher/lesson/<int:lesson_id>/edit/', teacher_lesson_edit, name='teacher_lesson_edit'),
    path('teacher/profile/', teacher_profile, name='teacher_profile'),

    # Actions / API
    path('student/payment/<int:payment_id>/receipt/', upload_receipt_view, name='upload_receipt'),
    path('student/task/<int:task_id>/submit/', submit_task_view, name='submit_task'),
    path('student/lesson/<int:lesson_id>/comment/', submit_lesson_comment_view, name='submit_lesson_comment'),
    path('student/notifications/api/', notifications_list_api, name='notifications_api'),
    path('student/notifications/read/', notification_mark_read_api, name='notification_mark_read'),
]