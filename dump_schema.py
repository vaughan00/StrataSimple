"""
Script to dump the current database schema to a SQL file that can be tracked in Git.
This helps maintain documentation of the schema and track changes over time.
"""
import os
import subprocess
import datetime
from app import app

def dump_schema():
    """Dump the current database schema to a SQL file."""
    # Get database connection details from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not found.")
        return False
    
    # Parse connection details from DATABASE_URL
    # Format: postgresql://username:password@host:port/database?params
    try:
        from urllib.parse import urlparse, parse_qs
        
        # Parse the URL
        parsed_url = urlparse(db_url)
        
        # Extract username and password
        username = parsed_url.username
        password = parsed_url.password
        
        # Extract host and port
        host = parsed_url.hostname
        port = parsed_url.port or '5432'  # Default PostgreSQL port
        
        # Extract database name (remove query parameters)
        database = ''
        path = parsed_url.path
        if path.startswith('/'):
            database = path[1:]  # Remove leading slash
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}")
        return False
    
    # Create directory for schema dumps if it doesn't exist
    schema_dir = 'db_schema'
    if not os.path.exists(schema_dir):
        os.makedirs(schema_dir)
    
    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    schema_file = f"{schema_dir}/schema_{timestamp}.sql"
    
    # Use pg_dump to dump schema (no data)
    cmd = [
        'pg_dump',
        f'--host={host}',
        f'--port={port}',
        f'--username={username}',
        f'--dbname={database}',
        '--schema-only',  # Only dump schema, not data
        '--no-owner',     # Don't include ownership commands
        '--no-privileges',  # Skip privileges (GRANT/REVOKE)
        '-f', schema_file
    ]
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    if password:
        env['PGPASSWORD'] = password
    
    try:
        print(f"Dumping schema to {schema_file}...")
        subprocess.run(cmd, env=env, check=True)
        print(f"Schema successfully dumped to {schema_file}")
        
        # Also create a copy as latest.sql for easy reference
        latest_file = f"{schema_dir}/latest.sql"
        try:
            with open(schema_file, 'r') as src, open(latest_file, 'w') as dst:
                dst.write(src.read())
            print(f"Latest schema copy created at {latest_file}")
        except Exception as e:
            print(f"Error creating latest schema copy: {e}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error dumping schema: {e}")
        return False

if __name__ == "__main__":
    with app.app_context():
        dump_schema()