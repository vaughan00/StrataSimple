"""
Script to track database schema changes for Git.
This script:
1. Creates a SQL dump of the current schema
2. Prints a human-readable representation of the schema
"""
import os
import sys
import datetime
from dump_schema import dump_schema
from print_schema import print_schema

def track_schema():
    """Track database schema by dumping SQL and printing human-readable schema."""
    print("=== TRACKING DATABASE SCHEMA ===")
    
    # Create schema_docs directory if it doesn't exist
    schema_dir = 'db_schema'
    if not os.path.exists(schema_dir):
        os.makedirs(schema_dir)
    
    # Generate timestamp for filenames
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Step 1: Dump schema to SQL file
    print("\n--- STEP 1: Dumping schema to SQL file ---")
    success = dump_schema()
    if not success:
        print("WARNING: Failed to dump schema to SQL file. Continuing with schema documentation...")
    
    # Step 2: Print human-readable schema
    print("\n--- STEP 2: Generating human-readable schema ---")
    schema_doc_file = f"{schema_dir}/schema_doc_{timestamp}.txt"
    latest_doc_file = f"{schema_dir}/latest_schema_doc.txt"
    
    try:
        # Capture the schema output as a string
        import io
        from contextlib import redirect_stdout
        
        # Use redirect_stdout to safely capture output
        output = io.StringIO()
        with redirect_stdout(output):
            print_schema()
            
        schema_text = output.getvalue()
        
        # Write to the timestamp file
        with open(schema_doc_file, 'w') as f:
            f.write(schema_text)
            
        # Write to the latest file
        with open(latest_doc_file, 'w') as f:
            f.write(schema_text)
        
        print(f"Human-readable schema saved to {schema_doc_file} and {latest_doc_file}")
    except Exception as e:
        print(f"Error generating human-readable schema: {e}")
    
    print("\n=== DATABASE SCHEMA TRACKING COMPLETE ===")
    print(f"Schema artifacts saved to {schema_dir}/ directory")
    print("Add these files to Git to track schema changes.")

if __name__ == "__main__":
    track_schema()