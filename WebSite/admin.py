from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html, mark_safe
from django.utils import timezone

from WebSite.models.opt_model import UserOTP
from WebSite.models.worker_model.workers import Teacher
from WebSite.models.student_model.student import Student
from WebSite.models.student_model.attandance import Attendance, StudentProgress
from WebSite.models.study.lesson import Course, Lesson, SubLesson, Task
from WebSite.models.study.lesson_comment import LessonComment
from WebSite.models.study.submission import TaskSubmission
from WebSite.models.study.grade_model import Grade
from WebSite.models.study.tarif_system import Tariff
from WebSite.models.group.groups import Group
from WebSite.models.pay_system.payment import Payment, StudentSubscription
from WebSite.models.notifications import Notification
from WebSite.models.news_model import News

User = get_user_model()

# ─────────────────────────────────────────
# USER
# ─────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['email', 'full_name', 'phone_number', 'role_badge', 'is_active', 'created_at']
    list_filter   = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'surname', 'phone_number', 'telegram_username']
    ordering      = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ('groups', 'user_permissions')
    list_per_page = 30

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личные данные', {'fields': ('first_name', 'surname', 'last_name', 'phone_number', 'birth_date')}),
        ('Telegram', {'fields': ('telegram_username', 'telegram_chat_id')}),
        ('Роль', {'fields': ('role',)}),
        ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'surname', 'phone_number', 'role', 'password1', 'password2'),
        }),
    )

    @admin.display(description='ФИО')
    def full_name(self, obj):
        return f"{obj.surname} {obj.first_name} {obj.last_name or ''}".strip()

    @admin.display(description='Роль')
    def role_badge(self, obj):
        colors = {
            'student': '#6366f1', 'teacher': '#10b981',
            'mentor': '#f59e0b', 'staff': '#06b6d4', 'guest': '#94a3b8',
        }
        c = colors.get(obj.role, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:50px;font-size:.75rem;font-weight:700">{}</span>',
            c, obj.get_role_display()
        )


# ─────────────────────────────────────────
# OTP
# ─────────────────────────────────────────

@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display  = ['identifier', 'code', 'session_id', 'valid_badge', 'is_used', 'attempts', 'created_at', 'expires_at']
    list_filter   = ['is_used']
    search_fields = ['identifier', 'session_id']
    readonly_fields = ['session_id', 'created_at', 'expires_at']
    ordering      = ['-created_at']
    list_per_page = 30

    @admin.display(description='Действующий?', boolean=True)
    def valid_badge(self, obj):
        return obj.is_valid


# ─────────────────────────────────────────
# WORKERS
# ─────────────────────────────────────────

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display  = ['id', 'choices', 'short_bio', 'experience_years', 'created_at']
    list_filter   = ['choices']
    search_fields = ['bio', 'working_companies']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['-created_at']

    @admin.display(description='Биография')
    def short_bio(self, obj):
        return (obj.bio or '')[:60] + ('…' if obj.bio and len(obj.bio) > 60 else '')


# ─────────────────────────────────────────
# STUDENTS
# ─────────────────────────────────────────

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ['id', 'user_email', 'user_full_name', 'course', 'created_at']
    list_filter   = ['course']
    search_fields = ['user__email', 'user__first_name', 'user__surname', 'user__phone_number']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['user', 'course']
    ordering      = ['-created_at']
    list_per_page = 30

    @admin.display(description='Email', ordering='user__email')
    def user_email(self, obj):
        return obj.user.email if obj.user else '—'

    @admin.display(description='ФИО', ordering='user__surname')
    def user_full_name(self, obj):
        if obj.user:
            return f"{obj.user.surname} {obj.user.first_name}".strip()
        return '—'


