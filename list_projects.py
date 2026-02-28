#!/usr/bin/env python3
"""
List all mite projects to find project IDs
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import yaml

# Import mite_client
from mite_client import MiteClient

# Load environment
load_dotenv()

# Load config
config_path = Path("config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Substitute env vars if needed
mite_account = config['mite']['account']
mite_api_key = config['mite']['api_key']

if mite_api_key.startswith('${') and mite_api_key.endswith('}'):
    import os
    var_name = mite_api_key[2:-1]
    mite_api_key = os.getenv(var_name)

# Create client
try:
    client = MiteClient(account=mite_account, api_key=mite_api_key)
    projects = client.projects.list()

    print(f"\n{'='*80}")
    print(f"Available mite projects ({len(projects)} total)")
    print(f"{'='*80}\n")

    # Sort by name
    projects_sorted = sorted(projects, key=lambda p: p.name.lower())

    for project in projects_sorted:
        archived = " [ARCHIVED]" if project.archived else ""
        customer = f" - {project.customer_name}" if project.customer_name else ""
        print(f"ID: {project.id:<8} | {project.name}{customer}{archived}")

    print(f"\n{'='*80}\n")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
