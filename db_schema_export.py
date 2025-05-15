"""
Script to export database schema information to files for Git tracking.
This script directly queries the database metadata tables to generate a complete schema.
"""
import os
import datetime
import csv
from app import app, db
from sqlalchemy import text

def export_schema():
    """Export the database schema to files for Git tracking."""
    with app.app_context():
        # Create schema directory if it doesn't exist
        schema_dir = 'db_schema'
        if not os.path.exists(schema_dir):
            os.makedirs(schema_dir)
            
        # Generate timestamp for filenames
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export table and column information
        table_schema_file = f"{schema_dir}/table_schema_{timestamp}.csv"
        latest_table_schema = f"{schema_dir}/latest_table_schema.csv"
        
        # Query to get table and column information
        table_query = """
        SELECT 
            table_name,
            column_name, 
            data_type, 
            character_maximum_length,
            column_default,
            is_nullable,
            CASE 
                WHEN column_name IN (
                    SELECT kcu.column_name 
                    FROM information_schema.table_constraints tc 
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name 
                    WHERE tc.constraint_type = 'PRIMARY KEY' 
                        AND tc.table_name = c.table_name
                ) THEN 'PRIMARY KEY'
                ELSE ''
            END AS primary_key_status,
            CASE 
                WHEN column_name IN (
                    SELECT kcu.column_name 
                    FROM information_schema.table_constraints tc 
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name 
                    WHERE tc.constraint_type = 'FOREIGN KEY' 
                        AND tc.table_name = c.table_name
                ) THEN 'FOREIGN KEY'
                ELSE ''
            END AS foreign_key_status
        FROM 
            information_schema.columns c
        WHERE 
            table_schema = 'public'
        ORDER BY 
            table_name, ordinal_position
        """
        
        # Query to get foreign key relationships
        fk_query = """
        SELECT
            tc.table_schema, 
            tc.constraint_name, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name, kcu.column_name
        """
        
        try:
            # Execute the table schema query
            result = db.session.execute(text(table_query))
            
            # Write to the timestamped file
            with open(table_schema_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['table_name', 'column_name', 'data_type', 'max_length', 
                                'default_value', 'nullable', 'primary_key', 'foreign_key'])
                for row in result:
                    writer.writerow(row)
            
            # Write to the latest file
            with open(latest_table_schema, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['table_name', 'column_name', 'data_type', 'max_length', 
                                'default_value', 'nullable', 'primary_key', 'foreign_key'])
                
                # Re-execute query since the result was consumed
                result = db.session.execute(text(table_query))
                for row in result:
                    writer.writerow(row)
                    
            print(f"Table schema exported to {table_schema_file} and {latest_table_schema}")
            
            # Export foreign key relationships
            fk_file = f"{schema_dir}/foreign_keys_{timestamp}.csv"
            latest_fk_file = f"{schema_dir}/latest_foreign_keys.csv"
            
            # Execute the foreign key query
            result = db.session.execute(text(fk_query))
            
            # Write to the timestamped file
            with open(fk_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['schema', 'constraint_name', 'table_name', 'column_name', 
                                'foreign_schema', 'foreign_table', 'foreign_column'])
                for row in result:
                    writer.writerow(row)
            
            # Write to the latest file
            with open(latest_fk_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['schema', 'constraint_name', 'table_name', 'column_name', 
                                'foreign_schema', 'foreign_table', 'foreign_column'])
                
                # Re-execute query since the result was consumed
                result = db.session.execute(text(fk_query))
                for row in result:
                    writer.writerow(row)
                    
            print(f"Foreign key relationships exported to {fk_file} and {latest_fk_file}")
            
            # Create a README file if it doesn't exist
            readme_file = f"{schema_dir}/README.md"
            if not os.path.exists(readme_file):
                with open(readme_file, 'w') as f:
                    f.write("# Database Schema Documentation\n\n")
                    f.write("This directory contains database schema information for tracking changes over time.\n\n")
                    f.write("## Files\n\n")
                    f.write("- `latest_table_schema.csv`: Current table schema information\n")
                    f.write("- `latest_foreign_keys.csv`: Current foreign key relationships\n")
                    f.write("- `table_schema_*.csv`: Historical table schema snapshots with timestamps\n")
                    f.write("- `foreign_keys_*.csv`: Historical foreign key relationship snapshots with timestamps\n\n")
                    f.write("## Schema Updates\n\n")
                    f.write("When making schema changes, run `python db_schema_export.py` to update these files.\n")
                    
            print(f"Schema export completed. Files saved to {schema_dir}/ directory")
            return True
            
        except Exception as e:
            print(f"Error exporting schema: {e}")
            return False

if __name__ == "__main__":
    export_schema()