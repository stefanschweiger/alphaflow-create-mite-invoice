from typing import List, Dict, Any, Optional, Union
from datetime import date, datetime, timedelta
import calendar

from ..models import TimeEntry
from ..utils import build_query_params, get_month_range, get_last_month, group_time_entries_by_project, format_project_summary


class TimeEntriesEndpoint:
    def __init__(self, client):
        self.client = client
    
    def list(self, **kwargs) -> List[TimeEntry]:
        params = build_query_params(**kwargs)
        response = self.client.get('time_entries.json', params=params)
        
        time_entries = []
        for item in response:
            time_entries.append(TimeEntry.from_dict(item))
        
        return time_entries
    
    def get(self, entry_id: int) -> TimeEntry:
        response = self.client.get(f'time_entries/{entry_id}.json')
        return TimeEntry.from_dict(response)
    
    def create(self, date_at: Union[str, date], minutes: int, project_id: Optional[int] = None, 
               service_id: Optional[int] = None, note: Optional[str] = None, user_id: Optional[int] = None) -> TimeEntry:
        data = {
            'time-entry': {
                'date-at': date_at if isinstance(date_at, str) else date_at.strftime('%Y-%m-%d'),
                'minutes': minutes
            }
        }
        
        if project_id:
            data['time-entry']['project-id'] = project_id
        if service_id:
            data['time-entry']['service-id'] = service_id
        if note:
            data['time-entry']['note'] = note
        if user_id:
            data['time-entry']['user-id'] = user_id
        
        response = self.client.post('time_entries.json', data)
        return TimeEntry.from_dict(response)
    
    def update(self, entry_id: int, **kwargs) -> Optional[TimeEntry]:
        data = {'time-entry': {}}

        field_mapping = {
            'date_at': 'date-at',
            'minutes': 'minutes',
            'note': 'note',
            'project_id': 'project-id',
            'service_id': 'service-id',
            'user_id': 'user-id',
            'billable': 'billable',
            'locked': 'locked'
        }

        for key, value in kwargs.items():
            if key in field_mapping and value is not None:
                api_key = field_mapping[key]
                if key == 'date_at' and isinstance(value, date):
                    value = value.strftime('%Y-%m-%d')
                data['time-entry'][api_key] = value

        response = self.client.patch(f'time_entries/{entry_id}.json', data)
        # Die mite API gibt bei erfolgreichen Updates eine leere Response zurück
        # In diesem Fall geben wir None zurück, da das Update erfolgreich war
        if not response or not response.get('time-entry') and not response.get('time_entry'):
            return None
        return TimeEntry.from_dict(response)
    
    def delete(self, entry_id: int) -> bool:
        return self.client.delete(f'time_entries/{entry_id}.json')
    
    def get_daily(self, target_date: Optional[date] = None, user_id: Optional[int] = None) -> List[TimeEntry]:
        params = {}
        if target_date:
            params['at'] = target_date.strftime('%Y-%m-%d')
        else:
            params['at'] = 'today'
        
        if user_id:
            params['user_id'] = user_id
        
        return self.list(**params)
    
    def get_weekly(self, target_date: Optional[date] = None, user_id: Optional[int] = None) -> List[TimeEntry]:
        params = {'at': 'this_week'}
        if target_date:
            # Calculate week start (Monday)
            days_since_monday = target_date.weekday()
            week_start = target_date - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            params = {
                'from': week_start,
                'to': week_end
            }
        
        if user_id:
            params['user_id'] = user_id
        
        return self.list(**params)
    
    def get_monthly(self, year: Optional[int] = None, month: Optional[int] = None, 
                    user_id: Optional[int] = None) -> List[TimeEntry]:
        if year and month:
            first_day, last_day = get_month_range(year, month)
        else:
            first_day, last_day = get_last_month()
        
        params = {
            'from': first_day,
            'to': last_day
        }
        
        if user_id:
            params['user_id'] = user_id
        
        return self.list(**params)
    
    def get_date_range(self, from_date: date, to_date: date, user_id: Optional[int] = None,
                       project_id: Optional[int] = None, customer_id: Optional[int] = None,
                       billable: Optional[bool] = None, locked: Optional[bool] = None) -> List[TimeEntry]:
        params = {
            'from': from_date,
            'to': to_date
        }

        if user_id:
            params['user_id'] = user_id
        if project_id:
            params['project_id'] = project_id
        if customer_id:
            params['customer_id'] = customer_id
        if billable is not None:
            params['billable'] = billable
        if locked is not None:
            params['locked'] = locked

        return self.list(**params)
    
    def group_by_project(self, time_entries: List[TimeEntry]) -> Dict[str, Dict[str, Any]]:
        return group_time_entries_by_project(time_entries)
    
    def get_project_summary(self, time_entries: List[TimeEntry]) -> List[Dict[str, Any]]:
        grouped = self.group_by_project(time_entries)
        return format_project_summary(grouped)
    
    def get_monthly_project_summary(self, year: Optional[int] = None, month: Optional[int] = None) -> List[Dict[str, Any]]:
        entries = self.get_monthly(year, month)
        return self.get_project_summary(entries)