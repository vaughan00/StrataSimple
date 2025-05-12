"""
Script to add fee_type column to the Fee table in the database.
This is needed to support the flexible fee assignment feature.
"""
from app import app, db
from models import Fee

def add_fee_type_column():
    """Add fee_type column to Fee table."""
    with app.app_context():
        # Check if the column exists
        try:
            # Try to query the column to see if it exists
            db.session.execute(db.select(Fee.fee_type).limit(1))
            print("Column already exists, no change needed.")
            return
        except Exception as e:
            if "column fee.fee_type does not exist" in str(e):
                print("Column does not exist. Adding it now...")
            else:
                print(f"An unexpected error occurred: {e}")
                return
        
        # Add the column using SQL directly
        sql = "ALTER TABLE fee ADD COLUMN fee_type VARCHAR(50) DEFAULT 'billing_period'"
        db.session.execute(db.text(sql))
        db.session.commit()
        print("Successfully added fee_type column to Fee table.")

if __name__ == "__main__":
    add_fee_type_column()