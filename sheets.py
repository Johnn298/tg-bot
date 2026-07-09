# sheets.py — исправленная версия

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import config

class SheetManager:
    def __init__(self):
        scope = ["https://spreadsheets.google.com/feeds", 
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            config.CREDENTIALS_FILE, scope
        )
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(config.SHEET_ID).sheet1
        
        headers = self.sheet.row_values(1)
        if not headers:
            print("📊 Создаю заголовки в таблице...")
            self.sheet.append_row([
                "Дата", "TG ID", "Username", "ФИО", "Номер телефона",
                "Рефералов", "Рефералы (список)", "Кто привел"
            ])
    
    def _get_records_safe(self):
        try:
            rows = self.sheet.get_all_records()
            return rows if rows else []
        except IndexError:
            return []
    
    def user_exists(self, tg_id: int) -> bool:
        records = self._get_records_safe()
        return any(str(record.get("TG ID", "")) == str(tg_id) for record in records)
    
    def get_user_data(self, tg_id: int) -> dict:
        records = self._get_records_safe()
        for record in records:
            if str(record.get("TG ID", "")) == str(tg_id):
                return record
        return None
    
    def add_user(self, tg_id: int, username: str, fio: str, phone: str, 
                 referred_by: str = None, referral_code: str = None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not referral_code:
            referral_code = f"REF{tg_id}"
        
        row = [
            now,
            str(tg_id),
            username or "",
            fio,
            phone,
            0,          # Рефералов
            "",         # Рефералы (список) — всегда строка!
            referred_by or ""
        ]
        self.sheet.append_row(row)
        return referral_code
    
    def update_referral(self, tg_id: int, referrer_tg_id: int):
        all_rows = self.sheet.get_all_values()
        referrer_row = None
        
        for i, row in enumerate(all_rows, 1):
            if row and len(row) > 1 and row[1] == str(referrer_tg_id):
                referrer_row = i
                break
        
        if not referrer_row:
            return False
        
        try:
            # Обновляем счётчик (колонка 6)
            current_count = int(self.sheet.cell(referrer_row, 6).value or 0)
            self.sheet.update_cell(referrer_row, 6, current_count + 1)
            
            # Обновляем список (колонка 7) — всегда как строка
            current_list = str(self.sheet.cell(referrer_row, 7).value or "")
            new_list = f"{current_list}, {tg_id}" if current_list else str(tg_id)
            self.sheet.update_cell(referrer_row, 7, new_list)
            return True
        except Exception as e:
            print(f"Ошибка обновления рефералов: {e}")
            return False
    
    def get_referral_stats(self, tg_id: int) -> dict:
        user_data = self.get_user_data(tg_id)
        if not user_data:
            return {"count": 0, "list": []}
        
        # ✅ Исправлено: всегда работаем со строкой
        count = int(user_data.get("Рефералов", 0) or 0)
        ref_list = str(user_data.get("Рефералы (список)", "") or "")
        
        return {
            "count": count,
            "list": [x.strip() for x in ref_list.split(",") if x.strip()]
        }
