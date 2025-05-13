"""
Script to display current SMTP settings from environment variables.
"""

import os

def show_smtp_settings():
    """
    Display current SMTP settings from environment variables.
    """
    print("Current SMTP Settings")
    print("====================")
    
    smtp_server = os.environ.get('SMTP_SERVER', 'Not set')
    smtp_port = os.environ.get('SMTP_PORT', 'Not set')
    smtp_username = os.environ.get('SMTP_USERNAME', 'Not set')
    email_sender = os.environ.get('EMAIL_SENDER', 'Not set')
    
    # Check if password is set (don't display the actual password)
    smtp_password = "Set" if os.environ.get('SMTP_PASSWORD') else "Not set"
    
    print(f"SMTP_SERVER: {smtp_server}")
    print(f"SMTP_PORT: {smtp_port}")
    print(f"SMTP_USERNAME: {smtp_username}")
    print(f"EMAIL_SENDER: {email_sender}")
    print(f"SMTP_PASSWORD: {smtp_password}")
    
    print("\nNote: Passwords are not displayed for security reasons.")

if __name__ == "__main__":
    show_smtp_settings()