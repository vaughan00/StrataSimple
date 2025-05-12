"""
Script to reset the database to its initial empty state.
This script will drop all tables and recreate them.
"""

from main import app
from app import db
import models

print("Dropping all tables...")
with app.app_context():
    db.drop_all()
    print("Recreating all tables...")
    db.create_all()
    print("Database reset complete!")