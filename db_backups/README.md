# Database Backup and Schema Tools

This directory contains database backups and schema exports for StrataHub.

## Files

- `latest_schema.sql`: Current database schema as SQL (can be used to recreate tables)
- `schema_*.sql`: Historical schema snapshots with timestamps
- `latest_data_backup.sql`: Current database data as SQL INSERT statements
- `data_backup_*.sql`: Historical data backups with timestamps

## How to Use

### Backing Up the Database

To back up both the schema and data:

```bash
./backup_db.sh
```

This will:
1. Create a new schema file with timestamp in this directory
2. Update the `latest_schema.sql` file
3. Create a new data backup file with timestamp
4. Update the `latest_data_backup.sql` file

### Restoring the Database

To restore both the schema and data from the latest backups:

```bash
./restore_db.sh
```

To restore from specific backup files:

```bash
./restore_db.sh db_backups/schema_20250515_010033.sql db_backups/data_backup_20250515_010033.sql
```

**Warning:** This will DROP ALL TABLES and recreate them, then insert the backed-up data.

### Exporting Just the Schema

To export just the current database schema as SQL:

```bash
./export_schema.sh
```

## Schema Changes

When making database schema changes:

1. Update your SQLAlchemy models in `models.py`
2. Run `./backup_db.sh` to generate a new schema and data backup
3. Commit both the code changes and the schema files to track the evolution of your database structure

## Documentation

For a more detailed view of the database structure, see the CSV files in the `db_schema/` directory, which contain information about tables, columns, and relationships.