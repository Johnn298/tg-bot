# gcalendar.py — работа с Google Календарём (с проверкой занятости и отменой)

import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Авторизация в Google Calendar через Service Account"""
    try:
        creds = service_account.Credentials.from_service_account_file(
            'credentials_calendar.json', scopes=SCOPES
        )
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Ошибка авторизации в Google Calendar: {e}")
        return None

def get_busy_slots(date):
    """
    Получить занятые слоты на дату из Google Календаря
    
    date: "2026-07-15"
    Возвращает: список занятых часов ["10:00", "14:00", ...]
    """
    service = get_calendar_service()
    if not service:
        return []
    
    try:
        start_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date + datetime.timedelta(days=1)
        
        start_str = start_date.isoformat() + "+03:00"
        end_str = end_date.isoformat() + "+03:00"
        
        events_result = service.events().list(
            calendarId=config.CALENDAR_ID,
            timeMin=start_str,
            timeMax=end_str,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        busy_slots = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if start:
                try:
                    time_str = start.split('T')[1][:5]
                    busy_slots.append(time_str)
                except:
                    pass
        
        return busy_slots
        
    except Exception as e:
        print(f"❌ Ошибка получения занятых слотов: {e}")
        return []

def get_free_slots(date):
    """
    Получить свободные слоты на дату (9:00 - 21:00)
    Возвращает: список слотов с пометкой free=True/False
    """
    busy_slots = get_busy_slots(date)
    
    free_slots = []
    for hour in range(9, 21):
        time_str = f"{hour:02d}:00"
        is_free = time_str not in busy_slots
        free_slots.append({
            'start': time_str,
            'end': f"{hour+1:02d}:00",
            'free': is_free
        })
    
    return free_slots

def create_training_event(user_name, date, time_start, duration=60):
    """
    Создаёт событие в Google Календаре (без выбора тренера)
    
    user_name: ФИО клиента
    date: "2026-07-15"
    time_start: "10:00"
    duration: 60 (минут)
    
    Возвращает: ссылку на событие
    """
    service = get_calendar_service()
    if not service:
        return {'success': False, 'error': 'Ошибка авторизации'}
    
    try:
        start_datetime = datetime.datetime.strptime(
            f"{date} {time_start}", "%Y-%m-%d %H:%M"
        )
    except:
        return {'success': False, 'error': 'Неверный формат даты'}
    
    end_datetime = start_datetime + datetime.timedelta(minutes=duration)
    
    start_str = start_datetime.isoformat() + "+03:00"
    end_str = end_datetime.isoformat() + "+03:00"
    
    event = {
        'summary': f'🏋️ Тренировка - {user_name}',
        'description': (
            f'👤 Клиент: {user_name}\n'
            f'⏰ Длительность: {duration} мин.'
        ),
        'start': {
            'dateTime': start_str,
            'timeZone': 'Europe/Moscow',
        },
        'end': {
            'dateTime': end_str,
            'timeZone': 'Europe/Moscow',
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 60},
                {'method': 'popup', 'minutes': 15}
            ]
        }
    }
    
    try:
        event = service.events().insert(
            calendarId=config.CALENDAR_ID,
            body=event,
            sendNotifications=True
        ).execute()
        
        return {
            'success': True,
            'event_id': event['id'],
            'link': event.get('htmlLink', ''),
            'start': start_str,
            'end': end_str
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def delete_training_event(event_id):
    """
    Удаляет событие из Google Календаря
    
    event_id: ID события (из Google Calendar)
    """
    service = get_calendar_service()
    if not service:
        return {'success': False, 'error': 'Ошибка авторизации'}
    
    try:
        service.events().delete(
            calendarId=config.CALENDAR_ID,
            eventId=event_id
        ).execute()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_user_events(user_name, date=None):
    """
    Получить события пользователя по имени (для отмены)
    """
    service = get_calendar_service()
    if not service:
        return []
    
    try:
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        start_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date + datetime.timedelta(days=7)  # Ищем на неделю вперёд
        
        start_str = start_date.isoformat() + "+03:00"
        end_str = end_date.isoformat() + "+03:00"
        
        events_result = service.events().list(
            calendarId=config.CALENDAR_ID,
            timeMin=start_str,
            timeMax=end_str,
            q=user_name,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        result = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            result.append({
                'id': event['id'],
                'summary': event.get('summary', 'Тренировка'),
                'start': start,
                'link': event.get('htmlLink', '')
            })
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка получения событий пользователя: {e}")
        return []
