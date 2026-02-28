from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
import calendar


def format_date(dt: date) -> str:
    return dt.strftime('%Y-%m-%d')


def parse_date(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))


def get_month_range(year: int, month: int) -> tuple:
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day


def get_last_month() -> tuple:
    today = date.today()
    if today.month == 1:
        last_month = 12
        year = today.year - 1
    else:
        last_month = today.month - 1
        year = today.year
    
    return get_month_range(year, last_month)


def build_query_params(**kwargs) -> Dict[str, Any]:
    params = {}
    for key, value in kwargs.items():
        if value is not None:
            if isinstance(value, date):
                params[key] = format_date(value)
            elif isinstance(value, bool):
                params[key] = str(value).lower()
            else:
                params[key] = value
    return params


def group_time_entries_by_project(time_entries: List[Any]) -> Dict[str, Dict[str, Any]]:
    grouped = {}
    
    for entry in time_entries:
        project_key = f"{entry.project_id}_{entry.project_name or 'Unknown'}"
        
        if project_key not in grouped:
            grouped[project_key] = {
                'project_id': entry.project_id,
                'project_name': entry.project_name or 'Unknown Project',
                'customer_id': entry.customer_id,
                'customer_name': entry.customer_name or 'Unknown Customer',
                'total_minutes': 0,
                'total_hours': 0.0,
                'total_revenue': 0.0,
                'entries_count': 0,
                'entries': []
            }
        
        grouped[project_key]['total_minutes'] += entry.minutes
        grouped[project_key]['total_hours'] += entry.hours
        # revenue ist bereits in der korrekten Einheit (Cent), summiere direkt
        grouped[project_key]['total_revenue'] += entry.revenue or 0
        grouped[project_key]['entries_count'] += 1
        grouped[project_key]['entries'].append(entry)
    
    # Round hours for better readability, keep revenue in Cent for now
    for project_data in grouped.values():
        project_data['total_hours'] = round(project_data['total_hours'], 2)
        # total_revenue bleibt in Cent für genaue Berechnungen
    
    return grouped


def format_project_summary(grouped_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary = []
    
    for project_key, data in grouped_data.items():
        summary.append({
            'project_id': data['project_id'],
            'project_name': data['project_name'],
            'customer_id': data['customer_id'], 
            'customer_name': data['customer_name'],
            'total_hours': data['total_hours'],
            'total_minutes': data['total_minutes'],
            'total_revenue': data['total_revenue'],
            'entries_count': data['entries_count'],
            'average_hours_per_entry': round(data['total_hours'] / data['entries_count'], 2) if data['entries_count'] > 0 else 0
        })
    
    return sorted(summary, key=lambda x: x['total_hours'], reverse=True)