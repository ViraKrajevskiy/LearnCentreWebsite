from django.urls import path

from WebSite.views.views import (
    student_ai_chat, student_assignments, student_courses, student_home,
    student_messages, student_my_courses, student_news, student_profile,
    main_home, main_courses, main_about, main_contact, main_faq, main_invite,
    main_login, main_staff_login, main_register
)

urlpatterns = [
    # --- Главные страницы (Отображение HTML-шаблонов) ---
    path('', main_home, name='home'),
    path('courses/', main_courses, name='courses'),
    path('about/', main_about, name='about'),
    path('contact/', main_contact, name='contact'),
    path('faq/', main_faq, name='faq'),
    path('invite/', main_invite, name='invite'),
    path('login/', main_login, name='login'),
    path('staff/login/', main_staff_login, name='staff_login'),

    # Это страница, где юзер видит саму форму регистрации (HTML)
    path('register/', main_register, name='register'),

    # --- Страницы личного кабинета студента ---
    path('student/', student_home, name='student_home'),
    path('student/courses/', student_courses, name='student_courses'),
    path('student/my-courses/', student_my_courses, name='my-courses'),
    path('student/assignments/', student_assignments, name='assignments'),
    path('student/profile/', student_profile, name='profile'),
    path('student/ai-chat/', student_ai_chat, name='ai-chat'),
    path('student/messages/', student_messages, name='messages'),
    path('student/news/', student_news, name='news'),
]