import os
import pandas as pd
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, jsonify, session
from werkzeug.utils import secure_filename
from io import StringIO

from app import app, db
from models import Property, Payment, Fee, BillingPeriod, Contact, ContactProperty
from utils import process_csv, analyze_payments

@app.route('/')
def index():
    """Main dashboard showing financial status of all properties."""
    properties = Property.query.all()
    total_balance = sum(prop.balance for prop in properties)
    total_fees = db.session.query(db.func.sum(Fee.amount)).filter_by(paid=False).scalar() or 0
    total_paid = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    
    # Get recent payments and fees
    recent_payments = Payment.query.order_by(Payment.date.desc()).limit(5).all()
    recent_fees = Fee.query.order_by(Fee.date.desc()).limit(5).all()
    
    # Debug info
    print("RECENT FEES INFO:")
    for fee in recent_fees:
        payment_total = sum(payment.amount for payment in fee.payments) if hasattr(fee, 'payments') and fee.payments else 0
        print(f"  Fee ID: {fee.id}, Amount: {fee.amount}, Paid status: {fee.paid}, Payments: {payment_total}")
    
    return render_template('dashboard.html', 
                           properties=properties, 
                           total_balance=total_balance,
                           total_fees=total_fees,
                           total_paid=total_paid,
                           recent_payments=recent_payments,
                           recent_fees=recent_fees)

@app.route('/api/properties')
def get_properties():
    """API endpoint to get all properties data."""
    properties = Property.query.all()
    properties_data = []
    
    for prop in properties:
        unpaid_fees = sum(fee.amount for fee in prop.fees if not fee.paid)
        total_payments = sum(payment.amount for payment in prop.payments)
        
        # Get owner name
        owner = prop.get_owner()
        owner_name = owner.name if owner else "No owner assigned"
        
        properties_data.append({
            'id': prop.id,
            'unit_number': prop.unit_number,
            'owner_name': owner_name,
            'balance': prop.balance,
            'unpaid_fees': unpaid_fees,
            'total_payments': total_payments
        })
    
    return jsonify(properties_data)

@app.route('/reconciliation', methods=['GET', 'POST'])
def reconciliation():
    """Page for CSV upload and reconciliation."""
    if request.method == 'POST':
        # Handle CSV file upload
        if 'file' in request.files:
            file = request.files['file']
            
            # Check if file is empty
            if file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)
            
            # Check file type
            if file and (file.filename.endswith('.csv') or file.filename.lower().endswith('.csv')):
                # Read CSV content with error handling for different encodings
                file_content = file.read()
                
                # Try different encodings
                encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
                content = None
                
                for encoding in encodings:
                    try:
                        content = file_content.decode(encoding)
                        break  # Successfully decoded
                    except UnicodeDecodeError:
                        continue  # Try next encoding
                
                if content is None:
                    flash('Could not decode CSV file. Please ensure it uses a standard encoding.', 'danger')
                    return redirect(request.url)
                
                try:
                    # Process CSV data and analyze payments
                    payments = process_csv(content)
                    analyzed_payments = analyze_payments(payments)
                    
                    # Store in session for later confirmation
                    session_data = {
                        'transactions': [
                            {
                                'date': payment['date'].strftime('%Y-%m-%d'),
                                'amount': payment['amount'],
                                'description': payment['description'],
                                'reference': payment['reference'],
                                'transaction_id': payment['transaction_id'],
                                'is_duplicate': payment.get('is_duplicate', False),
                                'suggested_property_id': payment.get('suggested_property', {}).get('id') if payment.get('suggested_property') else None,
                                'suggested_fee_id': payment.get('suggested_fee', {}).get('id') if payment.get('suggested_fee') else None
                            }
                            for payment in analyzed_payments
                        ]
                    }
                    
                    # Count duplicates
                    duplicate_count = sum(1 for p in analyzed_payments if p.get('is_duplicate', False))
                    
                    # Count suggested matches
                    suggested_matches = sum(1 for p in analyzed_payments if p.get('suggested_property') is not None)
                    
                    flash(f'Successfully processed {len(analyzed_payments)} transactions. Found {duplicate_count} potential duplicates and suggested matches for {suggested_matches} transactions.', 'success')
                    
                    return render_template('reconciliation.html', 
                                          transactions=analyzed_payments,
                                          properties=Property.query.all(),
                                          unpaid_fees=Fee.query.filter_by(paid=False).all())
                
                except Exception as e:
                    flash(f'Error processing CSV: {str(e)}', 'danger')
                    return redirect(request.url)
            else:
                flash('Only CSV files are allowed', 'danger')
                return redirect(request.url)
                
        # Handle transaction confirmation form
        elif request.form.get('action') == 'confirm_matches':
            # Process the confirmed transactions
            transaction_ids = request.form.getlist('transaction_id')
            property_ids = request.form.getlist('property_id')
            fee_ids = request.form.getlist('fee_id')
            exclude_flags = request.form.getlist('exclude')
            
            confirmed_count = 0
            excluded_count = 0
            
            for i, transaction_id in enumerate(transaction_ids):
                # Skip if excluded
                if str(i) in exclude_flags:
                    excluded_count += 1
                    continue
                
                # Get form data
                property_id = property_ids[i] if property_ids[i] else None
                fee_id = fee_ids[i] if fee_ids[i] and fee_ids[i] != "null" else None
                
                # Skip if no property selected
                if not property_id:
                    continue
                
                # Get transaction details from form
                date_str = request.form.getlist('date')[i]
                amount = float(request.form.getlist('amount')[i])
                description = request.form.getlist('description')[i]
                reference = request.form.getlist('reference')[i]
                
                date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Create payment record
                new_payment = Payment(
                    property_id=property_id,
                    fee_id=fee_id,
                    amount=amount,
                    date=date,
                    description=description,
                    reference=reference,
                    transaction_id=transaction_id,
                    reconciled=True,
                    confirmed=True
                )
                db.session.add(new_payment)
                
                # Update property balance
                property = Property.query.get(property_id)
                if property:
                    property.balance += amount
                
                # Mark fee as paid if assigned
                if fee_id:
                    fee = Fee.query.get(fee_id)
                    if fee:
                        fee.paid = True
                
                confirmed_count += 1
            
            db.session.commit()
            
            flash(f'Successfully confirmed {confirmed_count} payments and excluded {excluded_count} transactions.', 'success')
            return redirect(url_for('index'))
    
    # GET request - show previously confirmed payments
    recently_confirmed = Payment.query.filter_by(confirmed=True).order_by(Payment.created_at.desc()).limit(10).all()
    
    return render_template('reconciliation.html', 
                          transactions=None,
                          properties=Property.query.all(),
                          unpaid_fees=Fee.query.filter_by(paid=False).all(), 
                          recently_confirmed=recently_confirmed)

