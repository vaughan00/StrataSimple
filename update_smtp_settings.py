"""
Script to update SMTP settings in environment variables.
Run this script with the --password flag to update your SMTP password.

Usage:
  python update_smtp_settings.py --password YOUR_NEW_PASSWORD

For a complete update with all settings:
  python update_smtp_settings.py --server smtp.example.com --port 587 --username user@example.com --password yourpassword --sender sender@example.com
"""

import os
import sys
import argparse

def update_smtp_settings():
    """
    Update SMTP settings in environment variables.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Update SMTP settings')
    parser.add_argument('--server', help='SMTP server address')
    parser.add_argument('--port', help='SMTP port')
    parser.add_argument('--username', help='SMTP username (email)')
    parser.add_argument('--password', help='SMTP password (App Password for Gmail)')
    parser.add_argument('--sender', help='Email sender address')
    
    args = parser.parse_args()
    
    print("Update SMTP Settings")
    print("====================")
    
    # Current values
    current_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    current_port = os.environ.get('SMTP_PORT', '587')
    current_username = os.environ.get('SMTP_USERNAME', '')
    current_sender = os.environ.get('EMAIL_SENDER', current_username)
    
    # New values (use current values if not provided)
    new_server = args.server or current_server
    new_port = args.port or current_port
    new_username = args.username or current_username
    new_password = args.password
    new_sender = args.sender or current_sender
    
    print("\nCurrent Settings:")
    print(f"SMTP_SERVER: {current_server}")
    print(f"SMTP_PORT: {current_port}")
    print(f"SMTP_USERNAME: {current_username}")
    print(f"EMAIL_SENDER: {current_sender}")
    print("SMTP_PASSWORD: *********")
    
    print("\nNew Settings:")
    print(f"SMTP_SERVER: {new_server}")
    print(f"SMTP_PORT: {new_port}")
    print(f"SMTP_USERNAME: {new_username}")
    print(f"EMAIL_SENDER: {new_sender}")
    print(f"SMTP_PASSWORD: {'(changed)' if new_password else '(unchanged)'}")
    
    # Check if any changes were made
    if (new_server != current_server or 
        new_port != current_port or 
        new_username != current_username or 
        new_sender != current_sender or 
        new_password):
        print("\nUpdating SMTP settings...")
        
        # Create or update the .env file
        try:
            # First read existing content
            env_content = {}
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            env_content[key] = value
            
            # Update with new values
            env_content['SMTP_SERVER'] = new_server
            env_content['SMTP_PORT'] = new_port
            env_content['SMTP_USERNAME'] = new_username
            if new_password:
                env_content['SMTP_PASSWORD'] = new_password
            env_content['EMAIL_SENDER'] = new_sender
            
            # Write back to .env file
            with open('.env', 'w') as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            # Update current process environment
            os.environ['SMTP_SERVER'] = new_server
            os.environ['SMTP_PORT'] = new_port
            os.environ['SMTP_USERNAME'] = new_username
            if new_password:
                os.environ['SMTP_PASSWORD'] = new_password
            os.environ['EMAIL_SENDER'] = new_sender
            
            print("\nSMTP settings updated successfully!")
            print("Note: For the changes to take effect, restart the application.")
        except Exception as e:
            print(f"\nError updating settings: {e}")
    else:
        print("\nNo changes made to settings.")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(__doc__)
    else:
        update_smtp_settings()