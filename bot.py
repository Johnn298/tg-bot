# bot.py — БАЗОВАЯ ВЕРСИЯ (без календаря и бронирования)

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)
import config
from sheets import SheetManager
from datetime import datetime
import asyncio
import os
import re

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

FIO, PHONE = range(2)
sheet = SheetManager()
CHANNEL_USERNAME = "spotind"

# ---------- Файлы для "О проекте" ----------
PHOTOS_FOLDER = "photos"
PHOTO_FILES = [
    {"file": "photo1.jpg", "caption": "SPOT — место, где собираются люди с общими интересами, знакомятся, становятся сильнее, поддерживают друг друга и просто кайфуют от процесса."},
    {"file": "photo2.jpg", "caption": "Здесь своя атмосфера, свой ритм, своё комьюнити."},
    {"file": "photo3.jpg", "caption": "Кто-то приходит за результатом, кто-то за перезагрузкой после рабочего дня."},
    {"file": "photo4.jpg", "caption": "Если ты ещё не был в SPOT — самое время познакомиться."},
    {"file": "photo5.jpg", "caption": ""}
]

# ---------- Проверка файлов ----------
def check_photos():
    missing = []
    for p in PHOTO_FILES:
        path = os.path.join(PHOTOS_FOLDER, p["file"])
        if not os.path.exists(path):
            missing.append(p["file"])
    if missing:
        logger.warning(f"⚠️ Отсутствуют файлы: {missing}")
        return False
    else:
        logger.info(f"✅ Все {len(PHOTO_FILES)} фото найдены")
        return True

PHOTOS_OK = check_photos()

# ---------- Утилиты ----------
def escape_md(text):
    """Экранирует спецсимволы для Markdown"""
    if not text:
        return ""
    chars = r'_*[]()~`>#+=|{}.!-'
    return re.sub(f'([{re.escape(chars)}])', r'\\\1', str(text))

def get_valid_users():
    """Получает список валидных TG ID из таблицы"""
    records = sheet.sheet.get_all_records()
    users = []
    for record in records:
        tg_id = record.get("TG ID")
        if tg_id and str(tg_id).strip() and str(tg_id) != "None":
            try:
                users.append(int(tg_id))
            except (ValueError, TypeError):
                continue
    return users

