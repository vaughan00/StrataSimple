"""
Script to seed the database with test data.
Run this script to create sample properties, contacts, and relationships.
"""
import os
import sys
from datetime import datetime, timedelta

from app import app, db
from models import Property, Contact, ContactProperty, Fee, BillingPeriod, User

def create_seed_data():
    """Create seed data for testing."""
    with app.app_context():
        # Check if data already exists
        if Property.query.count() > 0:
            print("Database already has data. Skipping seed.")
            return

        print("Creating seed data...")
        
        # Create properties
        properties = [
            Property(unit_number="Unit 101", description="Corner unit with balcony"),
            Property(unit_number="Unit 202", description="Two-bedroom with garden view"),
            Property(unit_number="Unit 303", description="Penthouse with rooftop access")
        ]
        
        # Add properties to database
        for prop in properties:
            db.session.add(prop)
        
        # Flush to get property IDs
        db.session.flush()
        
        # Create contacts (owners)
        contacts = [
            Contact(name="John Smith", email="john.smith@example.com", phone="555-123-4567", is_owner=True, 
                   notes="Primary contact for Unit 101"),
            Contact(name="Jane Doe", email="jane.doe@example.com", phone="555-234-5678", is_owner=True, 
                   notes="Prefers email communication"),
            Contact(name="Alex Johnson", email="alex.johnson@example.com", phone="555-345-6789", is_owner=True, 
                   notes="Overseas owner, contact during business hours only")
        ]
        
        # Add contacts to database
        for contact in contacts:
            db.session.add(contact)
        
        # Flush to get contact IDs
        db.session.flush()
        
        # Create property-contact relationships
        relationships = [
            ContactProperty(contact_id=contacts[0].id, property_id=properties[0].id, relationship_type="owner"),
            ContactProperty(contact_id=contacts[1].id, property_id=properties[1].id, relationship_type="owner"),
            ContactProperty(contact_id=contacts[2].id, property_id=properties[2].id, relationship_type="owner")
        ]
        
        # Add relationships to database
        for relationship in relationships:
            db.session.add(relationship)
        
        # Create a billing period
        now = datetime.now()
        quarter_start = datetime(now.year, ((now.month - 1) // 3) * 3 + 1, 1)
        quarter_end = quarter_start + timedelta(days=90)
        
        period = BillingPeriod(
            name=f"Q{(now.month - 1) // 3 + 1} {now.year}",
            start_date=quarter_start,
            end_date=quarter_end,
            total_amount=1000.0,
            description="Quarterly maintenance fees"
        )
        
        db.session.add(period)
        db.session.flush()
        
        # Create fees for each property (equal distribution)
        num_properties = len(properties)
        
        for prop in properties:
            # Calculate fee (equal split among all properties)
            fee_amount = period.total_amount / num_properties if num_properties > 0 else 0
            
            fee = Fee(
                property_id=prop.id,
                amount=fee_amount,
                date=period.start_date,
                description=f"Strata fee for {period.name}",
                period=period.name,
                paid=False
            )
            
            db.session.add(fee)
            
            # Deduct fee from property balance
            prop.balance -= fee_amount
        
        # Commit all changes
        db.session.commit()
        
        print(f"Created {len(properties)} properties with {len(contacts)} owners.")
        print(f"Created billing period {period.name} with fees for all properties.")
        
        # Print property details for reference
        for i, prop in enumerate(properties):
            owner = prop.get_owner()
            owner_name = owner.name if owner else "No owner"
            print(f"Property: {prop.unit_number}, Owner: {owner_name}, Balance: ${prop.balance:.2f}")

def create_admin_user(email="admin@stratahub.com"):
    """
    Create an admin user if one doesn't already exist.
    This should be run after the initial seed data is created.
    """
    with app.app_context():
        # Check if the admin user already exists
        existing_admin = User.query.filter_by(email=email, role='admin').first()
        if existing_admin:
            print(f"Admin user {email} already exists.")
            return
        
        # Create a new admin user
        admin = User()
        admin.email = email
        admin.role = 'admin'
        # Admin doesn't need to be associated with a specific property
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"Created admin user: {email}")
        print("The admin can log in via the login page by requesting a magic link.")

def create_committee_users():
    """
    Create committee users for each property if they don't already exist.
    This assigns committee role to the first owner of each property.
    """
    with app.app_context():
        properties = Property.query.all()
        
        for prop in properties:
            # Get the owner
            owner = prop.get_owner()
            if not owner or not owner.email:
                continue
                
            # Check if a committee user exists with this email
            existing_user = User.query.filter_by(email=owner.email).first()
            if existing_user:
                if existing_user.role == 'admin':
                    # Don't downgrade admin to committee
                    continue
                existing_user.role = 'committee'
                db.session.add(existing_user)
                print(f"Updated user {owner.email} to committee role.")
            else:
                # Create new committee user
                committee = User()
                committee.email = owner.email
                committee.role = 'committee'
                committee.property_id = prop.id
                
                db.session.add(committee)
                print(f"Created committee user: {owner.email} for property {prop.unit_number}")
        
        db.session.commit()

if __name__ == "__main__":
    create_seed_data()
    create_admin_user()
    create_committee_users()