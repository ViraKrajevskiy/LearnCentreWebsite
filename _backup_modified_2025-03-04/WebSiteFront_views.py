from django.shortcuts import render


def front_home(request):
    return render(request, 'Main_page/lastFigma versuin.html')


def front_register(request):
    return render(request, 'login_registration/register.html')


def front_login(request):
    return render(request, 'login_registration/login.html')


def front_courses(request):
    return render(request, 'main_pages/courses.html')


def front_about(request):
    return render(request, 'main_pages/about.html')


def front_contact(request):
    return render(request, 'main_pages/contact.html')


def front_faq(request):
    return render(request, 'main_pages/faq.html')


def front_invite(request):
    return render(request, 'main_pages/invite.html')
