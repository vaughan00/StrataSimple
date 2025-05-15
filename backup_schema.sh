#!/bin/bash

# Script to create a schema-only database backup (no data)
echo "Creating schema-only database backup..."
python db_backup_restore.py backup --schema-only

echo ""
echo "Schema backup created in the db_backups/ directory."
echo ""