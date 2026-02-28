#!/usr/bin/env python3
"""
Check details for a specific project
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

# Project ID
project_id = 4516575  # TESTPROJEKT

# Create client
try:
    client = MiteClient(account=mite_account, api_key=mite_api_key)

    # Get project details
    print(f"\n{'='*80}")
    print(f"Project Details")
    print(f"{'='*80}\n")

    project = client.projects.get(project_id)
    print(f"Project ID: {project.id}")
    print(f"Name: {project.name}")
    print(f"Customer: {project.customer_name or 'N/A'}")
    print(f"Hourly Rate: {project.hourly_rate / 100.0 if project.hourly_rate else 'N/A'} EUR")
    print(f"Budget: {project.budget or 'N/A'}")
    print(f"Active: {not project.archived}")
    print(f"Created: {project.created_at}")
    print(f"Updated: {project.updated_at}")

    # Check for time entries in different date ranges
    print(f"\n{'='*80}")
    print(f"Time Entries Search")
    print(f"{'='*80}\n")

    # Last 7 days
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    entries = client.time_entries.get_date_range(
        from_date=start_date,
        to_date=end_date,
        project_id=project_id
    )
    print(f"Last 7 days ({start_date} to {end_date}): {len(entries)} entries")

    # Last 30 days
    start_date = end_date - timedelta(days=30)
    entries = client.time_entries.get_date_range(
        from_date=start_date,
        to_date=end_date,
        project_id=project_id
    )
    print(f"Last 30 days ({start_date} to {end_date}): {len(entries)} entries")

    # All time (last 365 days)
    start_date = end_date - timedelta(days=365)
    entries = client.time_entries.get_date_range(
        from_date=start_date,
        to_date=end_date,
        project_id=project_id
    )
    print(f"Last 365 days ({start_date} to {end_date}): {len(entries)} entries")

    if entries:
        print(f"\n{'='*80}")
        print(f"Found Time Entries")
        print(f"{'='*80}\n")

        for entry in entries[:10]:  # Show first 10
            billable = "✓ billable" if entry.billable else "✗ non-billable"
            print(f"{entry.date_at} | {entry.user_name or 'N/A'} | {entry.minutes / 60:.2f}h | {billable}")
            if entry.note:
                print(f"  Note: {entry.note[:60]}...")
            print()

        if len(entries) > 10:
            print(f"... and {len(entries) - 10} more entries\n")

    print(f"{'='*80}\n")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
