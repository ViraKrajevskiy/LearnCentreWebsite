from django.shortcuts import render
from django.conf import settings


def front_home(request):
    return render(request, 'main_pages/home.html')


def front_register(request):
    return render(request, 'login_registration/register.html')


def front_login(request):
    return render(request, 'login_registration/login.html')


def front_courses(request):
    video_id = getattr(settings, 'GOOGLE_DRIVE_COURSES_VIDEO_ID', None)
    return render(request, 'main_pages/courses.html', {'google_drive_video_id': video_id})


def front_about(request):
    return render(request, 'main_pages/about.html')


def front_contact(request):
    return render(request, 'main_pages/contact.html')


def front_faq(request):
    return render(request, 'main_pages/faq.html')


def front_invite(request):
    return render(request, 'main_pages/invite.html')


def front_proftest(request):
    return render(request, 'main_pages/proftest.html')
