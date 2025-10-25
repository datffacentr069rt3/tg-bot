#!/usr/bin/env python3
# aiogram v2 bot — Заказы -> пересылка админу(ам)
# ВНИМАНИЕ: вставьте свой токен и ADMIN_IDS в переменные ниже перед запуском.

import logging
import sys
import asyncio
from typing import List

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.utils.exceptions import BotBlocked, ChatNotFound
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ----------------------------
# Настройки — ВСТАВЬТЕ СЮДА СВОИ ЗНАЧЕНИЯ
# ----------------------------
TOKEN = "8095234010:AAEWFdldpwEwquMhwD4AFA-QP8x_03gDgLo"        # <-- вставьте сюда токен (строка)
# ADMIN_IDS — список числовых id админов, которым будут приходить заявки
# Пример: ADMIN_IDS = [123456789, 987654321]
ADMIN_IDS: List[int] = [8243943192]  # <-- замените на ваш(и) числовой(е) ID

# Проверки
if TOKEN == "ВАШ_ТОКЕН_ЗДЕСЬ" or not TOKEN:
    raise SystemExit("Ошибка: вставьте реальный токен в переменную TOKEN в этом файле.")
if not isinstance(ADMIN_IDS, list) or not all(isinstance(i, int) for i in ADMIN_IDS):
    raise SystemExit("Ошибка: ADMIN_IDS должен быть списком числовых id, например [123456789].")

# ----------------------------
# Инициализация
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)

# ----------------------------
# Кнопки/константы
# ----------------------------
BTN_PRICES = "💰 Узнать цены"
BTN_PORTFOLIO = "🌐 Портфолио"
BTN_CONTACTS = "📞 Связаться"
BTN_CASES = "💼 Кейсы"
BTN_ORDER = "📝 Заказать"
BTN_HELP = "❓ Помощь"

def make_main_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton(BTN_PRICES), types.KeyboardButton(BTN_PORTFOLIO))
    kb.add(types.KeyboardButton(BTN_CONTACTS), types.KeyboardButton(BTN_CASES))
    kb.add(types.KeyboardButton(BTN_ORDER), types.KeyboardButton(BTN_HELP))
    return kb

# ----------------------------
# FSM состояния
# ----------------------------
class Order(StatesGroup):
    waiting_for_description = State()

# ----------------------------
# Тексты
# ----------------------------
START_TEXT = "Ассаламу алейкум 👋\nЯ — WebStudioIng Bot. Выберите пункт меню ниже."
PRICES_TEXT = (
    "💰 Прайс‑ориентиры:\n\n"
    "• 💻 Лендинг — от 10 000 ₽\n"
    "• 🤖 Telegram‑бот — от 8 000 ₽\n"
    "• 🎨 Логотип — от 5 000 ₽\n\n"
    "Для точной сметы опишите проект."
)
PORTFOLIO_URL = "https://datffacentr069rt3.github.io/portfolio-my/"
ORDER_PROMPT = "Опишите, пожалуйста, ваш проект (что нужно, сроки, бюджет). Можно прикрепить файлы/скрины."

# ----------------------------
# Хэндлеры
# ----------------------------
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.reply(START_TEXT, reply_markup=make_main_keyboard())

@dp.message_handler(lambda m: m.text and m.text.strip() == BTN_PRICES)
async def handle_prices(message: types.Message):
    await message.answer(PRICES_TEXT)

@dp.message_handler(lambda m: m.text and m.text.strip() == BTN_PORTFOLIO)
async def handle_portfolio(message: types.Message):
    await message.answer(f"Портфолио: {PORTFOLIO_URL}")

@dp.message_handler(lambda m: m.text and m.text.strip() == BTN_CONTACTS)
async def handle_contacts(message: types.Message):
    await message.answer("📩 Telegram: @твой_ник_в_TG\n📧 webstudioing@mail.com")

@dp.message_handler(lambda m: m.text and m.text.strip() == BTN_CASES)
async def handle_cases(message: types.Message):
    await message.answer("Кейсы: лендинг — +30% конверсии, бот‑поддержка — автоматизация заказов.")

@dp.message_handler(lambda m: m.text and m.text.strip() == BTN_HELP)
async def handle_help(message: types.Message):
    await message.answer("/start — показать меню\nИли используйте кнопки.")

# Начать заказ — переводим в состояние ожидания описания
@dp.message_handler(lambda m: m.text and m.text.strip() == BTN_ORDER)
async def cmd_order(message: types.Message):
    await message.answer(ORDER_PROMPT, reply_markup=types.ReplyKeyboardRemove())
    await Order.waiting_for_description.set()

# Принимаем текстовое описание
@dp.message_handler(state=Order.waiting_for_description, content_types=types.ContentTypes.TEXT)
async def process_order_description_text(message: types.Message, state: FSMContext):
    description = message.text.strip()
    await _send_order_to_admins(message.from_user, description_text=description, message_obj=message)
    # Подтверждаем пользователю и завершаем состояние
    await message.answer("Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.", reply_markup=make_main_keyboard())
    await state.finish()

