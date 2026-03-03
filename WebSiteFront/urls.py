from django.urls import path
from WebSiteFront.views import front_home, front_register, front_login

urlpatterns = [
    path('', front_home, name='home'),
    path('register/', front_register, name='register'),
    path('login/', front_login, name='login'),
]
