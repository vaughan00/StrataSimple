"""
Script to add emergency_contact field to the Contact table.
This field indicates if a contact's details should be visible to all users.
"""
import sys
from app import app, db
from sqlalchemy import Column, Boolean
from sqlalchemy.sql import text

def add_emergency_contact_field():
    """Add emergency_contact column to Contact table."""
    with app.app_context():
        try:
            # Check if the column already exists
            db.session.execute(text("SELECT emergency_contact FROM contact LIMIT 1"))
            print("Column already exists. Skipping migration.")
            return
        except Exception:
            pass  # Column doesn't exist, proceed with migration
            
        try:
            # Add the column using session.execute
            db.session.execute(text('ALTER TABLE contact ADD COLUMN emergency_contact BOOLEAN DEFAULT FALSE'))
            db.session.commit()
            print("Added emergency_contact column to Contact table.")
        except Exception as e:
            print(f"Error adding column: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    add_emergency_contact_field()