@app.route('/fees', methods=['GET', 'POST'])
def fees():
    """Page for raising new strata fees."""
    properties = Property.query.all()
    periods = BillingPeriod.query.order_by(BillingPeriod.start_date.desc()).all()
    
    if request.method == 'POST':
        # Check if all properties have owners first
        properties_without_owners = []
        for prop in properties:
            if not prop.get_owner():
                properties_without_owners.append(prop.unit_number)
                
        if properties_without_owners:
            flash(f'Cannot raise fees: The following properties have no assigned owners: {", ".join(properties_without_owners)}', 'danger')
            return redirect(url_for('fees'))
        
        # Create new billing period
        period_name = request.form.get('period_name')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        fee_per_unit = float(request.form.get('fee_per_unit'))
        description = request.form.get('description')
        
        # Calculate total amount based on fee per unit
        num_properties = len(properties)
        total_amount = fee_per_unit * num_properties
        
        new_period = BillingPeriod(
            name=period_name,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            description=description
        )
        db.session.add(new_period)
        db.session.commit()
        
        # Create fees for all properties
        for prop in properties:
            # Use fee per unit directly
            fee_amount = fee_per_unit
            
            new_fee = Fee(
                property_id=prop.id,
                amount=fee_amount,
                date=start_date,
                description=f"Strata fee for {period_name}",
                period=period_name,
                paid=False
            )
            db.session.add(new_fee)
            
            # Update property balance
            prop.balance -= fee_amount
        
        db.session.commit()
        
        flash(f'Successfully created {period_name} fees for all properties', 'success')
        return redirect(url_for('fees'))
    
    return render_template('fees.html', properties=properties, periods=periods)

@app.route('/api/billing_periods/<int:period_id>/fees')
def get_period_fees(period_id):
    """API endpoint to get fees for a specific billing period."""
    period = BillingPeriod.query.get_or_404(period_id)
    fees = Fee.query.filter_by(period=period.name).all()
    
    fees_data = []
    for fee in fees:
        property = Property.query.get(fee.property_id)
        if not property:
            continue
            
        # Get owner name
        owner = property.get_owner()
        owner_name = owner.name if owner else "No owner assigned"
        
        # Get payments associated with this fee
        payments = fee.payments if hasattr(fee, 'payments') else []
        
        fees_data.append({
            'id': fee.id,
            'unit_number': property.unit_number,
            'owner_name': owner_name,
            'amount': fee.amount,
            'paid': fee.paid,
            'payments': [{'amount': payment.amount, 'date': payment.date.strftime('%Y-%m-%d')} for payment in payments]
        })
    
    return jsonify(fees_data)

