"""
migrate.py - Run SQL migrations on Railway PostgreSQL
=====================================================
Usage:
    python migrate.py migrations/your_migration.sql

This script will run the specified SQL file against
the Railway (or local) PostgreSQL database.
"""

import sys
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def run_migration(sql_file: str):
    if not os.path.exists(sql_file):
        print(f"ERROR: File not found: {sql_file}")
        sys.exit(1)

    # Build connection from environment variables (same as app)
    host     = os.getenv("DB_HOST", "127.0.0.1")
    port     = int(os.getenv("DB_PORT", "5432"))
    dbname   = os.getenv("DB_NAME", "liceo_db")
    user     = os.getenv("DB_USER", "liceo_db")
    password = os.getenv("DB_PASSWORD", "liceo123")

    print(f"Connecting to: {host}:{port}/{dbname}")

    try:
        conn = psycopg2.connect(
            host=host, port=port,
            dbname=dbname, user=user, password=password
        )
        conn.autocommit = False

        with open(sql_file, encoding="utf-8") as f:
            sql = f.read()

        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Migration SUCCESS: {sql_file}")

    except Exception as e:
        print(f"❌ Migration FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate.py <sql_file>")
        print("Example: python migrate.py migrations/add_column.sql")
        sys.exit(1)

    run_migration(sys.argv[1])
