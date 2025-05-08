"""
Script to seed the database with test data.
Run this script to create sample properties, contacts, and relationships.
"""
import os
import sys
from datetime import datetime, timedelta

from app import app, db
from models import Property, Contact, ContactProperty, Fee, BillingPeriod

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
            Property(unit_number="Unit 101", description="Corner unit with balcony", entitlement=1.2),
            Property(unit_number="Unit 202", description="Two-bedroom with garden view", entitlement=1.0),
            Property(unit_number="Unit 303", description="Penthouse with rooftop access", entitlement=1.5)
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
        
        # Create fees for each property
        total_entitlement = sum(prop.entitlement for prop in properties)
        
        for prop in properties:
            # Calculate fee based on entitlement
            fee_amount = (prop.entitlement / total_entitlement) * period.total_amount
            
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

if __name__ == "__main__":
    create_seed_data()