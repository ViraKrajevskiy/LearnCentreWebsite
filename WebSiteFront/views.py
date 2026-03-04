from django.shortcuts import render


def front_home(request):
    return render(request, 'Main_page/lastFigma versuin.html')


def front_register(request):
    return render(request, 'login_registration/register.html')


def front_login(request):
    return render(request, 'login_registration/login.html')
