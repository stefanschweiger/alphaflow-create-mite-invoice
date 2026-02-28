#!/usr/bin/env python3
"""
Find projects with recent time entries
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from dotenv import load_dotenv
import yaml

from mite_client import MiteClient

# Load environment
load_dotenv()

# Load config
config_path = Path("config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

mite_account = config['mite']['account']
mite_api_key = config['mite']['api_key']

if mite_api_key.startswith('${') and mite_api_key.endswith('}'):
    import os
    var_name = mite_api_key[2:-1]
    mite_api_key = os.getenv(var_name)

# Create client
try:
    client = MiteClient(account=mite_account, api_key=mite_api_key)

    # Get time entries from last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    print(f"\nSearching for time entries from {start_date} to {end_date}...\n")

    entries = client.time_entries.get_date_range(
        from_date=start_date,
        to_date=end_date,
        billable=True
    )

    # Group by project
    projects_with_entries = {}
    for entry in entries:
        if entry.project_id:
            if entry.project_id not in projects_with_entries:
                projects_with_entries[entry.project_id] = {
                    'project_name': entry.project_name,
                    'customer_name': entry.customer_name,
                    'count': 0,
                    'hours': 0.0
                }
            projects_with_entries[entry.project_id]['count'] += 1
            projects_with_entries[entry.project_id]['hours'] += entry.minutes / 60.0

    if not projects_with_entries:
        print("No billable time entries found in the last 30 days.")
        sys.exit(0)

    # Sort by entry count
    sorted_projects = sorted(
        projects_with_entries.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )

    print(f"{'='*100}")
    print(f"Projects with billable time entries in last 30 days (Top 10)")
    print(f"{'='*100}\n")

    for project_id, data in sorted_projects[:10]:
        print(f"Project ID: {project_id}")
        print(f"  Name: {data['project_name']}")
        if data['customer_name']:
            print(f"  Customer: {data['customer_name']}")
        print(f"  Entries: {data['count']}")
        print(f"  Hours: {data['hours']:.2f}h")
        print()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
