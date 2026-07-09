# broadcast_scheduler.py — ПОЛНАЯ ФИНАЛЬНАЯ ВЕРСИЯ

import asyncio
import sys
from datetime import datetime
from telegram import Bot
import config
from sheets import SheetManager

def get_valid_users(sheet):
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

async def send_scheduled_broadcast(message: str):
    """Отправляет рассылку всем пользователям"""
    bot = Bot(token=config.BOT_TOKEN)
    sheet = SheetManager()
    
    users = get_valid_users(sheet)
    
    if not users:
        print(f"[{datetime.now()}] ⚠️ Нет зарегистрированных пользователей.")
        return
    
    sent = 0
    failed = 0
    
    print(f"[{datetime.now()}] 📨 Начинаю рассылку {len(users)} пользователям...")
    
    for tg_id in users:
        try:
            await bot.send_message(
                chat_id=tg_id,
                text=f"📢 {message}"
            )
            sent += 1
        except Exception as e:
            print(f"❌ Не удалось отправить {tg_id}: {e}")
            failed += 1
        await asyncio.sleep(0.05)
    
    print(f"[{datetime.now()}] ✅ Рассылка завершена! Отправлено: {sent}, Ошибок: {failed}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Использование: python broadcast_scheduler.py 'Текст сообщения'")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    asyncio.run(send_scheduled_broadcast(message))
