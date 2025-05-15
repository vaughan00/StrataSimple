#!/bin/bash

# Script to restore database from the latest backup or specified file
if [ -z "$1" ]; then
    echo "Restoring database from latest backup..."
    python db_backup_restore.py restore
else
    echo "Restoring database from $1..."
    python db_backup_restore.py restore --file "$1"
fi

echo ""
echo "Restore process completed."
echo ""