@app.route('/api/mark_fee_paid/<int:fee_id>', methods=['POST'])
def mark_fee_paid(fee_id):
    """API endpoint to mark a fee as paid."""
    fee = Fee.query.get_or_404(fee_id)
    fee.paid = True
    db.session.commit()
    
    return jsonify({'success': True})

# Setup routes
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """Page for initial strata setup and property management."""
    properties = Property.query.all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_property':
            # Add a new property
            unit_number = request.form.get('unit_number')
            description = request.form.get('description')
            
            # Check if property with this unit number already exists
            if Property.query.filter_by(unit_number=unit_number).first():
                flash(f'Property with unit number {unit_number} already exists', 'danger')
                return redirect(url_for('setup'))
            
            # Create new property (entitlement fixed at 1.0)
            new_property = Property(
                unit_number=unit_number,
                description=description
            )
            db.session.add(new_property)
            db.session.commit()
            
            flash(f'Property {unit_number} added successfully', 'success')
            return redirect(url_for('setup'))
            
        elif action == 'edit_property':
            # Edit existing property
            property_id = request.form.get('property_id')
            property = Property.query.get_or_404(property_id)
            
            property.unit_number = request.form.get('unit_number')
            property.description = request.form.get('description')
            # Entitlement fixed at 1.0
            
            db.session.commit()
            
            flash(f'Property {property.unit_number} updated successfully', 'success')
            return redirect(url_for('setup'))
            
        elif action == 'delete_property':
            # Delete property
            property_id = request.form.get('property_id')
            property = Property.query.get_or_404(property_id)
            
            # Check if property has payments or fees
            if property.payments or property.fees:
                flash(f'Cannot delete property {property.unit_number} because it has associated payments or fees', 'danger')
                return redirect(url_for('setup'))
            
            # Delete all contact associations
            for assoc in property.contact_associations:
                db.session.delete(assoc)
            
            db.session.delete(property)
            db.session.commit()
            
            flash(f'Property {property.unit_number} deleted successfully', 'success')
            return redirect(url_for('setup'))
            
        elif action == 'bulk_add':
            # Bulk add properties
            num_properties = int(request.form.get('num_properties') or 0)
            prefix = request.form.get('prefix') or 'Unit'
            
            if num_properties <= 0:
                flash('Please enter a valid number of properties', 'danger')
                return redirect(url_for('setup'))
            
            # Create properties with sequential unit numbers
            for i in range(1, num_properties + 1):
                unit_number = f"{prefix} {i}"
                
                # Skip if property with this unit number already exists
                if Property.query.filter_by(unit_number=unit_number).first():
                    continue
                
                new_property = Property(
                    unit_number=unit_number
                    # entitlement defaults to 1.0
                )
                db.session.add(new_property)
            
            db.session.commit()
            
            flash(f'Successfully added {num_properties} properties', 'success')
            return redirect(url_for('setup'))
    
    return render_template('setup.html', properties=properties)

