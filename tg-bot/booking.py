# booking.py — логика записи на тренировку

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import config
from sheets import SheetManager
from calendar import create_training_event, get_free_slots

# Состояния для регистрации
DATE, TIME, TRAINER, CONFIRM = range(4)

sheet = SheetManager()

# ---------- Тренеры ----------
TRAINERS = {
    "alex": "👨‍🏫 Александр (бокс)",
    "dmitry": "👨‍🏫 Дмитрий (ММА)",
    "elena": "👩‍🏫 Елена (фитнес)"
}

def get_date_keyboard():
    """Клавиатура с выбором даты (следующие 7 дней)"""
    keyboard = []
    today = datetime.now()
    
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
        month_day = date.strftime("%d.%m")
        keyboard.append([
            InlineKeyboardButton(
                f"{day_name} {month_day}", 
                callback_data=f"date_{date_str}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")])
    return InlineKeyboardMarkup(keyboard)

def get_time_keyboard(free_slots):
    """Клавиатура с выбором времени"""
    keyboard = []
    for slot in free_slots:
        keyboard.append([
            InlineKeyboardButton(
                f"{slot['start']} - {slot['end']}", 
                callback_data=f"time_{slot['start']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")])
    return InlineKeyboardMarkup(keyboard)

def get_trainer_keyboard():
    """Клавиатура с выбором тренера"""
    keyboard = []
    for key, name in TRAINERS.items():
        keyboard.append([
            InlineKeyboardButton(name, callback_data=f"trainer_{key}")
        ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")])
    return InlineKeyboardMarkup(keyboard)

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало записи на тренировку (выбираем дату)"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📅 **Запись на тренировку**\n\n"
        "Выберите дату:",
        reply_markup=get_date_keyboard(),
        parse_mode="Markdown"
    )
    return DATE

async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор даты"""
    query = update.callback_query
    await query.answer()
    
    date = query.data.replace("date_", "")
    context.user_data["booking_date"] = date
    
    # Получаем свободные слоты
    free_slots = get_free_slots(date)
    
    if not free_slots:
        await query.edit_message_text(
            "😔 **Нет свободных слотов на эту дату.**\n\n"
            "Попробуйте выбрать другой день.",
            reply_markup=get_date_keyboard(),
            parse_mode="Markdown"
        )
        return DATE
    
    # Показываем время
    await query.edit_message_text(
        f"📅 **Дата:** {date}\n\n"
        "🕐 **Выберите время:**",
        reply_markup=get_time_keyboard(free_slots),
        parse_mode="Markdown"
    )
    return TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор времени"""
    query = update.callback_query
    await query.answer()
    
    time = query.data.replace("time_", "")
    context.user_data["booking_time"] = time
    
    await query.edit_message_text(
        f"📅 **Дата:** {context.user_data['booking_date']}\n"
        f"🕐 **Время:** {time}\n\n"
        "👨‍🏫 **Выберите тренера:**",
        reply_markup=get_trainer_keyboard(),
        parse_mode="Markdown"
    )
    return TRAINER

async def select_trainer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор тренера и создание события"""
    query = update.callback_query
    await query.answer()
    
    trainer_key = query.data.replace("trainer_", "")
    trainer_name = TRAINERS.get(trainer_key, trainer_key)
    
    user = update.effective_user
    tg_id = user.id
    user_data = sheet.get_user_data(tg_id)
    user_name = user_data.get("ФИО", user.first_name) if user_data else user.first_name
    
    date = context.user_data["booking_date"]
    time = context.user_data["booking_time"]
    
    # Создаём событие в Google Календаре
    result = create_training_event(
        user_name=user_name,
        trainer=trainer_name,
        date=date,
        time_start=time
    )
    
    if result['success']:
        message = (
            f"✅ **Вы записаны на тренировку!**\n\n"
            f"📅 **Дата:** {date}\n"
            f"🕐 **Время:** {time}\n"
            f"👨‍🏫 **Тренер:** {trainer_name}\n\n"
            f"📲 **Событие добавлено в Google Календарь!**\n"
            f"🔗 [Открыть в календаре]({result['link']})\n\n"
            f"🔔 **Напомним о тренировке за час.**\n\n"
            f"📍 Адрес: ул. Спортивная, 15\n"
            f"📱 Менеджер: @spotdirect"
        )
        
        # Сохраняем запись в Google Sheets (дополнительная колонка)
        # Можно добавить отдельную таблицу для записей
        
        await query.edit_message_text(
            message,
            reply_markup=get_menu_button(),
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
    else:
        await query.edit_message_text(
            f"❌ **Ошибка при записи!**\n\n"
            f"{result.get('error', 'Попробуйте позже или свяжитесь с менеджером.')}",
            reply_markup=get_menu_button(),
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена записи"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ Запись отменена.",
        reply_markup=get_menu_button(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END
