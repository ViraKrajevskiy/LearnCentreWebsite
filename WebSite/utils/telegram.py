import json
import logging
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)

def send_telegram_message(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    if not chat_id or not settings.TELEGRAM_BOT_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": parse_mode}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return True
    except urllib.error.HTTPError as e:
        logger.warning("Telegram sendMessage failed: %s %s", e.code, e.read().decode())
    except Exception as e:
        logger.exception("Telegram send error: %s", e)
    return False
