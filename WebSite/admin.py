from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

from WebSite.models.opt_model import UserOTP

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'surname', 'phone_number', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'surname', 'phone_number', 'telegram_username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'surname', 'last_name', 'phone_number', 'telegram_username', 'birth_date')}),
        ('Роль', {'fields': ('role',)}),
        ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'surname', 'phone_number', 'password1', 'password2'),
        }),
    )


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display = ['identifier', 'code', 'session_id', 'is_used', 'attempts', 'created_at', 'expires_at']
    list_filter = ['is_used']
    search_fields = ['identifier', 'session_id']
    readonly_fields = ['session_id', 'created_at', 'expires_at']