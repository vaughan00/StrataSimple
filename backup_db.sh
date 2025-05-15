#!/bin/bash

# Script to create a full database backup (schema + data)
echo "Creating full database backup..."
python db_backup_restore.py backup

echo ""
echo "Backup created in the db_backups/ directory."
echo ""