#!/usr/bin/env python3
"""
Script to backup all data from the PostgreSQL database.
This creates a SQL file with INSERT statements for all data.
"""
import os
import sys
import datetime
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

def backup_data():
    """Backup all data from the database to a SQL file."""
    # Get database connection from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create the backup directory if it doesn't exist
    backup_dir = 'db_backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    # Filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{backup_dir}/data_backup_{timestamp}.sql"
    latest_backup = f"{backup_dir}/latest_data_backup.sql"
    
    # Connect to database
    engine = create_engine(database_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    # Open the file for writing
    with open(backup_filename, 'w') as f:
        f.write(f"-- Database Data Backup generated on {datetime.datetime.now()}\n")
        f.write("-- This file contains INSERT statements for all data\n\n")
        
        f.write("-- Disable triggers during import\n")
        f.write("SET session_replication_role = 'replica';\n\n")
        
        # For each table
        inspector = inspect(engine)
        for table_name in inspector.get_table_names():
            if table_name == 'alembic_version':
                continue  # Skip migration tracking tables
                
            table = Table(table_name, metadata, autoload_with=engine)
            
            # Get the number of rows
            with engine.connect() as conn:
                count = conn.execute(table.count()).scalar()
            
            if count == 0:
                continue  # Skip empty tables
                
            print(f"Backing up {count} rows from {table_name}")
            f.write(f"-- Table: {table_name}\n")
            f.write(f"-- {count} rows\n")
            
            # Get all rows
            with engine.connect() as conn:
                rows = conn.execute(table.select()).fetchall()
                
                for row in rows:
                    # Create column list
                    columns = [column.name for column in table.columns]
                    column_list = ", ".join(columns)
                    
                    # Create value list with proper SQL escaping
                    values = []
                    for i, column in enumerate(table.columns):
                        value = row[i]
                        if value is None:
                            values.append("NULL")
                        elif isinstance(value, (int, float)):
                            values.append(str(value))
                        elif isinstance(value, datetime.datetime):
                            values.append(f"'{value.isoformat()}'")
                        elif isinstance(value, bool):
                            values.append("TRUE" if value else "FALSE")
                        else:
                            # Escape single quotes in string values
                            escaped_value = str(value).replace("'", "''")
                            values.append(f"'{escaped_value}'")
                    
                    value_list = ", ".join(values)
                    
                    # Write INSERT statement
                    f.write(f"INSERT INTO {table_name} ({column_list}) VALUES ({value_list});\n")
            
            f.write("\n")
            
        f.write("-- Re-enable triggers\n")
        f.write("SET session_replication_role = 'origin';\n")
    
    # Create a copy as latest_data_backup.sql
    with open(backup_filename, 'r') as src:
        with open(latest_backup, 'w') as dst:
            dst.write(src.read())
    
    print(f"Database data backed up to {backup_filename}")
    print(f"Latest backup also available at {latest_backup}")
    return backup_filename

if __name__ == "__main__":
    backup_data()