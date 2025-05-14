"""
Script to migrate the database schema to include fee_type column.
This approach recreates the database schema using SQLAlchemy.
"""
import os
from app import app, db
from models import Fee, Contact, Property, ContactProperty, Payment, BillingPeriod
import json

def migrate_database():
    """
    Migrate the database to add the fee_type column.
    This approach:
    1. Backs up current data
    2. Drops and recreates the tables with the new schema
    3. Restores the data
    """
    with app.app_context():
        try:
            # Step 1: Backup all data
            print("Backing up existing data...")
            properties = []
            for prop in Property.query.all():
                properties.append({
                    'id': prop.id,
                    'unit_number': prop.unit_number,
                    'description': prop.description,
                    'balance': prop.balance,
                    'entitlement': prop.entitlement,
                    'created_at': prop.created_at.isoformat() if prop.created_at else None
                })
            
            contacts = []
            for contact in Contact.query.all():
                # Handle emergency_contact field
                emergency_contact = False
                # Try to access emergency_contact but handle the case where it doesn't exist yet
                try:
                    emergency_contact = contact.emergency_contact
                except:
                    pass
                
                contacts.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'is_owner': contact.is_owner,
                    'notes': contact.notes,
                    'emergency_contact': emergency_contact,
                    'created_at': contact.created_at.isoformat() if contact.created_at else None
                })
            
            contact_properties = []
            for cp in ContactProperty.query.all():
                contact_properties.append({
                    'contact_id': cp.contact_id,
                    'property_id': cp.property_id,
                    'relationship_type': cp.relationship_type,
                    'created_at': cp.created_at.isoformat() if cp.created_at else None
                })
            
            fees = []
            for fee in Fee.query.all():
                fees.append({
                    'id': fee.id,
                    'property_id': fee.property_id,
                    'amount': fee.amount,
                    'date': fee.date.isoformat() if fee.date else None,
                    'description': fee.description,
                    'period': fee.period,
                    'paid': fee.paid,
                    'fee_type': 'billing_period',  # Default all existing fees to billing_period
                    'created_at': fee.created_at.isoformat() if fee.created_at else None
                })
            
            payments = []
            for payment in Payment.query.all():
                payments.append({
                    'id': payment.id,
                    'property_id': payment.property_id,
                    'fee_id': payment.fee_id,
                    'amount': payment.amount,
                    'date': payment.date.isoformat() if payment.date else None,
                    'description': payment.description,
                    'reference': payment.reference,
                    'reconciled': payment.reconciled,
                    'is_duplicate': payment.is_duplicate,
                    'confirmed': payment.confirmed,
                    'transaction_id': payment.transaction_id,
                    'created_at': payment.created_at.isoformat() if payment.created_at else None
                })
            
            billing_periods = []
            for period in BillingPeriod.query.all():
                billing_periods.append({
                    'id': period.id,
                    'name': period.name,
                    'start_date': period.start_date.isoformat() if period.start_date else None,
                    'end_date': period.end_date.isoformat() if period.end_date else None,
                    'total_amount': period.total_amount,
                    'description': period.description,
                    'created_at': period.created_at.isoformat() if period.created_at else None
                })
            
            backup = {
                'properties': properties,
                'contacts': contacts,
                'contact_properties': contact_properties,
                'fees': fees,
                'payments': payments,
                'billing_periods': billing_periods
            }
            
            with open('db_backup.json', 'w') as f:
                json.dump(backup, f, indent=2)
            
            print("Data backup completed.")
            
            # Step 2: Drop and recreate tables
            print("Updating database schema...")
            db.drop_all()
            
            # Add fee_type to Fee model
            from models import Fee
            
            # Now update models.py to include fee_type field
            with open('models.py', 'r') as f:
                content = f.read()
            
            # Check if fee_type is already in the model
            if 'fee_type = db.Column' not in content:
                content = content.replace(
                    'paid = db.Column(db.Boolean, default=False)\n    created_at',
                    'paid = db.Column(db.Boolean, default=False)\n    fee_type = db.Column(db.String(50), default="billing_period")  # Options: billing_period, opening_balance, ad_hoc\n    created_at'
                )
                
                with open('models.py', 'w') as f:
                    f.write(content)
                
                print("Updated Fee model with fee_type field.")
                
            # Check if emergency_contact field is already in the Contact model
            if 'emergency_contact = db.Column' not in content:
                content = content.replace(
                    'notes = db.Column(db.Text)\n    created_at',
                    'notes = db.Column(db.Text)\n    emergency_contact = db.Column(db.Boolean, default=False)  # Visible to all residents if True\n    created_at'
                )
                
                with open('models.py', 'w') as f:
                    f.write(content)
                
                print("Updated Contact model with emergency_contact field.")
            
            # Recreate tables
            db.create_all()
            print("Database schema updated.")
            
            # Step 3: Restore data from backup
            print("Restoring data...")
            
            # Restore properties
            for prop_data in backup['properties']:
                prop = Property(
                    id=prop_data['id'],
                    unit_number=prop_data['unit_number'],
                    description=prop_data['description'],
                    balance=prop_data['balance'],
                    entitlement=prop_data['entitlement']
                )
                db.session.add(prop)
            
            db.session.commit()
            print(f"Restored {len(backup['properties'])} properties.")
            
            # Restore contacts
            for contact_data in backup['contacts']:
                contact = Contact(
                    id=contact_data['id'],
                    name=contact_data['name'],
                    email=contact_data['email'],
                    phone=contact_data['phone'],
                    is_owner=contact_data['is_owner'],
                    notes=contact_data['notes'],
                    emergency_contact=contact_data.get('emergency_contact', False)  # Include emergency_contact field
                )
                db.session.add(contact)
            
            db.session.commit()
            print(f"Restored {len(backup['contacts'])} contacts.")
            
            # Restore contact-property relationships
            for cp_data in backup['contact_properties']:
                cp = ContactProperty(
                    contact_id=cp_data['contact_id'],
                    property_id=cp_data['property_id'],
                    relationship_type=cp_data['relationship_type']
                )
                db.session.add(cp)
                
            db.session.commit()
            print(f"Restored {len(backup['contact_properties'])} contact-property relationships.")
            
            # Restore billing periods
            for period_data in backup['billing_periods']:
                from datetime import datetime
                
                period = BillingPeriod(
                    id=period_data['id'],
                    name=period_data['name'],
                    start_date=datetime.fromisoformat(period_data['start_date']) if period_data['start_date'] else None,
                    end_date=datetime.fromisoformat(period_data['end_date']) if period_data['end_date'] else None,
                    total_amount=period_data['total_amount'],
                    description=period_data['description']
                )
                db.session.add(period)
                
            db.session.commit()
            print(f"Restored {len(backup['billing_periods'])} billing periods.")
            
            # Restore fees with the new fee_type field
            for fee_data in backup['fees']:
                from datetime import datetime
                
                fee = Fee(
                    id=fee_data['id'],
                    property_id=fee_data['property_id'],
                    amount=fee_data['amount'],
                    date=datetime.fromisoformat(fee_data['date']) if fee_data['date'] else None,
                    description=fee_data['description'],
                    period=fee_data['period'],
                    paid=fee_data['paid'],
                    fee_type=fee_data.get('fee_type', 'billing_period')  # Use the new field
                )
                db.session.add(fee)
                
            db.session.commit()
            print(f"Restored {len(backup['fees'])} fees.")
            
            # Restore payments
            for payment_data in backup['payments']:
                from datetime import datetime
                
                payment = Payment(
                    id=payment_data['id'],
                    property_id=payment_data['property_id'],
                    fee_id=payment_data['fee_id'],
                    amount=payment_data['amount'],
                    date=datetime.fromisoformat(payment_data['date']) if payment_data['date'] else None,
                    description=payment_data['description'],
                    reference=payment_data['reference'],
                    reconciled=payment_data['reconciled'],
                    is_duplicate=payment_data['is_duplicate'],
                    confirmed=payment_data['confirmed'],
                    transaction_id=payment_data['transaction_id']
                )
                db.session.add(payment)
                
            db.session.commit()
            print(f"Restored {len(backup['payments'])} payments.")
            
            print("Migration completed successfully.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_database()