def send_otp_to_telegram(identifier: str, code: str) -> bool:
    """
    Отправить OTP‑код пользователю через Telegram‑бот.
    identifier: phone_number или user_id
    code: 6-значный код
    Returns: True при успехе
    """
    # TODO: вызвать API бота или отправить в очередь
    # import requests
    # requests.post(BOT_WEBHOOK_URL, json={'identifier': identifier, 'code': code})
    return True
