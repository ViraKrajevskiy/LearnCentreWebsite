
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from asgiref.sync import sync_to_async
from django.conf import settings

from WebSite.models.opt_model import UserOTP


logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()



@sync_to_async
def get_otp_by_session(session_id: str):
    try:
        otp = UserOTP.objects.get(session_id=session_id)
        if otp.is_valid:
            return otp.code
    except (UserOTP.DoesNotExist, ValueError):
        return None
    return None



@dp.message(CommandStart(deep_link=True))
async def command_start_with_link(message: types.Message, command: CommandObject):
    session_id = command.args

    if session_id:
        code = await get_otp_by_session(session_id)
        if code:
            await message.answer(
                f"Здравствуйте, <b>{message.from_user.first_name}</b>! \n\n"
                f"Ваш код для подтверждения регистрации на сайте:\n"
                f"<code>{code}</code>\n\n"
                f"Вернитесь на сайт и введите этот код."
            )
        else:
            await message.answer(" Ошибка: Сессия истекла, недействительна или уже использована.")
    else:
        await message.answer("Добро пожаловать!")


@dp.message(CommandStart())
async def standard_start(message: types.Message):
    await message.answer("Привет! Перейди на сайт, чтобы зарегистрироваться.")