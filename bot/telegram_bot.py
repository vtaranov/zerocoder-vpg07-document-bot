"""Telegram transport. Sequential processing keeps request attachments isolated."""
import logging
from io import BytesIO
import telebot
from config import load_config
from service import DocumentBot
HELP = """VPg07: персональный помощник с памятью Haystack + Pinecone.
Пришлите PDF/DOCX/MD/TXT до 10 МБ: сохраню фрагменты и дам краткое резюме.\nМогу получить факт о кошках, фото собаки с описанием, текущую погоду и вспомнить ваши сообщения.
/help - справка; /clear - инструкция очистки; /clear confirm - удалить свою память.
Сообщения передаются в OpenAI и Pinecone; внешние инструменты вызываются по запросу."""

def owner_for(message):
    return f"telegram:{message.chat.id}:{message.from_user.id}"
def deliver(bot, chat_id, result):
    for a in result["attachments"]:
        photo = BytesIO(a["bytes"])
        photo.name = "dog.jpg"
        caption = a["caption"]
        bot.send_photo(chat_id, photo, caption=caption[:1000])
        if len(caption) > 1000:
            for start in range(1000, len(caption), 3500):
                bot.send_message(chat_id, caption[start:start+3500])
    for start in range(0, len(result["answer"]), 3500):
        bot.send_message(chat_id, result["answer"][start:start+3500])

def build_bot(config, service, bot=None):
    bot = bot or telebot.TeleBot(config.bot_token, threaded=False)
    @bot.message_handler(content_types=["document"])
    def document(message):
        import tempfile
        from pathlib import Path
        from components.documents import SUPPORTED, MAX_BYTES
        if not message.from_user or message.from_user.id not in config.allowed_users or message.chat.type != "private":
            return
        name = Path(message.document.file_name or "document").name
        if Path(name).suffix.lower() not in SUPPORTED or not 0 < (message.document.file_size or 0) <= MAX_BYTES:
            bot.send_message(message.chat.id, "Поддерживаются PDF/DOCX/MD/TXT до 10 МБ.")
            return
        bot.send_message(message.chat.id, "Файл получен. Запускаю анализ и сохранение. Это может занять немного времени…")
        try:
            info = bot.get_file(message.document.file_id)
            payload = bot.download_file(info.file_path)
            if len(payload)>MAX_BYTES:
                raise ValueError("Превышен размер файла")
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / ("upload" + Path(name).suffix.lower())
                path.write_bytes(payload)
                result = service.ingest(owner_for(message), path, name)
            bot.send_message(message.chat.id, "Готово. Я изучил этот файл, теперь можем его обсудить.")
            bot.send_message(message.chat.id, result["summary"])
        except Exception as exc:
            logging.getLogger(__name__).error("document_error=%s",type(exc).__name__)
            bot.send_message(message.chat.id, "Обработка не завершена. Если ошибка возникла после записи, фрагменты могли сохраниться; повторная загрузка одинакового файла не создаёт дубли.")
    @bot.message_handler(content_types=["text"])
    def handle(message):
        if not message.from_user or message.from_user.id not in config.allowed_users or message.chat.type != "private":
            return
        owner = owner_for(message)
        text = message.text or ""
        try:
            if text.split() and text.split()[0] in {"/start", "/help"}:
                bot.send_message(message.chat.id, HELP)
            elif text == "/clear":
                bot.send_message(message.chat.id, "Для удаления вашей памяти VPg07: /clear confirm")
            elif text == "/clear confirm":
                service.clear(owner)
                bot.send_message(message.chat.id, "Ваша память VPg07 очищена.")
            elif text.startswith("/"):
                bot.send_message(message.chat.id, "Неизвестная команда. /help")
            else:
                deliver(bot, message.chat.id, service.handle(owner, text))
        except Exception as exc:
            logging.getLogger(__name__).error("request_error=%s", type(exc).__name__)
            bot.send_message(message.chat.id, "Ошибка обработки. Сообщение могло сохраниться в памяти. Повторите позже.")
    return bot

def main():
    import fcntl
    import hashlib
    from pathlib import Path
    from config import ROOT
    logging.basicConfig(level=logging.INFO)
    for name in ["httpx", "httpcore", "urllib3", "telebot"]:
        logging.getLogger(name).setLevel(logging.CRITICAL)
    config = load_config(require_bot=True)
    # Shared token lock between copies of this application on this Mac.
    lock = (Path("/tmp") / ("zerocoder-telegram-" + hashlib.sha256(config.bot_token.encode()).hexdigest()[:16] + ".lock")).open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("VPg07 уже запущен.")
    bot = build_bot(config, DocumentBot(config))
    if bot.get_webhook_info().url:
        raise RuntimeError("У токена активен webhook; polling не запущен.")
    print("VPg07 bot ready:", bot.get_me().username, flush=True)
    try:
        bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20, allowed_updates=["message"])
    finally:
        bot.stop_polling()
if __name__ == "__main__":
    main()
