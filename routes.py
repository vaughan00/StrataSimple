import os
import pandas as pd
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, jsonify
from werkzeug.utils import secure_filename
from io import StringIO

from app import app, db
from models import Property, Payment, Fee, BillingPeriod
from utils import process_csv, match_payments_to_properties

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
        
        properties_data.append({
            'id': prop.id,
            'unit_number': prop.unit_number,
            'owner_name': prop.owner_name,
            'balance': prop.balance,
            'unpaid_fees': unpaid_fees,
            'total_payments': total_payments
        })
    
    return jsonify(properties_data)

@app.route('/reconciliation', methods=['GET', 'POST'])
def reconciliation():
    """Page for CSV upload and reconciliation."""
    if request.method == 'POST':
        # Check if file part exists
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if file is empty
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        # Check file type
        if file and file.filename.endswith('.csv'):
            # Read CSV content
            content = file.read().decode('utf-8')
            
            try:
                # Process CSV data
                payments = process_csv(content)
                
                # Match payments to properties
                matched, unmatched = match_payments_to_properties(payments)
                
                # Save matched payments to database
                for payment in matched:
                    # Create new payment record
                    new_payment = Payment(
                        property_id=payment['property_id'],
                        amount=payment['amount'],
                        date=payment['date'],
                        description=payment['description'],
                        reference=payment['reference'],
                        reconciled=True
                    )
                    db.session.add(new_payment)
                    
                    # Update property balance
                    property = Property.query.get(payment['property_id'])
                    if property:
                        property.balance += payment['amount']
                
                db.session.commit()
                
                flash(f'Successfully reconciled {len(matched)} payments. {len(unmatched)} payments could not be matched.', 'success')
                
                return render_template('reconciliation.html', 
                                      matched_payments=matched, 
                                      unmatched_payments=unmatched)
            
            except Exception as e:
                flash(f'Error processing CSV: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Only CSV files are allowed', 'danger')
            return redirect(request.url)
    
    # GET request
    return render_template('reconciliation.html', matched_payments=None, unmatched_payments=None)

@app.route('/fees', methods=['GET', 'POST'])
def fees():
    """Page for raising new strata fees."""
    properties = Property.query.all()
    periods = BillingPeriod.query.order_by(BillingPeriod.start_date.desc()).all()
    
    if request.method == 'POST':
        # Create new billing period
        period_name = request.form.get('period_name')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        total_amount = float(request.form.get('total_amount'))
        description = request.form.get('description')
        
        new_period = BillingPeriod(
            name=period_name,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            description=description
        )
        db.session.add(new_period)
        db.session.commit()
        
        # Calculate and create fees for all properties
        total_entitlement = sum(prop.entitlement for prop in properties)
        
        for prop in properties:
            # Calculate fee amount based on property entitlement
            fee_amount = (prop.entitlement / total_entitlement) * total_amount
            
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
        fees_data.append({
            'id': fee.id,
            'unit_number': property.unit_number,
            'owner_name': property.owner_name,
            'amount': fee.amount,
            'paid': fee.paid
        })
    
    return jsonify(fees_data)

@app.route('/api/mark_fee_paid/<int:fee_id>', methods=['POST'])
def mark_fee_paid(fee_id):
    """API endpoint to mark a fee as paid."""
    fee = Fee.query.get_or_404(fee_id)
    fee.paid = True
    db.session.commit()
    
    return jsonify({'success': True})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
