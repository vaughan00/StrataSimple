#!/bin/bash

# Script to update database schema documentation
# Run this after making any database schema changes

echo "Updating database schema documentation..."
python db_schema_export.py

echo "Checking for changes to commit..."
git status db_schema/

echo ""
echo "Next steps:"
echo "1. Review the changes in the db_schema/ directory"
echo "2. Commit the changes with: git add db_schema/ && git commit -m 'Update database schema documentation'"
echo ""
echo "Done!"