# Database Backup and Schema Tools

This directory contains database backups and schema exports for StrataHub.

## Files

- `latest_schema.sql`: Current database schema as SQL (can be used to recreate tables)
- `schema_*.sql`: Historical schema snapshots with timestamps

## How to Use

### Exporting the Schema

To export the current database schema as SQL:

```bash
./export_schema.sh
```

This will create a new SQL file in this directory with the current schema and also update the `latest_schema.sql` file.

### Recreating the Database Schema

To recreate the database schema in another PostgreSQL database:

```bash
psql -h <host> -U <user> -d <database> -f db_backups/latest_schema.sql
```

Or you can copy the SQL statements and run them in any SQL client.

## Schema Changes

When making database schema changes:

1. Update your SQLAlchemy models in `models.py`
2. Run `./export_schema.sh` to generate a new schema file
3. Commit both the code changes and the schema file to track the evolution of your database structure

## Documentation

For a more detailed view of the database structure, see the CSV files in the `db_schema/` directory, which contain information about tables, columns, and relationships.