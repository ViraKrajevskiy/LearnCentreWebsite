"""Контекст-процессоры для шаблонов."""


def teacher_dashboard(request):
    """Добавляет is_teacher: True только для пользователей с ролью учителя (не ментор)."""
    is_teacher = False
    if request.user.is_authenticated:
        try:
            profile = getattr(request.user, 'teachers', None)
            is_teacher = profile is not None and getattr(profile, 'choices', None) == 'teacher'
        except Exception:
            pass
    return {'is_teacher': is_teacher}
