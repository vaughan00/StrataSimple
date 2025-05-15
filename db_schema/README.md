# Database Schema Documentation

This directory contains database schema information for tracking changes over time.

## Files

- `latest_table_schema.csv`: Current table schema information
- `latest_foreign_keys.csv`: Current foreign key relationships
- `table_schema_*.csv`: Historical table schema snapshots with timestamps
- `foreign_keys_*.csv`: Historical foreign key relationship snapshots with timestamps

## Schema Updates

When making schema changes, run `python db_schema_export.py` to update these files.
