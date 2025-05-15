#!/bin/bash

# Script to export database schema as SQL
echo "Exporting database schema as SQL..."
python sql_schema_export.py

echo ""
echo "Schema exported to db_backups/ directory."
echo "You can find the latest schema in db_backups/latest_schema.sql"
echo ""
echo "To recreate the schema in another database, run:"
echo "psql -h <host> -U <user> -d <database> -f db_backups/latest_schema.sql"
echo ""