from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.filters.command import CommandObject
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from asgiref.sync import sync_to_async
from django.conf import settings

from WebSite.models.opt_model import UserOTP
from django.contrib.auth import get_user_model

User = get_user_model()

_token = (settings.TELEGRAM_BOT_TOKEN or '').strip()
if _token:
    bot = Bot(token=_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
else:
    bot = None
dp = Dispatcher(storage=MemoryStorage())


class ChangePasswordStates(StatesGroup):
    waiting_old = State()
    waiting_new = State()


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
    try:
        user = User.objects.get(telegram_chat_id=chat_id)
        return user
    except User.DoesNotExist:
        pass
    if username:
        clean = str(username).lstrip('@').lower()
        try:
            user = User.objects.get(telegram_username__iexact=clean)
            user.telegram_chat_id = chat_id
            user.save(update_fields=['telegram_chat_id'])
            return user
        except User.DoesNotExist:
            pass
    return None


@sync_to_async
def change_password(user, old_password: str, new_password: str) -> tuple[bool, str]:
    if not user.check_password(old_password):
        return False, "Неверный текущий пароль."
    if len(new_password) < 8:
        return False, "Новый пароль должен быть не менее 8 символов."
    user.set_password(new_password)
    user.save()
    return True, "Пароль успешно изменён."


@dp.message(CommandStart(deep_link=True))
async def command_start_with_link(message: types.Message, command: CommandObject):
    session_id = command.args
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


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    username = message.from_user.username if message.from_user else None
    user = await get_user_by_telegram(message.chat.id, username)
    if not user:
        await message.answer(
            " Аккаунт не найден.\n\n"
            "Привяжите Telegram: укажите ваш @username при регистрации на сайте и получите код через этого бота."
        )
        return
    role_display = user.get_role_display() if hasattr(user, 'get_role_display') else user.role
    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"Имя: {user.first_name} {user.surname}\n"
        f"Телефон: {user.phone_number}\n"
        f"Telegram: @{user.telegram_username or '—'}\n"
        f"Роль: {role_display}\n"
        f"Email: {user.email}"
    )
    await message.answer(text)


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


async def _send_welcome(message: types.Message):
    await message.answer(
        " Привет! Я бот учебного центра LearnCentre.\n\n"
        " <b>Как получить код подтверждения:</b>\n"
        "1. Зарегистрируйся на нашем сайте\n"
        "2. После регистрации тебе придёт ссылка на этот бот\n"
        "3. Нажми на ссылку — я сразу пришлю тебе 6-значный код\n"
        "4. Введи код на сайте для завершения регистрации\n\n"
        " <b>Команды:</b>\n"
        "/profile — просмотр профиля\n"
        "/changepassword — смена пароля\n\n"
        "⚡ Код приходит только по ссылке с сайта."
    )
