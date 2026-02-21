from django.urls import path
from WebSite.view_sets.otp_register_views.register_verify import RegistrationView, VerifyOTPView
from WebSite.views.views import (
    student_ai_chat, student_assignments, student_courses, student_home,
    student_messages, student_my_courses, student_news, student_profile,
    main_home, main_courses, main_about, main_contact, main_faq, main_invite, main_login, main_register
)

urlpatterns = [
    # Главные страницы (Main)
    path('', main_home, name='home'),
    path('courses/', main_courses, name='courses'),
    path('about/', main_about, name='about'),
    path('contact/', main_contact, name='contact'),
    path('faq/', main_faq, name='faq'),
    path('invite/', main_invite, name='invite'),
    path('login/', main_login, name='login'),
    path('register/', main_register, name='register'),

    # Личный кабинет студента (префикс student/ чтобы не было конфликтов)
    path('student/', student_home, name='student_home'),
    path('student/courses/', student_courses, name='student_courses'),
    path('student/my-courses/', student_my_courses, name='my-courses'),
    path('student/assignments/', student_assignments, name='assignments'),
    path('student/profile/', student_profile, name='profile'),
    path('student/ai-chat/', student_ai_chat, name='ai-chat'),
    path('student/messages/', student_messages, name='messages'),
    path('student/news/', student_news, name='news'),

    # API для мобилки или фронтенда (JWT + OTP)
    path('api/v1/auth/registration/', RegistrationView.as_view(), name='api_register'),
    path('api/v1/auth/verify-otp/', VerifyOTPView.as_view(), name='api_verify_otp'),
]