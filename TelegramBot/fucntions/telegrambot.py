from aiogram import Router, types
from aiogram.filters import CommandStart, CommandObject
from asgiref.sync import sync_to_async

from WebSite.models.opt_model import UserOTP

router = Router()

@sync_to_async
def get_otp_by_session(session_id: str):
    try:
        # Ищем валидный код по session_id
        otp = UserOTP.objects.get(session_id=session_id)
        if otp.is_valid:
            return otp.code
    except (UserOTP.DoesNotExist, ValueError):
        return None
    return None


@router.message(CommandStart(deep_link=True))
async def command_start_with_link(message: types.Message, command: CommandObject):
    # commands.args содержит то, что идет после ?start= (наш session_id)
    session_id = command.args

    if session_id:
        # Ищем код в базе
        code = await get_otp_by_session(session_id)

        if code:
            await message.answer(
                f"Здравствуйте, {message.from_user.first_name}! 👋\n\n"
                f"Ваш код для подтверждения регистрации на сайте:\n"
                f"<b>{code}</b>\n\n"
                f"Вернитесь на сайт и введите этот код.",
                parse_mode="HTML"
            )
        else:
            await message.answer("Ошибка: Сессия истекла, недействительна или уже использована.")
    else:
        # Если юзер просто нажал /start без ссылки
        await message.answer("Добро пожаловать в бота нашего учебного центра!")