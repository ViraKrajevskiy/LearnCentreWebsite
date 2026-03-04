from django.urls import path
from WebSiteFront.views import (
    front_home, front_register, front_login,
    front_courses, front_about, front_contact, front_faq, front_invite,
)

urlpatterns = [
    path('', front_home, name='home'),
    path('register/', front_register, name='register'),
    path('login/', front_login, name='login'),
    path('courses/', front_courses, name='courses'),
    path('about/', front_about, name='about'),
    path('contact/', front_contact, name='contact'),
    path('faq/', front_faq, name='faq'),
    path('invite/', front_invite, name='invite'),
]
