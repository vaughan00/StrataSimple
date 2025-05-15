#!/usr/bin/env python3
"""
Script to restore database data from a SQL backup file.
This script assumes the database schema already exists.
"""
import os
import sys
import datetime
import argparse
from sqlalchemy import create_engine, text

def restore_data(backup_file=None):
    """
    Restore database data from a SQL backup file.
    
    Args:
        backup_file: Path to the backup file to restore from.
                    If None, uses latest data backup.
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Get database connection from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Determine which backup file to use
    backup_dir = 'db_backups'
    if not backup_file:
        backup_file = f"{backup_dir}/latest_data_backup.sql"
        if not os.path.exists(backup_file):
            print(f"Error: Latest backup file {backup_file} not found")
            return False
    
    if not os.path.exists(backup_file):
        print(f"Error: Backup file {backup_file} not found")
        return False
    
    print(f"Restoring data from {backup_file}")
    
    # Connect to database
    engine = create_engine(database_url)
    
    # Read the SQL file
    with open(backup_file, 'r') as f:
        sql_script = f.read()
    
    # Execute the SQL script
    try:
        with engine.begin() as conn:
            # Execute each statement separately
            for statement in sql_script.split(';'):
                if statement.strip() and not statement.strip().startswith('--'):
                    conn.execute(text(statement))
        
        print(f"Database data restored successfully from {backup_file}")
        return True
    
    except Exception as e:
        print(f"Error restoring database: {e}")
        return False

def main():
    """Parse arguments and restore data."""
    parser = argparse.ArgumentParser(description='Restore database data from a backup.')
    parser.add_argument('--file', help='Path to the backup file to restore from')
    args = parser.parse_args()
    
    restore_data(args.file)

if __name__ == "__main__":
    main()