# ─────────────────────────────────────────
# ATTENDANCE & PROGRESS
# ─────────────────────────────────────────

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display  = ['student', 'lesson', 'date', 'present_badge', 'reason_short']
    list_filter   = ['is_present', 'date']
    search_fields = ['student__user__email', 'student__user__surname', 'lesson__title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    ordering      = ['-date']
    list_per_page = 40

    @admin.display(description='Присутствие', boolean=True)
    def present_badge(self, obj):
        return obj.is_present

    @admin.display(description='Причина отсутствия')
    def reason_short(self, obj):
        r = obj.reason_of_absence or ''
        return r[:50] + ('…' if len(r) > 50 else '') if r else '—'


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display  = ['student', 'course', 'completed_lessons_count', 'average_grade_fmt', 'finished_badge', 'created_at']
    list_filter   = ['finished_course', 'course']
    search_fields = ['student__user__email', 'student__user__surname', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['-created_at']

    @admin.display(description='Ср. балл')
    def average_grade_fmt(self, obj):
        return f"{obj.average_grade:.1f}"

    @admin.display(description='Завершён', boolean=True)
    def finished_badge(self, obj):
        return obj.finished_course


# ─────────────────────────────────────────
# STUDY — COURSE / LESSON / SUBLESSON / TASK
# ─────────────────────────────────────────

class SubLessonInline(admin.TabularInline):
    model   = SubLesson
    extra   = 1
    fields  = ['order', 'title', 'content_link']
    ordering = ['order']


class TaskInline(admin.TabularInline):
    model   = Task
    extra   = 1
    fields  = ['description', 'max_score']


class LessonInline(admin.TabularInline):
    model   = Lesson
    extra   = 0
    fields  = ['title', 'scheduled_at', 'group']
    readonly_fields = ['scheduled_at']
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display  = ['title', 'creator', 'price', 'lesson_count', 'created_at']
    list_filter   = ['creator']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['-created_at']
    inlines       = [LessonInline]

    @admin.display(description='Уроков')
    def lesson_count(self, obj):
        return obj.lessons.count()


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display  = ['title', 'course', 'group', 'scheduled_at', 'sub_count']
    list_filter   = ['course', 'group']
    search_fields = ['title', 'course__title', 'group__name']
    readonly_fields = []
    date_hierarchy = 'scheduled_at'
    ordering      = ['scheduled_at']
    inlines       = [SubLessonInline]
    autocomplete_fields = ['course', 'group']
    list_per_page = 30

    @admin.display(description='Подуроков')
    def sub_count(self, obj):
        return obj.sub_lessons.count()


@admin.register(SubLesson)
class SubLessonAdmin(admin.ModelAdmin):
    list_display  = ['title', 'lesson', 'order', 'task_count', 'link_preview']
    list_filter   = ['lesson__course']
    search_fields = ['title', 'lesson__title']
    ordering      = ['lesson', 'order']
    inlines       = [TaskInline]

    @admin.display(description='Заданий')
    def task_count(self, obj):
        return obj.tasks.count()

    @admin.display(description='Ссылка')
    def link_preview(self, obj):
        if obj.content_link:
            return format_html('<a href="{}" target="_blank">Открыть ↗</a>', obj.content_link)
        return '—'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display  = ['short_desc', 'sub_lesson', 'max_score']
    list_filter   = ['sub_lesson__lesson__course']
    search_fields = ['description', 'sub_lesson__title', 'sub_lesson__lesson__title']

    @admin.display(description='Задание')
    def short_desc(self, obj):
        return obj.description[:70] + ('…' if len(obj.description) > 70 else '')


@admin.register(LessonComment)
class LessonCommentAdmin(admin.ModelAdmin):
    list_display  = ['lesson', 'student', 'short_text', 'file_link', 'created_at']
    list_filter   = ['lesson__course']
    search_fields = ['text', 'lesson__title']
    readonly_fields = ['created_at']
    ordering      = ['-created_at']
    list_per_page = 30

    @admin.display(description='Комментарий')
    def short_text(self, obj):
        if not obj.text:
            return '—'
        return obj.text[:60] + ('…' if len(obj.text) > 60 else '')

    @admin.display(description='Файл')
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Скачать</a>', obj.file.url)
        return '—'


@admin.register(TaskSubmission)
class TaskSubmissionAdmin(admin.ModelAdmin):
    list_display  = ['student', 'task', 'short_text', 'file_link', 'created_at']
    list_filter   = ['task__sub_lesson__lesson__course']
    search_fields = ['text', 'student__user__email']
    readonly_fields = ['created_at']
    ordering      = ['-created_at']
    list_per_page = 30

    @admin.display(description='Ответ')
    def short_text(self, obj):
        if not obj.text:
            return '—'
        return obj.text[:50] + ('…' if len(obj.text) > 50 else '')

    @admin.display(description='Файл')
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Скачать</a>', obj.file.url)
        return '—'


# ─────────────────────────────────────────
# GRADE
# ─────────────────────────────────────────

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display  = ['get_grade_display_fmt', 'grade_value', 'value_badge', 'created_at']
    list_filter   = ['grade']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['-created_at']
    list_per_page = 40

    @admin.display(description='Тип оценки')
    def get_grade_display_fmt(self, obj):
        return obj.get_grade_display()

    @admin.display(description='Балл')
    def value_badge(self, obj):
        v = obj.grade_value
        if v is None:
            return '—'
        if v >= 80:
            color, bg = '#10b981', 'rgba(16,185,129,.15)'
        elif v >= 60:
            color, bg = '#f59e0b', 'rgba(245,158,11,.15)'
        else:
            color, bg = '#ef4444', 'rgba(239,68,68,.15)'
        return format_html(
            '<span style="background:{};color:{};padding:3px 12px;border-radius:50px;font-weight:700">{}</span>',
            bg, color, v
        )


# ─────────────────────────────────────────
# GROUPS
# ─────────────────────────────────────────

class LessonGroupInline(admin.TabularInline):
    model   = Lesson
    extra   = 0
    fields  = ['title', 'scheduled_at']
    readonly_fields = ['title', 'scheduled_at']
    show_change_link = True
    verbose_name = 'Урок'
    verbose_name_plural = 'Уроки группы'


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display  = ['name', 'course', 'student_count', 'lesson_count', 'start_date', 'created_at']
    list_filter   = ['course', 'start_date']
    search_fields = ['name', 'course__title']
    filter_horizontal = ['students']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['-start_date']
    inlines       = [LessonGroupInline]

    @admin.display(description='Студентов')
    def student_count(self, obj):
        return obj.students.count()

    @admin.display(description='Уроков')
    def lesson_count(self, obj):
        return obj.lessons.count()


# ─────────────────────────────────────────
# TARIFF
# ─────────────────────────────────────────

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display  = ['title', 'course', 'price', 'duration_days', 'created_at']
    list_filter   = ['course']
    search_fields = ['title', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['course', 'price']


# ─────────────────────────────────────────
# PAYMENT & SUBSCRIPTION
# ─────────────────────────────────────────

@admin.register(StudentSubscription)
class StudentSubscriptionAdmin(admin.ModelAdmin):
    list_display  = ['student', 'tariff', 'start_date', 'end_date', 'active_badge', 'days_left']
    list_filter   = ['is_active', 'tariff__course']
    search_fields = ['student__user__email', 'student__user__surname', 'tariff__title']
    readonly_fields = ['created_at', 'updated_at', 'start_date']
    ordering      = ['-start_date']
    list_per_page = 30

    @admin.display(description='Активна', boolean=True)
    def active_badge(self, obj):
        return obj.is_active

    @admin.display(description='Осталось дней')
    def days_left(self, obj):
        if obj.end_date:
            delta = (obj.end_date - timezone.now()).days
            if delta > 0:
                return format_html('<span style="color:#10b981;font-weight:700">{}д</span>', delta)
            return mark_safe('<span style="color:#ef4444;font-weight:700">Истекла</span>')
        return '—'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ['student', 'amount', 'method_badge', 'confirmed_badge', 'confirmed_by_name', 'created_at']
    list_filter   = ['is_confirmed', 'method']
    search_fields = ['student__user__email', 'student__user__surname', 'confirmed_by_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['-created_at']
    list_per_page = 40

    actions = ['confirm_payments']

    @admin.display(description='Метод')
    def method_badge(self, obj):
        colors = {'card': '#6366f1', 'cash': '#10b981', 'transfer': '#f59e0b'}
        c = colors.get(obj.method, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:50px;font-size:.75rem;font-weight:700">{}</span>',
            c, obj.get_method_display()
        )

    @admin.display(description='Подтверждён', boolean=True)
    def confirmed_badge(self, obj):
        return obj.is_confirmed

    @admin.action(description='✅ Подтвердить выбранные платежи')
    def confirm_payments(self, request, queryset):
        updated = queryset.filter(is_confirmed=False).update(is_confirmed=True)
        self.message_user(request, f'Подтверждено платежей: {updated}')


# ─────────────────────────────────────────
# NOTIFICATIONS & NEWS
# ─────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['id', 'student', 'kind_badge', 'title_short', 'is_read', 'created_at']
    list_filter   = ['kind', 'is_read']
    search_fields = ['title', 'message', 'student__user__email']
    readonly_fields = ['created_at', 'updated_at']
    ordering      = ['-created_at']
    list_per_page = 40

    @admin.display(description='Тип')
    def kind_badge(self, obj):
        return obj.get_kind_display()

    @admin.display(description='Заголовок')
    def title_short(self, obj):
        return (obj.title or '')[:50] + ('…' if len(obj.title or '') > 50 else '')


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display  = ['title', 'is_published', 'created_at']
    list_filter   = ['is_published']
    search_fields = ['title', 'content']
    ordering      = ['-created_at']


# ─────────────────────────────────────────
# ADMIN SITE CUSTOMIZATION
# ─────────────────────────────────────────

admin.site.site_header  = '⚡ Swift Intell — Панель управления'
admin.site.site_title   = 'Swift Intell Admin'
admin.site.index_title  = 'Добро пожаловать в панель управления'
