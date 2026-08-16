"""One-time helper: wipe Postgres public schema when RESET_DB=1."""

import os
import sys
from pathlib import Path

if os.environ.get("RESET_DB") != "1":
    print("RESET_DB is not 1; skipping schema reset.")
    sys.exit(0)

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DROP SCHEMA public CASCADE")
    cursor.execute("CREATE SCHEMA public")

print("Reset Postgres public schema.")
