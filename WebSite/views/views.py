from django.shortcuts import render

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

def student_my_courses(request):
    return render(request, 'student/my_courses.html')

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