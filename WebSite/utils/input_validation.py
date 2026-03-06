"""
Валидация и санитизация пользовательского ввода.
Защита от XSS, ограничение длины, допустимые символы.
Django ORM использует параметризованные запросы — SQL-инъекции исключены при использовании .filter(), .create() и т.д.
"""
import re
import json

# Лимиты длины (согласованы с моделями или разумные по умолчанию)
MAX_TEXT_FIELD = 10000   # текст задания, комментария
MAX_NAME = 255
MAX_NAME_SHORT = 50
MAX_EMAIL = 254
MAX_PHONE_STR = 20
MAX_TELEGRAM = 128
MAX_TAG = 128
MAX_TITLE = 255
MAX_LINK = 500
MAX_OTP_CODE = 6

# Допустимые символы: буквы (в т.ч. кириллица), цифры, пробелы, дефис, апостроф
SAFE_NAME_RE = re.compile(r'[^\w\s\-\u0400-\u04FF\']', re.UNICODE)
# Telegram: буквы, цифры, @, подчёркивание
SAFE_TELEGRAM_RE = re.compile(r'[^\w@]', re.UNICODE)
# Тег: буквы, цифры, подчёркивание, дефис
SAFE_TAG_RE = re.compile(r'[^\w\-]', re.UNICODE)
# Текст комментария/задания: убираем управляющие символы и нулевой байт
CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_name(value, max_len=None):
    """Имя: буквы, пробелы, дефис, апостроф."""
    if value is None:
        return ''
    s = str(value).strip()
    s = SAFE_NAME_RE.sub('', s)
    return s[: (max_len or MAX_NAME)]


def sanitize_email(value):
    """Email: trim, нижний регистр, лимит длины."""
    if value is None:
        return ''
    s = str(value).strip().lower()
    return s[:MAX_EMAIL]


def sanitize_phone_digits(value):
    """Телефон: только цифры и + - ( ) пробелы."""
    if value is None:
        return ''
    s = str(value).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    return re.sub(r'[^0-9+]', '', s)[:MAX_PHONE_STR]


def sanitize_telegram(value):
    """Telegram username: буквы, цифры, @."""
    if value is None:
        return ''
    s = str(value).strip().lstrip('@')
    s = SAFE_TELEGRAM_RE.sub('', s)
    return s[:MAX_TELEGRAM]


def sanitize_tag(value):
    """Тег: буквы, цифры, дефис, подчёркивание."""
    if value is None:
        return ''
    s = str(value).strip()
    s = SAFE_TAG_RE.sub('', s)
    return s[:MAX_TAG]


def sanitize_text_field(value, max_len=None):
    """Текст задания/комментария: убрать управляющие символы, лимит длины."""
    if value is None:
        return ''
    s = str(value).strip()
    s = CONTROL_CHARS_RE.sub('', s)
    return s[: (max_len or MAX_TEXT_FIELD)]


def sanitize_title(value, max_len=None):
    """Заголовок: как имя, но лимит 255."""
    return sanitize_name(value, max_len=(max_len or MAX_TITLE))


def sanitize_otp_code(value):
    """OTP: только цифры, 6 символов."""
    if value is None:
        return ''
    s = re.sub(r'[^0-9]', '', str(value))
    return s[:MAX_OTP_CODE]


def sanitize_profile_id(value, valid_ids):
    """profile_id должен быть из списка допустимых (защита от подмены)."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s in valid_ids else None


def validate_int_id(value, allow_none=False):
    """Безопасное целое для pk/notification_id (защита от SQL-инъекций и некорректных данных)."""
    if value is None:
        return None if allow_none else 0
    try:
        n = int(value)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None


def validate_json_scores(value, max_keys=10, max_value=100):
    """
    scores_json для профтеста: только объект с допустимыми ключами и числами.
    Защита от огромного payload и произвольных ключей.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        data = value
    elif isinstance(value, str):
        try:
            data = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
    else:
        return None
    valid_keys = {'ai_business', 'design_content', 'python_ml', 'analytics'}
    out = {}
    for k, v in list(data.items())[:max_keys]:
        if k not in valid_keys:
            continue
        try:
            num = int(v) if isinstance(v, (int, float)) else int(v)
            if 0 <= num <= max_value:
                out[k] = num
        except (TypeError, ValueError):
            continue
    return out if out else None
