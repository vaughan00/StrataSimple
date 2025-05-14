"""
Script to fix the emergency_contact field issue by recreating the database properly.
This is used to resolve a migration issue when the field is already in the model but not in the database.
"""
import os
import sys
import json
from datetime import datetime
from app import app, db
from sqlalchemy import text

def fix_emergency_contact():
    """
    Fix the emergency_contact field issue by:
    1. Temporarily patching the models.py to remove the emergency_contact field
    2. Backing up all data
    3. Dropping and recreating tables
    4. Restoring data
    5. Adding the emergency_contact field to the schema
    """
    with app.app_context():
        try:
            print("Starting migration process...")
            
            # Step 1: Temporarily patch models.py to remove emergency_contact field
            print("Patching models.py to temporarily remove emergency_contact field...")
            with open('models.py', 'r') as f:
                content = f.read()
            
            # Save original file
            with open('models.py.bak', 'w') as f:
                f.write(content)
            
            # Remove emergency_contact field
            if 'emergency_contact = db.Column' in content:
                content = content.replace('    emergency_contact = db.Column(db.Boolean, default=False)  # Visible to all residents if True\n', '')
                
                with open('models.py', 'w') as f:
                    f.write(content)
                
                print("Temporarily removed emergency_contact field from models.py.")
            
            # Reload models to apply the changes
            import importlib
            import models
            importlib.reload(models)
            
            # Extract model classes from the updated module
            from models import Contact, Property, ContactProperty, Payment, Fee, BillingPeriod, User, ActivityLog, Expense, StrataSettings
            
            # Step 2: Backup all data
            print("Backing up existing data...")
            
            # Backup contacts
            contacts = []
            for contact in Contact.query.all():
                contacts.append({
                    'id': contact.id,
                    'name': contact.name,
                    'email': contact.email,
                    'phone': contact.phone,
                    'is_owner': contact.is_owner,
                    'notes': contact.notes,
                    'created_at': contact.created_at.isoformat() if contact.created_at else None
                })
            print(f"Backed up {len(contacts)} contacts.")
            
            # Backup properties
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
            print(f"Backed up {len(properties)} properties.")
            
            # Backup contact-property relationships
            contact_properties = []
            for cp in ContactProperty.query.all():
                contact_properties.append({
                    'contact_id': cp.contact_id,
                    'property_id': cp.property_id,
                    'relationship_type': cp.relationship_type,
                    'created_at': cp.created_at.isoformat() if cp.created_at else None
                })
            print(f"Backed up {len(contact_properties)} contact-property relationships.")
            
            # Backup fees
            fees = []
            for fee in Fee.query.all():
                fees.append({
                    'id': fee.id,
                    'property_id': fee.property_id,
                    'amount': fee.amount,
                    'date': fee.date.isoformat() if fee.date else None,
                    'due_date': fee.due_date.isoformat() if hasattr(fee, 'due_date') and fee.due_date else None,
                    'description': fee.description,
                    'period': fee.period,
                    'paid': fee.paid,
                    'fee_type': fee.fee_type if hasattr(fee, 'fee_type') else 'billing_period',
                    'paid_amount': fee.paid_amount if hasattr(fee, 'paid_amount') else 0.0,
                    'created_at': fee.created_at.isoformat() if fee.created_at else None
                })
            print(f"Backed up {len(fees)} fees.")
            
            # Backup payments
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
            print(f"Backed up {len(payments)} payments.")
            
            # Backup billing periods
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
            print(f"Backed up {len(billing_periods)} billing periods.")
            
            # Backup users
            users = []
            for user in User.query.all():
                users.append({
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'token': user.token,
                    'token_expiry': user.token_expiry.isoformat() if user.token_expiry else None,
                    'property_id': user.property_id,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                })
            print(f"Backed up {len(users)} users.")
            
            # Backup activity logs
            logs = []
            for log in ActivityLog.query.all():
                logs.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                    'event_type': log.event_type,
                    'description': log.description,
                    'related_object_type': log.related_object_type,
                    'related_object_id': log.related_object_id,
                })
            print(f"Backed up {len(logs)} activity logs.")
            
            # Backup expenses
            expenses = []
            for expense in Expense.query.all():
                expenses.append({
                    'id': expense.id,
                    'amount': expense.amount,
                    'name': expense.name,
                    'description': expense.description,
                    'due_date': expense.due_date.isoformat() if expense.due_date else None,
                    'paid': expense.paid,
                    'paid_date': expense.paid_date.isoformat() if expense.paid_date else None,
                    'invoice_filename': expense.invoice_filename,
                    'matched_transaction_id': expense.matched_transaction_id,
                    'created_at': expense.created_at.isoformat() if expense.created_at else None
                })
            print(f"Backed up {len(expenses)} expenses.")
            
            # Backup strata settings
            settings = []
            for setting in StrataSettings.query.all():
                settings.append({
                    'id': setting.id,
                    'strata_name': setting.strata_name,
                    'address': setting.address,
                    'admin_email': setting.admin_email,
                    'bank_account_name': setting.bank_account_name,
                    'bank_bsb': setting.bank_bsb,
                    'bank_account_number': setting.bank_account_number,
                    'created_at': setting.created_at.isoformat() if setting.created_at else None
                })
            print(f"Backed up {len(settings)} strata settings.")
            
            backup = {
                'contacts': contacts,
                'properties': properties,
                'contact_properties': contact_properties,
                'fees': fees,
                'payments': payments,
                'billing_periods': billing_periods,
                'users': users,
                'activity_logs': logs,
                'expenses': expenses,
                'strata_settings': settings
            }
            
            with open('db_backup_emergency.json', 'w') as f:
                json.dump(backup, f, indent=2)
            
            print("Data backup completed.")
            
            # Step 3: Drop and recreate tables
            print("Dropping and recreating database schema...")
            db.drop_all()
            db.create_all()
            print("Database schema recreated.")
            
            # Step 4: Restore data
            print("Restoring data without emergency_contact field...")
            
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
                    notes=contact_data['notes']
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
            
            # Restore fees
            for fee_data in backup['fees']:
                fee = Fee(
                    id=fee_data['id'],
                    property_id=fee_data['property_id'],
                    amount=fee_data['amount'],
                    date=datetime.fromisoformat(fee_data['date']) if fee_data['date'] else None,
                    description=fee_data['description'],
                    period=fee_data['period'],
                    paid=fee_data['paid']
                )
                # Handle due_date, fee_type, and paid_amount if they exist
                if hasattr(Fee, 'due_date') and fee_data.get('due_date'):
                    fee.due_date = datetime.fromisoformat(fee_data['due_date'])
                if hasattr(Fee, 'fee_type'):
                    fee.fee_type = fee_data.get('fee_type', 'billing_period')
                if hasattr(Fee, 'paid_amount'):
                    fee.paid_amount = fee_data.get('paid_amount', 0.0)
                
                db.session.add(fee)
            db.session.commit()
            print(f"Restored {len(backup['fees'])} fees.")
            
            # Restore payments
            for payment_data in backup['payments']:
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
            
            # Restore users
            for user_data in backup['users']:
                user = User(
                    id=user_data['id'],
                    email=user_data['email'],
                    role=user_data['role'],
                    token=user_data['token'],
                    token_expiry=datetime.fromisoformat(user_data['token_expiry']) if user_data['token_expiry'] else None,
                    property_id=user_data['property_id'],
                    last_login=datetime.fromisoformat(user_data['last_login']) if user_data['last_login'] else None
                )
                db.session.add(user)
            db.session.commit()
            print(f"Restored {len(backup['users'])} users.")
            
            # Restore activity logs
            for log_data in backup['activity_logs']:
                log = ActivityLog(
                    id=log_data['id'],
                    timestamp=datetime.fromisoformat(log_data['timestamp']) if log_data['timestamp'] else None,
                    event_type=log_data['event_type'],
                    description=log_data['description'],
                    related_object_type=log_data['related_object_type'],
                    related_object_id=log_data['related_object_id']
                )
                db.session.add(log)
            db.session.commit()
            print(f"Restored {len(backup['activity_logs'])} activity logs.")
            
            # Restore expenses
            for expense_data in backup['expenses']:
                expense = Expense(
                    id=expense_data['id'],
                    amount=expense_data['amount'],
                    name=expense_data['name'],
                    description=expense_data['description'],
                    due_date=datetime.fromisoformat(expense_data['due_date']) if expense_data['due_date'] else None,
                    paid=expense_data['paid'],
                    paid_date=datetime.fromisoformat(expense_data['paid_date']) if expense_data['paid_date'] else None,
                    invoice_filename=expense_data['invoice_filename'],
                    matched_transaction_id=expense_data['matched_transaction_id']
                )
                db.session.add(expense)
            db.session.commit()
            print(f"Restored {len(backup['expenses'])} expenses.")
            
            # Restore strata settings
            for setting_data in backup['strata_settings']:
                setting = StrataSettings(
                    id=setting_data['id'],
                    strata_name=setting_data['strata_name'],
                    address=setting_data['address'],
                    admin_email=setting_data['admin_email'],
                    bank_account_name=setting_data['bank_account_name'],
                    bank_bsb=setting_data['bank_bsb'],
                    bank_account_number=setting_data['bank_account_number']
                )
                db.session.add(setting)
            db.session.commit()
            print(f"Restored {len(backup['strata_settings'])} strata settings.")
            
            # Step 5: Restore original models.py file with emergency_contact field
            print("Restoring original models.py file with emergency_contact field...")
            with open('models.py.bak', 'r') as f:
                content = f.read()
                
            with open('models.py', 'w') as f:
                f.write(content)
                
            # Now add the emergency_contact column to the database
            print("Adding emergency_contact column to Contact table...")
            db.session.execute(text('ALTER TABLE contact ADD COLUMN emergency_contact BOOLEAN DEFAULT FALSE'))
            db.session.commit()
            print("Added emergency_contact column to Contact table.")
            
            # Log completion
            print("Migration completed successfully.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            
            # Try to restore the original models.py file if it exists
            if os.path.exists('models.py.bak'):
                print("Restoring original models.py file...")
                with open('models.py.bak', 'r') as f:
                    content = f.read()
                    
                with open('models.py', 'w') as f:
                    f.write(content)
                    
                print("Original models.py file restored.")
                
            raise

if __name__ == "__main__":
    fix_emergency_contact()