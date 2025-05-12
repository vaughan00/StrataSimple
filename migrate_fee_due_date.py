"""
Script to migrate the Fee table to include due_date and paid_amount fields.
This is needed to support the new fee due date and status tracking features.
"""
from app import app, db
from datetime import datetime, timedelta
from sqlalchemy import text

def migrate_fee_model():
    """Add due_date and paid_amount columns to Fee table."""
    with app.app_context():
        # Check if columns exist
        try:
            # Try to add the columns
            print("Adding due_date column...")
            db.session.execute(text("ALTER TABLE fee ADD COLUMN due_date TIMESTAMP"))
            print("Successfully added due_date column.")
            
            print("Adding paid_amount column...")
            db.session.execute(text("ALTER TABLE fee ADD COLUMN paid_amount FLOAT DEFAULT 0.0"))
            print("Successfully added paid_amount column.")
            
            # Update existing fees to have a due date (30 days from creation date by default)
            print("Updating existing fees with default due dates...")
            db.session.execute(text("UPDATE fee SET due_date = date + interval '30 days' WHERE due_date IS NULL"))
            
            # Update existing fees to have correct paid_amount based on payments
            print("Updating paid_amount for existing fees...")
            db.session.execute(text("""
                UPDATE fee SET paid_amount = (
                    SELECT COALESCE(SUM(payment.amount), 0)
                    FROM payment
                    WHERE payment.fee_id = fee.id
                )
            """))
            
            # Make due_date not nullable
            print("Making due_date column not nullable...")
            db.session.execute(text("ALTER TABLE fee ALTER COLUMN due_date SET NOT NULL"))
            
            db.session.commit()
            print("Migration completed successfully.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_fee_model()