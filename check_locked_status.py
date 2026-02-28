#!/usr/bin/env python3
"""
Quick script to check if time entries are locked
"""
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os
import re

load_dotenv()

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Substitute env vars
def substitute_env_vars(value):
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.getenv(var_name)
            if env_value:
                value = value.replace(f'${{{var_name}}}', env_value)
        return value
    elif isinstance(value, dict):
        return {k: substitute_env_vars(v) for k, v in value.items()}
    return value

config = substitute_env_vars(config)

# Import mite client
from mite_client import MiteClient

client = MiteClient(
    account=config['mite']['account'],
    api_key=config['mite']['api_key']
)

entries = client.time_entries.get_date_range(
    from_date='2026-01-01',
    to_date='2026-01-31',
    project_id=4516575,
    billable=True
)

print(f'\nFound {len(entries)} time entries for project 4516575 in January 2026:\n')
for entry in entries:
    locked_status = "🔒 LOCKED" if entry.locked else "🔓 unlocked"
    print(f'  Entry {entry.id}: {locked_status} | {entry.date_at} | {entry.minutes/60:.2f}h | {entry.user_name}')

locked_count = sum(1 for e in entries if e.locked)
unlocked_count = len(entries) - locked_count
print(f'\nSummary: {locked_count} locked, {unlocked_count} unlocked')
