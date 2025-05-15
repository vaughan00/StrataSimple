#!/bin/bash

# Script to backup database schema and data
echo "Starting database backup..."

# Export schema first
echo "Exporting database schema..."
python sql_schema_export.py

# Export data
echo "Exporting database data..."
python backup_db_data.py

echo ""
echo "Database backup complete."
echo "Schema: db_backups/latest_schema.sql"
echo "Data: db_backups/latest_data_backup.sql"
echo ""