# ---------- Меню ----------
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 Реферальная программа", callback_data="referral")],
        [InlineKeyboardButton("🌐 Соц Сети", callback_data="social")],
        [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_subscribe_menu():
    keyboard = [
        [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ Я подписался", callback_data="subscribed_done")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_registration_menu():
    keyboard = [
        [InlineKeyboardButton("📝 Заполнить анкету", callback_data="fill_form")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_phone_keyboard():
    keyboard = [
        [KeyboardButton("📱 Отправить номер телефона", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_after_registration_menu():
    keyboard = [[InlineKeyboardButton("📋 MENU", callback_data="menu")]]
    return InlineKeyboardMarkup(keyboard)

def get_menu_button():
    keyboard = [[InlineKeyboardButton("📋 MENU", callback_data="menu")]]
    return InlineKeyboardMarkup(keyboard)

# ---------- Команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id = user.id
    
    if context.args and context.args[0].startswith("ref_"):
        referral_code = context.args[0][4:]
        referrer_tg_id = referral_code.replace("REF", "")
        if referrer_tg_id.isdigit():
            context.user_data["referred_by"] = referrer_tg_id
    
    if sheet.user_exists(tg_id):
        user_data = sheet.get_user_data(tg_id)
        name = user_data.get("ФИО", "друг") if user_data else "друг"
        await update.message.reply_text(
            f"👋 С возвращением, {escape_md(name)}!\n\n"
            "Вы уже зарегистрированы в нашей системе.",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
        return
    
    await update.message.reply_text(
        "👋 **Здравствуйте!**\nСпасибо за интерес к нашему проекту.",
        parse_mode="Markdown"
    )
    
    await update.message.reply_text(
        f"📢 **Подпишитесь на канал**,\nчтобы быть в курсе последних новостей.\n\nПосле подписки нажмите «Я подписался».",
        reply_markup=get_subscribe_menu(),
        parse_mode="Markdown"
    )

async def subscribed_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tg_id = update.effective_user.id
    if sheet.user_exists(tg_id):
        await query.edit_message_text(
            "✅ Вы уже зарегистрированы!",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
        return
    
    await query.edit_message_text(
        "🎁 **Вы у нас впервые?**\nУ нас действует акция на первое бесплатное посещение + бесплатная тренировка!",
        parse_mode="Markdown"
    )
    
    await context.bot.send_message(
        chat_id=tg_id,
        text="📝 **Для записи нам необходимы**\nВаши **ФИО** и **номер телефона**.",
        reply_markup=get_registration_menu(),
        parse_mode="Markdown"
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📋 **Главное меню**\n\nВыберите раздел:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "📋 **Главное меню**\n\nВыберите раздел:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )

# ---------- Регистрация ----------
async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("📝 **Введите Ваши ФИО:**", parse_mode="Markdown")
    else:
        await update.message.reply_text("📝 **Введите Ваши ФИО:**", parse_mode="Markdown")
    return FIO

async def get_fio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fio"] = update.message.text
    await update.message.reply_text(
        "📱 **Нажмите кнопку ниже**\nдля отправки номера телефона:",
        reply_markup=get_phone_keyboard(),
        parse_mode="Markdown"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text
    
    fio = context.user_data.get("fio")
    tg_id = update.effective_user.id
    username = update.effective_user.username or ""
    referred_by = context.user_data.get("referred_by")
    
    if sheet.user_exists(tg_id):
        await update.message.reply_text(
            "✅ Вы уже зарегистрированы!",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END
    
    referral_code = sheet.add_user(tg_id, username, fio, phone, referred_by)
    if referred_by:
        sheet.update_referral(tg_id, int(referred_by))
    
    await update.message.reply_text(
        "✅ **Спасибо!**\n\n"
        "Мы получили Вашу заявку.\n\n"
        "Наш менеджер свяжется\n"
        "с Вами в ближайшее время.",
        reply_markup=get_after_registration_menu(),
        parse_mode="Markdown"
    )
    
    # Отправка менеджеру БЕЗ parse_mode
    await context.bot.send_message(
        chat_id=config.MANAGER_CHAT_ID,
        text=f"📝 Новая заявка!\n\n"
             f"🆔 TG ID: {tg_id}\n"
             f"👤 Username: @{username or 'не указан'}\n"
             f"👤 ФИО: {fio}\n"
             f"📱 Телефон: {phone}\n"
             f"🔗 Реферальный код: {referral_code}\n"
             f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    return ConversationHandler.END

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Регистрация отменена.",
        reply_markup=get_menu_button()
    )
    return ConversationHandler.END

# ---------- Админ: рассылка ----------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != config.ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет прав для этой команды.")
        return
    
    if context.args:
        text = " ".join(context.args)
        context.user_data["broadcast_text"] = text
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, отправить", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")]
        ]
        await update.message.reply_text(
            f"📨 Подтвердите рассылку\n\n"
            f"Сообщение:\n"
            f"\"{text}\"\n\n"
            f"Будет отправлено всем зарегистрированным пользователям.\n\n"
            f"⏳ Это может занять несколько минут.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    context.user_data["awaiting_broadcast"] = True
    await update.message.reply_text(
        "📨 Введите текст для рассылки:\n\n"
        "Отправьте одно сообщение с текстом, который хотите разослать всем пользователям.\n\n"
        "❌ Чтобы отменить — отправьте /cancel"
    )

async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != config.ADMIN_ID:
        return
    
    if update.message.text == "/cancel":
        context.user_data["awaiting_broadcast"] = False
        context.user_data["broadcast_text"] = None
        await update.message.reply_text("❌ Рассылка отменена.")
        return
    
    if context.user_data.get("awaiting_broadcast"):
        text = update.message.text
        context.user_data["broadcast_text"] = text
        context.user_data["awaiting_broadcast"] = False
        
        keyboard = [
            [InlineKeyboardButton("✅ Да, отправить", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")]
        ]
        await update.message.reply_text(
            f"📨 Подтвердите рассылку\n\n"
            f"Сообщение:\n"
            f"\"{text}\"\n\n"
            f"Будет отправлено всем зарегистрированным пользователям.\n\n"
            f"⏳ Это может занять несколько минут.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if user.id != config.ADMIN_ID:
        await query.edit_message_text("⛔ У вас нет прав.")
        return
    
    text = context.user_data.get("broadcast_text")
    if not text:
        await query.edit_message_text("❌ Нет текста для рассылки.")
        return
    
    users = get_valid_users()
    
    if not users:
        await query.edit_message_text("⚠️ Нет зарегистрированных пользователей.")
        return
    
    broadcast_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    context.user_data["broadcast_active"] = True
    context.user_data["current_broadcast_id"] = broadcast_id
    
    await query.edit_message_text(
        f"📨 Начинаю рассылку {len(users)} пользователям...\n"
        f"🆔 ID рассылки: {broadcast_id}\n\n"
        f"Чтобы отменить рассылку — отправьте /stop_broadcast"
    )
    
    sent = 0
    failed = 0
    
    for tg_id in users:
        if not context.user_data.get("broadcast_active", True):
            await context.bot.send_message(
                chat_id=user.id,
                text=f"⛔ Рассылка отменена!\n"
                     f"📤 Отправлено: {sent}\n"
                     f"❌ Ошибок: {failed}"
            )
            return
        
        try:
            await context.bot.send_message(
                chat_id=tg_id,
                text=f"📢 {text}"
            )
            sent += 1
        except Exception as e:
            logger.error(f"Не удалось отправить {tg_id}: {e}")
            failed += 1
        await asyncio.sleep(0.05)
    
    context.user_data["broadcast_text"] = None
    context.user_data["broadcast_active"] = False
    context.user_data["current_broadcast_id"] = None
    
    await context.bot.send_message(
        chat_id=user.id,
        text=f"✅ Рассылка завершена!\n"
             f"📤 Отправлено: {sent}\n"
             f"❌ Ошибок: {failed}\n"
             f"🆔 ID: {broadcast_id}"
    )

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if user.id != config.ADMIN_ID:
        await query.edit_message_text("⛔ У вас нет прав.")
        return
    
    context.user_data["broadcast_text"] = None
    context.user_data["awaiting_broadcast"] = False
    context.user_data["broadcast_active"] = False
    context.user_data["current_broadcast_id"] = None
    
    await query.edit_message_text("❌ Рассылка отменена.")

async def stop_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != config.ADMIN_ID:
        await update.message.reply_text("⛔ У вас нет прав.")
        return
    
    if context.user_data.get("broadcast_active", False):
        context.user_data["broadcast_active"] = False
        await update.message.reply_text(
            f"⛔ Рассылка остановлена!\n"
            f"🆔 ID: {context.user_data.get('current_broadcast_id', 'неизвестен')}"
        )
    else:
        await update.message.reply_text("ℹ️ Активная рассылка не найдена.")

# ---------- Обработчик кнопок ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    tg_id = user.id
    data = query.data
    
    if data == "subscribed_done":
        await subscribed_done(update, context)
        return
    
    if data == "confirm_broadcast":
        await confirm_broadcast(update, context)
        return
    
    if data == "cancel_broadcast":
        await cancel_broadcast(update, context)
        return
    
    if data == "referral":
        stats = sheet.get_referral_stats(tg_id)
        referral_code = f"REF{tg_id}"
        referral_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{referral_code}"
        
        await query.edit_message_text(
            f"💰 **Реферальная программа**\n\n"
            f"👥 Ваших рефералов: {stats['count']}\n"
            f"⭐ Бонусов: {stats['count'] * config.REFERRAL_BONUS}\n\n"
            f"**Ваша ссылка:**\n`{referral_link}`\n\n"
            "Отправьте её друзьям — и получайте бонусы! 🎁",
            reply_markup=get_menu_button(),
            parse_mode="Markdown"
        )
        return
    
    if data == "social":
        keyboard = [
            [InlineKeyboardButton("📱 VK", url="https://vk.ru/spot_industrial")],
            [InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/spot.industrial")],
            [InlineKeyboardButton("🌐 Website", url="https://spot-gym.ru/tproduct/166347588652-trenazhernii-za")],
            [InlineKeyboardButton("📋 MENU", callback_data="menu")]
        ]
        await query.edit_message_text(
            "🌐 **Наши социальные сети**\n\nПодписывайтесь и следите за новостями!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return
    
    if data == "about":
        await query.message.delete()
        
        await context.bot.send_message(
            chat_id=tg_id,
            text="📖 **О проекте**\n\nСейчас я расскажу тебе о SPOT.",
            parse_mode="Markdown"
        )
        
        for p in PHOTO_FILES:
            photo_path = os.path.join(PHOTOS_FOLDER, p["file"])
            try:
                if os.path.exists(photo_path):
                    with open(photo_path, 'rb') as f:
                        await context.bot.send_photo(
                            chat_id=tg_id,
                            photo=f,
                            caption=p["caption"] if p["caption"] else None,
                            parse_mode="Markdown"
                        )
                else:
                    if p["caption"]:
                        await context.bot.send_message(
                            chat_id=tg_id,
                            text=f"📝 {p['caption']}",
                            parse_mode="Markdown"
                        )
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка отправки фото {photo_path}: {e}")
                if p["caption"]:
                    await context.bot.send_message(
                        chat_id=tg_id,
                        text=f"📝 {p['caption']}",
                        parse_mode="Markdown"
                    )
                await asyncio.sleep(0.5)
        
        await context.bot.send_message(
            chat_id=tg_id,
            text="📋 **Вернуться в меню**",
            reply_markup=get_menu_button(),
            parse_mode="Markdown"
        )
        return
    
    if data == "menu":
        await query.edit_message_text(
            "📋 **Главное меню**\n\nВыберите раздел:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
        return
    
    if data == "fill_form":
        context.user_data["tg_id"] = tg_id
        context.user_data["username"] = user.username or ""
        await query.edit_message_text("📝 **Введите Ваши ФИО:**", parse_mode="Markdown")
        return FIO

# ---------- Запуск ----------
def main():
    if not PHOTOS_OK:
        logger.warning("⚠️ Некоторые фото отсутствуют")
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stop_broadcast", stop_broadcast))
    app.add_handler(CommandHandler("cancel", cancel_registration))
    
    # Обработчик текста для рассылки
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_text))
    
    # Регистрация (Conversation)
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registration, pattern="^fill_form$")],
        states={
            FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fio)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )
    app.add_handler(conv)
    
    # Обработчик всех кнопок
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