# Принимаем файлы/фото/документы — пересылаем администраторам и просим текст, если нужно
@dp.message_handler(state=Order.waiting_for_description, content_types=types.ContentTypes.ANY)
async def process_order_description_any(message: types.Message, state: FSMContext):
    # Если это фото
    try:
        if message.photo:
            # берем файл с наибольшим разрешением
            photo = message.photo[-1]
            caption = message.caption or ""
            await _forward_media_to_admins(message, media_type="photo", file_id=photo.file_id, caption=caption)
            # если есть подпись/описание, отправим его отдельно
            if caption:
                await _send_order_to_admins(message.from_user, description_text=caption, message_obj=message)
            await message.answer("Фото получено. Спасибо! Мы свяжемся с вами.", reply_markup=make_main_keyboard())
            await state.finish()
            return

        if message.document:
            doc = message.document
            caption = message.caption or ""
            await _forward_media_to_admins(message, media_type="document", file_id=doc.file_id, caption=caption, filename=doc.file_name)
            if caption:
                await _send_order_to_admins(message.from_user, description_text=caption, message_obj=message)
            await message.answer("Файл получен. Спасибо! Мы свяжемся с вами.", reply_markup=make_main_keyboard())
            await state.finish()
            return

        if message.video:
            video = message.video
            caption = message.caption or ""
            await _forward_media_to_admins(message, media_type="video", file_id=video.file_id, caption=caption)
            if caption:
                await _send_order_to_admins(message.from_user, description_text=caption, message_obj=message)
            await message.answer("Видео получено. Спасибо! Мы свяжемся с вами.", reply_markup=make_main_keyboard())
            await state.finish()
            return

        # Если другое — попрошим прислать текстовое описание
        await message.answer("Пожалуйста, пришлите описание проекта текстом или прикрепите файл/скриншот с подписью.")
    except Exception as e:
        logging.exception("Ошибка при обработке вложения: %s", e)
        await message.answer("Произошла ошибка при обработке вашего файла. Попробуйте отправить файл ещё раз.")
        await state.finish()

# Универсальная функция: отправка текста админу(ам)
async def _send_order_to_admins(user: types.User, description_text: str, message_obj: types.Message = None):
    username = f"@{user.username}" if user.username else "—"
    name = " ".join(filter(None, [user.first_name, user.last_name])).strip() or "—"
    user_id = user.id

    admin_message = (
        f"🆕 Новая заявка на заказ\n\n"
        f"Отправитель: {name}\n"
        f"Username: {username}\n"
        f"User ID: {user_id}\n\n"
        f"Описание:\n{description_text}"
    )

    for admin in ADMIN_IDS:
        try:
            await bot.send_message(admin, admin_message)
        except BotBlocked:
            logging.warning("Не удалось отправить заявку админу %s — бот заблокирован.", admin)
        except ChatNotFound:
            logging.warning("Чат с админом %s не найден (возможно, админ не запускал бота).", admin)
        except Exception as e:
            logging.exception("Ошибка при отправке админу %s: %s", admin, e)

# Универсальная функция: пересылка медиа (мы используем send_... с file_id чтобы переслать)
async def _forward_media_to_admins(message: types.Message, media_type: str, file_id: str, caption: str = "", filename: str = None):
    """
    media_type: 'photo' | 'document' | 'video'
    """
    for admin in ADMIN_IDS:
        try:
            if media_type == "photo":
                await bot.send_photo(admin, photo=file_id, caption=f"Отправитель: {message.from_user.id}\n{caption}")
            elif media_type == "document":
                await bot.send_document(admin, document=file_id, caption=f"Отправитель: {message.from_user.id}\n{caption}")
            elif media_type == "video":
                await bot.send_video(admin, video=file_id, caption=f"Отправитель: {message.from_user.id}\n{caption}")
        except BotBlocked:
            logging.warning("Не удалось переслать медиа админу %s — бот заблокирован.", admin)
        except ChatNotFound:
            logging.warning("Чат с админом %s не найден при пересылке медиа.", admin)
        except Exception as e:
            logging.exception("Ошибка при пересылке медиа админу %s: %s", admin, e)

# Универсальный fallback
@dp.message_handler()
async def fallback(message: types.Message):
    text = (message.text or "").strip()
    logging.info("Входящее сообщение от %s (id=%s): %r", getattr(message.from_user, "username", None), message.from_user.id, text)
    await message.reply("Не распознал команду. Пожалуйста, выберите пункт меню ниже.", reply_markup=make_main_keyboard())

# ----------------------------
# Event loop fix for Windows + new Python builds
# ----------------------------
def setup_event_loop_for_windows():
    try:
        if sys.platform.startswith("win"):
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            except Exception:
                pass
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except Exception as e:
        logging.warning("Не удалось явно настроить event loop: %s", e)

# ----------------------------
# Запуск
# ----------------------------
if __name__ == "__main__":
    setup_event_loop_for_windows()
    executor.start_polling(dp, skip_updates=True)