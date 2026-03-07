from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.filters.command import CommandObject
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from asgiref.sync import sync_to_async
from django.conf import settings

from WebSite.models.opt_model import UserOTP
from WebSite.models.telegram_link import TelegramLinkToken
from WebSite.models.pay_system.payment import Payment
from django.contrib.auth import get_user_model

User = get_user_model()

_token = (settings.TELEGRAM_BOT_TOKEN or '').strip()
if _token:
    _proxy = getattr(settings, 'TELEGRAM_BOT_PROXY', None)
    _session = AiohttpSession(
        timeout=90.0,
        proxy=_proxy if _proxy else None,
    )
    bot = Bot(token=_token, session=_session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
else:
    bot = None
dp = Dispatcher(storage=MemoryStorage())


class ChangePasswordStates(StatesGroup):
    waiting_old = State()
    waiting_new = State()


class ResetPasswordStates(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_new_password = State()


class LoginStates(StatesGroup):
    waiting_phone = State()
    waiting_password = State()


@sync_to_async
def get_otp_by_session(session_id: str):
    try:
        otp = UserOTP.objects.get(session_id=session_id)
        if otp.is_valid:
            return otp
    except (UserOTP.DoesNotExist, ValueError):
        return None
    return None


@sync_to_async
def save_otp_chat_id(session_id: str, chat_id: int):
    try:
        otp = UserOTP.objects.get(session_id=session_id)
        otp.telegram_chat_id = chat_id
        otp.save(update_fields=['telegram_chat_id'])
    except (UserOTP.DoesNotExist, ValueError):
        pass


@sync_to_async
def get_user_by_telegram(chat_id: int, username: str = None):
    # Может быть несколько записей с одним chat_id (дубликаты) — берём первую
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if user:
        return user
    if username:
        clean = str(username).lstrip('@').lower()
        user = User.objects.filter(telegram_username__iexact=clean).first()
        if user:
            user.telegram_chat_id = chat_id
            user.save(update_fields=['telegram_chat_id'])
            return user
    return None


@sync_to_async
def consume_link_token(token: str, chat_id: int):
    """Привязка аккаунта по одноразовому токену (после входа на сайте). Возвращает (user или None, сообщение)."""
    try:
        record = TelegramLinkToken.objects.get(token=token)
    except TelegramLinkToken.DoesNotExist:
        return None, "Ссылка недействительна или уже использована. Получите новую в личном кабинете на сайте."
    if record.is_expired:
        record.delete()
        return None, "Время действия ссылки истекло. Получите новую ссылку после входа на сайте."
    user = record.user
    record.delete()
    user.telegram_chat_id = chat_id
    user.save(update_fields=['telegram_chat_id'])
    return user, None


@sync_to_async
def get_payment_count_for_user(user):
    """Количество оплат студента (только после входа на сайте и привязки Telegram)."""
    if not hasattr(user, 'student'):
        return 0
    return Payment.objects.filter(student=user.student).count()


@sync_to_async
def login_by_phone_password(phone: str, password: str) -> "User|None":
    """Вход по номеру телефона и паролю. Возвращает User или None."""
    import re
    digits = re.sub(r"\D", "", (phone or "").strip())
    if not digits:
        return None
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10 and digits[0] in "79":
        digits = "7" + digits
    if len(digits) < 10:
        return None
    # Поиск по цифрам номера (в БД хранится в нормализованном виде, например +79991234567)
    user = User.objects.filter(phone_number__icontains=digits).first()
    if not user or not user.check_password(password or ""):
        return None
    return user


@sync_to_async
def change_password(user, old_password: str, new_password: str) -> tuple[bool, str]:
    if not user.check_password(old_password):
        return False, "Неверный текущий пароль."
    if len(new_password) < 8:
        return False, "Новый пароль должен быть не менее 8 символов."
    user.set_password(new_password)
    user.save()
    return True, "Пароль успешно изменён."


def _normalize_phone(phone: str) -> str:
    import re
    digits = re.sub(r"\D", "", (phone or "").strip())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    elif len(digits) == 10 and digits[0] in "79":
        digits = "7" + digits
    return digits


@sync_to_async
def get_user_by_phone(phone: str):
    """Найти пользователя по номеру телефона (для сброса пароля)."""
    digits = _normalize_phone(phone)
    if len(digits) < 10:
        return None
    return User.objects.filter(phone_number__icontains=digits).first()


@sync_to_async
def create_reset_password_otp(user, chat_id: int):
    """Создать OTP для сброса пароля и отправить код в Telegram. Возвращает (session_id или None, сообщение об ошибке)."""
    import random
    from WebSite.utils.telegram import send_telegram_message
    code = str(random.randint(100000, 999999))
    identifier = f"pwchange:{user.pk}"
    otp_record = UserOTP.objects.create(identifier=identifier, code=code, telegram_chat_id=chat_id)
    ok = send_telegram_message(chat_id, f"Код для сброса пароля LearnCentre:\n<code>{code}</code>\n\nВведите его в боте. Код действителен 5 минут.")
    if not ok:
        return None, "Не удалось отправить сообщение. Попробуйте позже."
    return str(otp_record.session_id), None


@sync_to_async
def find_reset_otp_by_chat_and_code(chat_id: int, code: str):
    """Найти действующий OTP смены пароля по chat_id и коду."""
    otp = UserOTP.objects.filter(
        telegram_chat_id=chat_id,
        code=code.strip(),
        identifier__startswith="pwchange:"
    ).first()
    if otp and otp.is_valid:
        return otp
    return None


@sync_to_async
def set_password_by_otp_session(session_id: str, new_password: str) -> tuple[bool, str]:
    """Установить новый пароль по session_id OTP. Возвращает (успех, сообщение)."""
    if len(new_password) < 8:
        return False, "Пароль должен быть не менее 8 символов."
    try:
        otp = UserOTP.objects.get(session_id=session_id)
    except (UserOTP.DoesNotExist, ValueError):
        return False, "Сессия не найдена. Запросите код заново: /resetpassword"
    if not otp.is_valid:
        return False, "Код истёк или уже использован. Запросите новый: /resetpassword"
    if not (otp.identifier or "").startswith("pwchange:"):
        return False, "Неверная сессия."
    try:
        user_id = int(otp.identifier.split(":", 1)[1])
        user = User.objects.get(pk=user_id)
    except (ValueError, User.DoesNotExist):
        return False, "Пользователь не найден."
    otp.is_used = True
    otp.save()
    user.set_password(new_password)
    user.save()
    if not getattr(user, 'telegram_chat_id', None):
        user.telegram_chat_id = otp.telegram_chat_id
        user.save(update_fields=['telegram_chat_id'])
    return True, "Пароль успешно изменён. Можете войти на сайт или в боте: /login"


@dp.message(CommandStart(deep_link=True))
async def command_start_with_link(message: types.Message, command: CommandObject):
    args = (command.args or "").strip()
    # Привязка Telegram после входа на сайте: start=link_TOKEN
    if args.startswith("link_"):
        token = args[5:].strip()
        if token:
            user, err = await consume_link_token(token, message.chat.id)
            if err:
                await message.answer(f"❌ {err}")
            else:
                await message.answer(
                    "✅ <b>Аккаунт привязан!</b>\n\n"
                    "Теперь вы можете:\n"
                    "/profile — данные профиля\n"
                    "/payments — количество оплат\n"
                    "/changepassword — смена пароля\n"
                    "/resetpassword — сброс пароля по коду (если забыли пароль)"
                )
        else:
            await _send_welcome(message)
        return

    session_id = args
    if session_id:
        otp = await get_otp_by_session(session_id)
        if otp:
            await save_otp_chat_id(session_id, message.chat.id)
            await message.answer(
                f"Здравствуйте, <b>{message.from_user.first_name}</b>! 👋\n\n"
                f"Ваш код для подтверждения регистрации на сайте:\n"
                f"<code>{otp.code}</code>\n\n"
                f"Вернитесь на сайт и введите этот код."
            )
        else:
            await message.answer(
                "❌ Сессия истекла, недействительна или уже использована.\n"
                "Запросите новую регистрацию на сайте."
            )
    else:
        await _send_welcome(message)


@dp.message(CommandStart())
async def standard_start(message: types.Message):
    await _send_welcome(message)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await _send_welcome(message)


@dp.message(Command("payments"))
async def cmd_payments(message: types.Message):
    """Количество оплат — после входа по /login или привязки с сайта."""
    username = message.from_user.username if message.from_user else None
    user = await get_user_by_telegram(message.chat.id, username)
    if not user:
        await message.answer(
            "👤 Вы не вошли в аккаунт.\n\n"
            "Войдите по номеру телефона и паролю: /login"
        )
        return
    count = await get_payment_count_for_user(user)
    await message.answer(
        f"💳 <b>Оплаты</b>\n\n"
        f"Всего оплат по вашему аккаунту: <b>{count}</b>\n\n"
        f"Детали и чеки — в личном кабинете на сайте."
    )


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Просмотр данных профиля: имя, контакты, роль, дата регистрации."""
    username = message.from_user.username if message.from_user else None
    user = await get_user_by_telegram(message.chat.id, username)
    if not user:
        await message.answer(
            "👤 Вы не вошли в аккаунт.\n\n"
            "Войдите по номеру телефона и паролю: /login"
        )
        return
    text = _format_profile_text(user)
    await message.answer(text)


def _format_profile_text(user) -> str:
    """Форматирует текст блока «Данные профиля» для отправки в боте."""
    role_display = user.get_role_display() if hasattr(user, 'get_role_display') else user.role
    full_name = f"{user.surname or ''} {user.first_name or ''}".strip() or "—"
    if getattr(user, 'last_name', None):
        full_name += f" {user.last_name}"
    created = ""
    if getattr(user, 'created_at', None):
        created = user.created_at.strftime("%d.%m.%Y")
    return (
        f"👤 <b>Данные профиля</b>\n\n"
        f"ФИО: {full_name}\n"
        f"Email: {user.email}\n"
        f"Телефон: {user.phone_number}\n"
        f"Telegram: @{user.telegram_username or '—'}\n"
        f"Роль: {role_display}\n"
        f"Дата регистрации: {created or '—'}"
    )


@dp.message(Command("login"))
async def cmd_login(message: types.Message, state: FSMContext):
    """Начать вход по номеру телефона и паролю."""
    await state.set_state(LoginStates.waiting_phone)
    await message.answer(
        "🔐 <b>Вход по данным с сайта</b>\n\n"
        "Введите номер телефона (как в личном кабинете на сайте):"
    )


@dp.message(LoginStates.waiting_phone)
async def login_phone(message: types.Message, state: FSMContext):
    phone = (message.text or "").strip()
    if not phone:
        await message.answer("Введите номер телефона (например +7 999 123-45-67):")
        return
    await state.update_data(login_phone=phone)
    await state.set_state(LoginStates.waiting_password)
    await message.answer("Введите пароль от личного кабинета на сайте:")


@dp.message(LoginStates.waiting_password)
async def login_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("login_phone") or ""
    password = (message.text or "").strip()
    await state.clear()
    if not password:
        await message.answer("Пароль не введён. Повторите вход: /login")
        return
    user = await login_by_phone_password(phone, password)
    if not user:
        await message.answer(
            "❌ Неверный номер телефона или пароль.\n\n"
            "Проверьте данные и попробуйте снова: /login"
        )
        return
    # Привязываем этот чат к аккаунту, чтобы дальше /profile и /payments работали без повторного ввода
    await _save_telegram_chat_id(user, message.chat.id)
    await message.answer("✅ Вы вошли в аккаунт.\n\n" + _format_profile_text(user))
    await message.answer(
        "Теперь можно использовать:\n"
        "/profile — данные профиля\n"
        "/payments — количество оплат\n"
        "/changepassword — смена пароля"
    )


@sync_to_async
def _save_telegram_chat_id(user, chat_id: int):
    user.telegram_chat_id = chat_id
    user.save(update_fields=["telegram_chat_id"])


@dp.message(Command("changepassword"))
async def cmd_changepassword_start(message: types.Message, state: FSMContext):
    username = message.from_user.username if message.from_user else None
    user = await get_user_by_telegram(message.chat.id, username)
    if not user:
        await message.answer(" Аккаунт не найден. Зарегистрируйтесь на сайте и привяжите Telegram.")
        return
    await state.set_state(ChangePasswordStates.waiting_old)
    await state.update_data(user_id=user.pk)
    await message.answer("Введите текущий пароль:")


@dp.message(ChangePasswordStates.waiting_old)
async def changepassword_old(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('user_id')
    if not user_id:
        await state.clear()
        return
    try:
        user = await sync_to_async(User.objects.get)(pk=user_id)
    except User.DoesNotExist:
        await state.clear()
        await message.answer(" Ошибка. Начните заново: /changepassword")
        return
    old_password = message.text
    if not old_password:
        await message.answer("Введите текущий пароль (текстом):")
        return
    await state.update_data(old_password=old_password)
    await state.set_state(ChangePasswordStates.waiting_new)
    await message.answer("Введите новый пароль (не менее 8 символов):")


@dp.message(ChangePasswordStates.waiting_new)
async def changepassword_new(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('user_id')
    old_password = data.get('old_password')
    if not user_id or not old_password:
        await state.clear()
        await message.answer("❌ Сессия истекла. Начните заново: /changepassword")
        return
    new_password = message.text
    if not new_password:
        await message.answer("Введите новый пароль:")
        return
    try:
        user = await sync_to_async(User.objects.get)(pk=user_id)
    except User.DoesNotExist:
        await state.clear()
        await message.answer(" Ошибка.")
        return
    ok, msg = await change_password(user, old_password, new_password)
    await state.clear()
    if ok:
        await message.answer(f" {msg}")
    else:
        await message.answer(f" {msg}\n\nПопробуйте снова: /changepassword")


# --- Сброс пароля по коду из Telegram (для тех, кто забыл пароль) ---

@dp.message(Command("resetpassword"))
async def cmd_resetpassword(message: types.Message, state: FSMContext):
    """Сброс пароля без текущего пароля: телефон → код в Telegram → новый пароль. Для студентов и преподавателей."""
    await state.set_state(ResetPasswordStates.waiting_phone)
    await message.answer(
        "🔑 <b>Сброс пароля</b>\n\n"
        "Введите номер телефона (как при регистрации на сайте):"
    )


@dp.message(ResetPasswordStates.waiting_phone)
async def resetpassword_phone(message: types.Message, state: FSMContext):
    phone = (message.text or "").strip()
    if not phone:
        await message.answer("Введите номер телефона:")
        return
    user = await get_user_by_phone(phone)
    if not user:
        await state.clear()
        await message.answer("❌ Пользователь с таким номером не найден. Проверьте номер или зарегистрируйтесь на сайте.")
        return
    session_id, err = await create_reset_password_otp(user, message.chat.id)
    if err:
        await state.clear()
        await message.answer(f"❌ {err}")
        return
    await state.update_data(reset_session_id=session_id)
    await state.set_state(ResetPasswordStates.waiting_code)
    await message.answer("Код отправлен в этот чат. Введите код из сообщения:")


@dp.message(ResetPasswordStates.waiting_code)
async def resetpassword_code(message: types.Message, state: FSMContext):
    code = (message.text or "").strip()
    if not code:
        await message.answer("Введите 6-значный код:")
        return
    otp = await find_reset_otp_by_chat_and_code(message.chat.id, code)
    if not otp or not otp.is_valid:
        await message.answer("❌ Неверный или истёкший код. Запросите новый: /resetpassword")
        return
    await state.update_data(reset_session_id=str(otp.session_id))
    await state.set_state(ResetPasswordStates.waiting_new_password)
    await message.answer("Введите новый пароль (не менее 8 символов):")


@dp.message(ResetPasswordStates.waiting_new_password)
async def resetpassword_new(message: types.Message, state: FSMContext):
    new_password = (message.text or "").strip()
    data = await state.get_data()
    session_id = data.get("reset_session_id")
    await state.clear()
    if not session_id:
        await message.answer("❌ Сессия истекла. Начните заново: /resetpassword")
        return
    ok, msg = await set_password_by_otp_session(session_id, new_password)
    if ok:
        await message.answer(f"✅ {msg}")
    else:
        await message.answer(f"❌ {msg}")


async def _send_welcome(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот учебного центра LearnCentre.\n\n"
        "🔐 <b>Вход в аккаунт:</b>\n"
        "/login — войти по номеру телефона и паролю (как на сайте). После входа доступны /profile и /payments.\n\n"
        "🔑 <b>Пароль:</b>\n"
        "/changepassword — смена пароля (нужен текущий пароль)\n"
        "/resetpassword — сброс пароля по коду в Telegram (если забыли пароль)\n\n"
        "📋 <b>Команды:</b>\n"
        "/profile — данные профиля\n"
        "/payments — количество оплат\n\n"
        "⚡ Код подтверждения регистрации приходит по ссылке с сайта после регистрации."
    )
