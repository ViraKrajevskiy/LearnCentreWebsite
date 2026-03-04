from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from WebSite.view_sets.otp_register_views.register_verify import (
    RegisterView, VerifyOTPView, LoginView, ProfileView, ChangePasswordView
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/auth/register/', RegisterView.as_view(), name='api_register'),
    path('api/v1/auth/verify-otp/', VerifyOTPView.as_view(), name='api_verify_otp'),
    path('api/v1/auth/login/', LoginView.as_view(), name='api_login'),
    path('api/v1/auth/me/', ProfileView.as_view(), name='api_profile'),
    path('api/v1/auth/change-password/', ChangePasswordView.as_view(), name='api_change_password'),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('', include('WebSiteFront.urls')),
    path('', include('WebSite.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)