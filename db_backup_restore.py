"""
Script to create and restore PostgreSQL database backups.
This script creates SQL dumps that can be reloaded into a database.
"""
import os
import sys
import subprocess
import datetime
import argparse
from urllib.parse import urlparse

def parse_db_url():
    """Parse DATABASE_URL environment variable into components."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not found.")
        return None
    
    try:
        # Parse the URL
        parsed = urlparse(db_url)
        
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'user': parsed.username,
            'password': parsed.password,
            'dbname': parsed.path[1:] if parsed.path and parsed.path.startswith('/') else '',
            'sslmode': 'require' if 'sslmode=require' in db_url else None
        }
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {e}")
        return None

def backup_database(backup_dir='db_backups', schema_only=False):
    """
    Create a PostgreSQL database backup using pg_dump.
    
    Args:
        backup_dir (str): Directory to store backups
        schema_only (bool): If True, only dump schema without data
    
    Returns:
        str: Path to backup file or None if failed
    """
    # Create backup directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Get database connection details
    db_params = parse_db_url()
    if not db_params:
        return None
    
    # Generate backup filename with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_type = "schema" if schema_only else "full"
    backup_file = f"{backup_dir}/{backup_type}_backup_{timestamp}.sql"
    
    # Build pg_dump command
    cmd = [
        'pg_dump',
        f'--host={db_params["host"]}',
        f'--port={db_params["port"]}',
        f'--username={db_params["user"]}',
        f'--dbname={db_params["dbname"]}',
        '--no-owner',  # Don't include ownership commands
        '--no-acl',    # Don't include privilege commands
    ]
    
    # Add schema-only flag if requested
    if schema_only:
        cmd.append('--schema-only')
    
    # Add sslmode if required
    if db_params.get('sslmode') == 'require':
        cmd.append('--sslmode=require')
    
    # Add output file
    cmd.extend(['-f', backup_file])
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    if db_params.get('password'):
        env['PGPASSWORD'] = db_params['password']
    
    try:
        print(f"Creating {'schema-only' if schema_only else 'full'} database backup...")
        subprocess.run(cmd, env=env, check=True)
        print(f"Backup created successfully: {backup_file}")
        
        # Create a symbolic link to latest backup
        latest_link = f"{backup_dir}/latest_{backup_type}_backup.sql"
        if os.path.exists(latest_link):
            os.remove(latest_link)
        try:
            # On systems that support symbolic links
            os.symlink(os.path.basename(backup_file), latest_link)
        except:
            # Fall back to copying the file if symlinks aren't supported
            import shutil
            shutil.copy2(backup_file, latest_link)
            
        print(f"Latest backup link created: {latest_link}")
        return backup_file
    except subprocess.CalledProcessError as e:
        print(f"Error creating backup: {e}")
        return None

def restore_database(backup_file=None):
    """
    Restore a PostgreSQL database from a backup file.
    
    Args:
        backup_file (str): Path to backup file to restore.
                          If None, uses latest full backup.
    
    Returns:
        bool: True if successful, False otherwise
    """
    # If no backup file specified, find the latest full backup
    if not backup_file:
        backup_dir = 'db_backups'
        latest_link = f"{backup_dir}/latest_full_backup.sql"
        
        if os.path.exists(latest_link):
            backup_file = latest_link
        else:
            # Find the most recent backup
            if os.path.exists(backup_dir):
                backups = [f for f in os.listdir(backup_dir) if f.startswith('full_backup_') and f.endswith('.sql')]
                if backups:
                    backups.sort(reverse=True)  # Sort to get most recent
                    backup_file = f"{backup_dir}/{backups[0]}"
            
            if not backup_file:
                print("Error: No backup file specified and no latest backup found.")
                return False
    
    if not os.path.exists(backup_file):
        print(f"Error: Backup file not found: {backup_file}")
        return False
    
    # Get database connection details
    db_params = parse_db_url()
    if not db_params:
        return False
    
    # Build psql command
    cmd = [
        'psql',
        f'--host={db_params["host"]}',
        f'--port={db_params["port"]}',
        f'--username={db_params["user"]}',
        f'--dbname={db_params["dbname"]}',
    ]
    
    # Add sslmode if required
    if db_params.get('sslmode') == 'require':
        cmd.append('--sslmode=require')
    
    # Input from file
    cmd.extend(['-f', backup_file])
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    if db_params.get('password'):
        env['PGPASSWORD'] = db_params['password']
    
    try:
        print(f"Restoring database from {backup_file}...")
        subprocess.run(cmd, env=env, check=True)
        print("Database restored successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error restoring database: {e}")
        return False

def main():
    """Main function to parse arguments and perform backup/restore."""
    parser = argparse.ArgumentParser(description="PostgreSQL Database Backup and Restore Tool")
    
    # Create subparsers for backup and restore commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create a database backup')
    backup_parser.add_argument('--schema-only', action='store_true', help='Backup schema only (no data)')
    backup_parser.add_argument('--dir', default='db_backups', help='Directory to store backups')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore a database backup')
    restore_parser.add_argument('--file', help='Path to backup file to restore')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'backup':
        backup_database(backup_dir=args.dir, schema_only=args.schema_only)
    elif args.command == 'restore':
        restore_database(backup_file=args.file)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()