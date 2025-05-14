"""
Direct script to add emergency_contact column to Contact table.
This uses direct SQL execution without requiring the field to be present in the model.
"""
import os
from app import app
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

def add_emergency_contact_column():
    """Add emergency_contact column to Contact table using direct SQL."""
    with app.app_context():
        # Get direct database connection
        from app import db
        
        # Use direct raw SQL execution with session transaction management
        try:
            # Check if column exists
            try:
                db.session.execute(text("SELECT emergency_contact FROM contact LIMIT 1"))
                print("Column already exists. Skipping.")
                return True
            except Exception:
                # Column doesn't exist, proceed with adding it
                print("Column doesn't exist. Adding it...")
                db.session.rollback()  # Rollback any failed transaction
                
            # Create a fresh session/connection
            db.session.commit()  # Commit any pending transactions
            
            # Add the column as a separate transaction
            db.session.execute(text("ALTER TABLE contact ADD COLUMN emergency_contact BOOLEAN DEFAULT FALSE"))
            db.session.commit()
            
            print("Successfully added emergency_contact column to Contact table.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error adding column: {e}")
            return False

if __name__ == "__main__":
    add_emergency_contact_column()