@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    """Page for managing contacts and owners."""
    contacts = Contact.query.all()
    properties = Property.query.all()
    
    # Pre-fetch all property contacts to avoid the need for AJAX
    property_contacts = {}
    for property in properties:
        contacts_data = []
        for assoc in property.contact_associations:
            contacts_data.append({
                'contact_id': assoc.contact_id,
                'name': assoc.contact.name,
                'relationship_type': assoc.relationship_type,
                'email': assoc.contact.email,
                'phone': assoc.contact.phone
            })
        property_contacts[property.id] = contacts_data
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_contact':
            # Add a new contact
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            is_owner = request.form.get('is_owner') == 'on'
            notes = request.form.get('notes')
            
            new_contact = Contact(
                name=name,
                email=email,
                phone=phone,
                is_owner=is_owner,
                notes=notes
            )
            db.session.add(new_contact)
            db.session.commit()
            
            flash(f'Contact {name} added successfully', 'success')
            return redirect(url_for('contacts'))
            
        elif action == 'edit_contact':
            # Edit existing contact
            contact_id = request.form.get('contact_id')
            contact = Contact.query.get_or_404(contact_id)
            
            contact.name = request.form.get('name')
            contact.email = request.form.get('email')
            contact.phone = request.form.get('phone')
            contact.is_owner = request.form.get('is_owner') == 'on'
            contact.notes = request.form.get('notes')
            
            db.session.commit()
            
            flash(f'Contact {contact.name} updated successfully', 'success')
            return redirect(url_for('contacts'))
            
        elif action == 'delete_contact':
            # Delete contact
            contact_id = request.form.get('contact_id')
            contact = Contact.query.get_or_404(contact_id)
            
            # Delete all property associations
            for assoc in contact.property_associations:
                db.session.delete(assoc)
            
            db.session.delete(contact)
            db.session.commit()
            
            flash(f'Contact {contact.name} deleted successfully', 'success')
            return redirect(url_for('contacts'))
            
        elif action == 'assign_property':
            # Assign contact to property
            contact_id = request.form.get('contact_id')
            property_id = request.form.get('property_id')
            relationship_type = request.form.get('relationship_type')
            
            # Get the property
            property = Property.query.get(property_id)
            
            # If adding a non-owner contact, check if property already has an owner
            if relationship_type != 'owner' and not property.get_owner():
                flash(f'Property {property.unit_number} must have an owner assigned before adding other contacts', 'danger')
                return redirect(url_for('contacts'))
            
            # Check if this relationship already exists
            existing = ContactProperty.query.filter_by(
                contact_id=contact_id,
                property_id=property_id,
                relationship_type=relationship_type
            ).first()
            
            if existing:
                flash('This relationship already exists', 'warning')
                return redirect(url_for('contacts'))
            
            # Create new relationship
            new_assoc = ContactProperty(
                contact_id=contact_id,
                property_id=property_id,
                relationship_type=relationship_type
            )
            db.session.add(new_assoc)
            db.session.commit()
            
            contact = Contact.query.get(contact_id)
            property = Property.query.get(property_id)
            
            flash(f'Successfully assigned {contact.name} as {relationship_type} of {property.unit_number}', 'success')
            return redirect(url_for('contacts'))
            
        elif action == 'remove_assignment':
            # Remove contact from property
            contact_id = request.form.get('contact_id')
            property_id = request.form.get('property_id')
            relationship_type = request.form.get('relationship_type')
            
            assoc = ContactProperty.query.filter_by(
                contact_id=contact_id,
                property_id=property_id,
                relationship_type=relationship_type
            ).first()
            
            if assoc:
                db.session.delete(assoc)
                db.session.commit()
                
                contact = Contact.query.get(contact_id)
                property = Property.query.get(property_id)
                
                flash(f'Successfully removed {contact.name} as {relationship_type} of {property.unit_number}', 'success')
            
            return redirect(url_for('contacts'))
    
    return render_template('contacts.html', contacts=contacts, properties=properties, property_contacts=property_contacts)

@app.route('/api/contacts')
def get_contacts():
    """API endpoint to get all contacts data."""
    contacts = Contact.query.all()
    contacts_data = []
    
    for contact in contacts:
        owned_properties = [p.unit_number for p in contact.owned_properties]
        managed_properties = [p.unit_number for p in contact.managed_properties]
        
        contacts_data.append({
            'id': contact.id,
            'name': contact.name,
            'email': contact.email,
            'phone': contact.phone,
            'is_owner': contact.is_owner,
            'owned_properties': owned_properties,
            'managed_properties': managed_properties,
            'notes': contact.notes
        })
    
    return jsonify(contacts_data)

@app.route('/api/contacts/<int:contact_id>')
def get_contact(contact_id):
    """API endpoint to get a specific contact by ID."""
    contact = Contact.query.get_or_404(contact_id)
    
    owned_properties = [p.unit_number for p in contact.owned_properties]
    managed_properties = [p.unit_number for p in contact.managed_properties]
    
    return jsonify({
        'id': contact.id,
        'name': contact.name,
        'email': contact.email,
        'phone': contact.phone,
        'is_owner': contact.is_owner,
        'notes': contact.notes,
        'owned_properties': owned_properties,
        'managed_properties': managed_properties
    })

@app.route('/api/properties/<int:property_id>/contacts')
def get_property_contacts(property_id):
    """API endpoint to get contacts for a specific property."""
    property = Property.query.get_or_404(property_id)
    
    contacts_data = []
    for assoc in property.contact_associations:
        contacts_data.append({
            'contact_id': assoc.contact_id,
            'name': assoc.contact.name,
            'relationship_type': assoc.relationship_type,
            'email': assoc.contact.email,
            'phone': assoc.contact.phone
        })
    
    return jsonify(contacts_data)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
