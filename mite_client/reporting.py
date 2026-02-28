from typing import List, Dict, Any, Optional, Union
from datetime import date, datetime
import pandas as pd
import json
import csv
from pathlib import Path

from .models import TimeEntry, Project
from .utils import get_last_month, get_month_range, format_project_summary, group_time_entries_by_project


class MonthlyReporter:
    def __init__(self, client):
        self.client = client
    
    def get_monthly_data(self, year: Optional[int] = None, month: Optional[int] = None, 
                        user_ids: Optional[List[int]] = None) -> List[TimeEntry]:
        if user_ids:
            all_entries = []
            for user_id in user_ids:
                entries = self.client.time_entries.get_monthly(year, month, user_id)
                all_entries.extend(entries)
            return all_entries
        else:
            return self.client.time_entries.get_monthly(year, month)
    
    def generate_project_summary(self, time_entries: List[TimeEntry]) -> List[Dict[str, Any]]:
        return self.client.time_entries.get_project_summary(time_entries)
    
    def generate_user_summary(self, time_entries: List[TimeEntry]) -> List[Dict[str, Any]]:
        user_data = {}
        
        for entry in time_entries:
            user_key = f"{entry.user_id}_{entry.user_name or 'Unknown'}"
            
            if user_key not in user_data:
                user_data[user_key] = {
                    'user_id': entry.user_id,
                    'user_name': entry.user_name or 'Unknown User',
                    'total_minutes': 0,
                    'total_hours': 0.0,
                    'total_revenue': 0.0,
                    'entries_count': 0,
                    'billable_hours': 0.0,
                    'non_billable_hours': 0.0,
                    'projects': set()
                }
            
            user_data[user_key]['total_minutes'] += entry.minutes
            user_data[user_key]['total_hours'] += entry.hours
            user_data[user_key]['total_revenue'] += entry.revenue or 0
            user_data[user_key]['entries_count'] += 1
            
            if entry.billable:
                user_data[user_key]['billable_hours'] += entry.hours
            else:
                user_data[user_key]['non_billable_hours'] += entry.hours
            
            if entry.project_name:
                user_data[user_key]['projects'].add(entry.project_name)
        
        # Convert to list and clean up
        summary = []
        for user_key, data in user_data.items():
            data['projects'] = list(data['projects'])
            data['projects_count'] = len(data['projects'])
            data['total_hours'] = round(data['total_hours'], 2)
            data['billable_hours'] = round(data['billable_hours'], 2)
            data['non_billable_hours'] = round(data['non_billable_hours'], 2)
            data['total_revenue'] = round(data['total_revenue'], 2)
            summary.append(data)
        
        return sorted(summary, key=lambda x: x['total_hours'], reverse=True)
    
    def generate_customer_summary(self, time_entries: List[TimeEntry]) -> List[Dict[str, Any]]:
        customer_data = {}
        
        for entry in time_entries:
            customer_key = f"{entry.customer_id}_{entry.customer_name or 'Unknown'}"
            
            if customer_key not in customer_data:
                customer_data[customer_key] = {
                    'customer_id': entry.customer_id,
                    'customer_name': entry.customer_name or 'Unknown Customer',
                    'total_minutes': 0,
                    'total_hours': 0.0,
                    'total_revenue': 0.0,
                    'entries_count': 0,
                    'projects': set(),
                    'users': set()
                }
            
            customer_data[customer_key]['total_minutes'] += entry.minutes
            customer_data[customer_key]['total_hours'] += entry.hours
            customer_data[customer_key]['total_revenue'] += entry.revenue or 0
            customer_data[customer_key]['entries_count'] += 1
            
            if entry.project_name:
                customer_data[customer_key]['projects'].add(entry.project_name)
            if entry.user_name:
                customer_data[customer_key]['users'].add(entry.user_name)
        
        # Convert to list and clean up
        summary = []
        for customer_key, data in customer_data.items():
            data['projects'] = list(data['projects'])
            data['users'] = list(data['users'])
            data['projects_count'] = len(data['projects'])
            data['users_count'] = len(data['users'])
            data['total_hours'] = round(data['total_hours'], 2)
            data['total_revenue'] = round(data['total_revenue'], 2)
            summary.append(data)
        
        return sorted(summary, key=lambda x: x['total_hours'], reverse=True)
    
    def create_dataframe(self, time_entries: List[TimeEntry]) -> pd.DataFrame:
        data = []
        for entry in time_entries:
            data.append({
                'id': entry.id,
                'date': entry.date_at,
                'hours': entry.hours,
                'minutes': entry.minutes,
                'note': entry.note,
                'billable': entry.billable,
                'locked': entry.locked,
                'revenue': entry.revenue,
                'hourly_rate': entry.hourly_rate,
                'user_id': entry.user_id,
                'user_name': entry.user_name,
                'customer_id': entry.customer_id,
                'customer_name': entry.customer_name,
                'project_id': entry.project_id,
                'project_name': entry.project_name,
                'service_id': entry.service_id,
                'service_name': entry.service_name,
                'created_at': entry.created_at,
                'updated_at': entry.updated_at
            })
        return pd.DataFrame(data)
    
    def export_to_csv(self, data: List[Dict[str, Any]], filename: str, directory: str = "exports") -> str:
        Path(directory).mkdir(exist_ok=True)
        filepath = Path(directory) / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            if data:
                writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        
        return str(filepath)
    
    def export_to_json(self, data: List[Dict[str, Any]], filename: str, directory: str = "exports") -> str:
        Path(directory).mkdir(exist_ok=True)
        filepath = Path(directory) / filename
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def export_to_excel(self, data: Dict[str, List[Dict[str, Any]]], filename: str, directory: str = "exports") -> str:
        Path(directory).mkdir(exist_ok=True)
        filepath = Path(directory) / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            for sheet_name, sheet_data in data.items():
                if sheet_data:
                    df = pd.DataFrame(sheet_data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return str(filepath)
    
    def generate_complete_monthly_report(self, year: Optional[int] = None, month: Optional[int] = None,
                                       export_format: str = "json", export_directory: str = "exports") -> Dict[str, Any]:
        # Get data
        if year and month:
            period_str = f"{year}-{month:02d}"
            first_day, last_day = get_month_range(year, month)
        else:
            first_day, last_day = get_last_month()
            period_str = f"{first_day.year}-{first_day.month:02d}"
        
        time_entries = self.get_monthly_data(year, month)
        
        # Generate summaries
        project_summary = self.generate_project_summary(time_entries)
        user_summary = self.generate_user_summary(time_entries)
        customer_summary = self.generate_customer_summary(time_entries)
        
        # Calculate totals
        total_hours = sum(entry.hours for entry in time_entries)
        total_revenue = sum(entry.revenue or 0 for entry in time_entries)
        billable_hours = sum(entry.hours for entry in time_entries if entry.billable)
        non_billable_hours = total_hours - billable_hours
        
        report = {
            'report_generated': datetime.now().isoformat(),
            'period': {
                'year': first_day.year,
                'month': first_day.month,
                'from_date': first_day.strftime('%Y-%m-%d'),
                'to_date': last_day.strftime('%Y-%m-%d')
            },
            'totals': {
                'total_hours': round(total_hours, 2),
                'billable_hours': round(billable_hours, 2),
                'non_billable_hours': round(non_billable_hours, 2),
                'total_revenue': round(total_revenue, 2),
                'entries_count': len(time_entries)
            },
            'project_summary': project_summary,
            'user_summary': user_summary,
            'customer_summary': customer_summary
        }
        
        # Export data
        if export_format.lower() == "json":
            export_path = self.export_to_json(
                report, 
                f"mite_monthly_report_{period_str}.json", 
                export_directory
            )
        elif export_format.lower() == "csv":
            # Export separate CSV files for each summary
            project_path = self.export_to_csv(
                project_summary, 
                f"mite_projects_{period_str}.csv", 
                export_directory
            )
            user_path = self.export_to_csv(
                user_summary, 
                f"mite_users_{period_str}.csv", 
                export_directory
            )
            customer_path = self.export_to_csv(
                customer_summary, 
                f"mite_customers_{period_str}.csv", 
                export_directory
            )
            export_path = f"Multiple files: {project_path}, {user_path}, {customer_path}"
        elif export_format.lower() == "excel":
            export_path = self.export_to_excel(
                {
                    'Projects': project_summary,
                    'Users': user_summary, 
                    'Customers': customer_summary,
                    'Summary': [report['totals']]
                },
                f"mite_monthly_report_{period_str}.xlsx",
                export_directory
            )
        
        report['export_path'] = export_path
        return report
    
    def format_for_billing_system(self, project_summary: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        billing_data = []
        
        for project in project_summary:
            billing_entry = {
                'external_project_id': project['project_id'],
                'project_name': project['project_name'],
                'customer_name': project['customer_name'],
                'hours': project['total_hours'],
                'amount': project['total_revenue'],
                'description': f"Consulting services for {project['project_name']} ({project['entries_count']} entries)"
            }
            billing_data.append(billing_entry)
        
        return billing_data