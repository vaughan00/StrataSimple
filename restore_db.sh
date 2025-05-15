#!/bin/bash

# Script to restore database schema and data
echo "Starting database restore..."

# Check if a specific backup is specified
if [ "$1" != "" ]; then
    SCHEMA_FILE="$1"
    DATA_FILE="$2"
    
    if [ "$DATA_FILE" == "" ]; then
        echo "Error: When specifying a schema file, you must also specify a data file."
        echo "Usage: ./restore_db.sh <schema_file> <data_file>"
        exit 1
    fi
    
    if [ ! -f "$SCHEMA_FILE" ]; then
        echo "Error: Schema file $SCHEMA_FILE not found."
        exit 1
    fi
    
    if [ ! -f "$DATA_FILE" ]; then
        echo "Error: Data file $DATA_FILE not found."
        exit 1
    fi
else
    # Use latest backups
    SCHEMA_FILE="db_backups/latest_schema.sql"
    DATA_FILE="db_backups/latest_data_backup.sql"
    
    if [ ! -f "$SCHEMA_FILE" ]; then
        echo "Error: Latest schema backup $SCHEMA_FILE not found."
        exit 1
    fi
    
    if [ ! -f "$DATA_FILE" ]; then
        echo "Error: Latest data backup $DATA_FILE not found."
        exit 1
    fi
fi

# Restore schema
echo "Restoring database schema from $SCHEMA_FILE..."
echo "This will DROP ALL TABLES and recreate them."
read -p "Are you sure you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Database restore cancelled."
    exit 1
fi

# Parse DATABASE_URL to get connection details
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable not set."
    exit 1
fi

# Restore schema (dropping and recreating all tables)
echo "Executing schema restore..."
cat "$SCHEMA_FILE" | python -c "
import os, sys
from sqlalchemy import create_engine, text

try:
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.begin() as conn:
        sql = sys.stdin.read()
        conn.execute(text(sql))
    print('Schema restored successfully.')
except Exception as e:
    print(f'Error restoring schema: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Error: Failed to restore schema."
    exit 1
fi

# Restore data
echo "Restoring database data from $DATA_FILE..."
python restore_db_data.py --file "$DATA_FILE"

if [ $? -ne 0 ]; then
    echo "Error: Failed to restore data."
    exit 1
fi

echo ""
echo "Database restore complete."
echo ""