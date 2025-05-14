import os
import pandas as pd
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, request, flash, jsonify, session, abort, send_from_directory
from werkzeug.utils import secure_filename
from io import StringIO

from app import app, db
from models import Property, Payment, Fee, BillingPeriod, Contact, ContactProperty, ActivityLog, Expense, StrataSettings, User
from utils import process_csv, analyze_payments, log_activity, reconcile_expenses
import email_service
from auth import login_required, require_role

@app.route('/')
@login_required
def index():
    """Main dashboard showing financial status of all properties."""
    today = datetime.now()
    
    # Get user role from session
    user_role = session.get('user_role')
    user_property_id = None
    
    # If user is an owner, restrict view to their property only
    if user_role == 'owner':
        user = User.query.get(session.get('user_id'))
        if user and user.property_id:
            user_property_id = user.property_id
            properties = Property.query.filter_by(id=user_property_id).all()
            total_balance = sum(prop.balance for prop in properties)
            
            # Calculate total unpaid fees for this property only
            total_fees = db.session.query(db.func.sum(Fee.amount))\
                .filter_by(paid=False, property_id=user_property_id).scalar() or 0
            
            # Calculate total payments for this property only
            total_paid = db.session.query(db.func.sum(Payment.amount))\
                .filter_by(property_id=user_property_id).scalar() or 0
            
            # Calculate fees due now for this property only
            today_date_only = today.replace(hour=0, minute=0, second=0, microsecond=0)
            due_now = db.session.query(db.func.sum(Fee.amount - Fee.paid_amount))\
                .filter(Fee.paid == False, 
                       Fee.property_id == user_property_id,
                       Fee.due_date <= today_date_only).scalar() or 0
            
            # Get recent payments, fees for this property only
            recent_payments = Payment.query.filter(
                Payment.amount > 0, 
                Payment.property_id == user_property_id
            ).order_by(Payment.date.desc()).limit(5).all()
            
            recent_fees = Fee.query.filter_by(
                property_id=user_property_id
            ).order_by(Fee.date.desc()).limit(5).all()
            
            # For owners, don't show expenses
            recent_expenses = []
            total_unpaid_expenses = 0
        else:
            # Fallback if user has no property
            flash('Your account is not properly linked to a property. Please contact the administrator.', 'warning')
            return redirect(url_for('logout'))
    else:
        # For admin and committee users, show all properties
        properties = Property.query.all()
        total_balance = sum(prop.balance for prop in properties)
        
        # Calculate total unpaid fees
        total_fees = db.session.query(db.func.sum(Fee.amount)).filter_by(paid=False).scalar() or 0
        
        # Calculate total payments
        total_paid = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
        
        # Calculate fees due now (where due_date <= today)
        today_date_only = today.replace(hour=0, minute=0, second=0, microsecond=0)
        due_now = db.session.query(db.func.sum(Fee.amount - Fee.paid_amount)) \
                  .filter(Fee.paid == False) \
                  .filter(Fee.due_date <= today_date_only) \
                  .scalar() or 0
        
        # Get recent payments, fees, and expenses
        recent_payments = Payment.query.filter(Payment.amount > 0).order_by(Payment.date.desc()).limit(5).all()
        recent_fees = Fee.query.order_by(Fee.date.desc()).limit(5).all()
        recent_expenses = Expense.query.order_by(Expense.due_date.desc()).limit(5).all()
        
        # Calculate total unpaid expenses
        unpaid_expenses = Expense.query.filter(Expense.paid == False).all()
        total_unpaid_expenses = sum(expense.amount for expense in unpaid_expenses)
    
    # Print debugging information
    print(f"TODAY: {today}, TODAY_DATE_ONLY: {today_date_only if 'today_date_only' in locals() else 'N/A'}")
    if user_role != 'owner' or (user_role == 'owner' and user_property_id):
        overdue_fees = Fee.query.filter(
            Fee.paid == False, 
            Fee.due_date <= today_date_only if 'today_date_only' in locals() else today
        )
        
        if user_role == 'owner':
            overdue_fees = overdue_fees.filter_by(property_id=user_property_id)
            
        overdue_fees = overdue_fees.all()
        print(f"OVERDUE FEES: {len(overdue_fees)} fees are overdue")
        for fee in overdue_fees:
            print(f"  Fee ID: {fee.id}, Due date: {fee.due_date}, Amount: {fee.amount}, Property: {fee.property_id}")
    
    # Debug info for fees
    if 'recent_fees' in locals() and recent_fees:
        print("RECENT FEES INFO:")
        for fee in recent_fees:
            payment_total = sum(payment.amount for payment in fee.payments) if hasattr(fee, 'payments') and fee.payments else 0
            print(f"  Fee ID: {fee.id}, Amount: {fee.amount}, Paid status: {fee.paid}, Payments: {payment_total}")
    
    # Debug each property's due now amount
    if 'properties' in locals() and properties:
        print("\nPROPERTY DUE NOW AMOUNTS:")
        for prop in properties:
            due_now_prop = prop.get_due_now_amount(today)
            if due_now_prop > 0:
                print(f"  Property {prop.id} (Unit {prop.unit_number}): Due Now = ${due_now_prop:.2f}")
                # List overdue fees
                for fee in prop.fees:
                    if not fee.paid and fee.is_overdue(today):
                        print(f"    Fee ID: {fee.id}, Amount: ${fee.amount:.2f}, Paid Amount: ${fee.paid_amount:.2f}, Remaining: ${fee.remaining_amount:.2f}, Due Date: {fee.due_date.strftime('%Y-%m-%d')}")
    
    # Debug expenses (only for admin/committee)
    if user_role != 'owner' and 'recent_expenses' in locals() and recent_expenses:
        print("\nRECENT EXPENSES INFO:")
        for expense in recent_expenses:
            print(f"  Expense ID: {expense.id}, Name: {expense.name}, Amount: ${expense.amount:.2f}, Paid: {expense.paid}, Due Date: {expense.due_date.strftime('%Y-%m-%d')}")
        
        if 'total_unpaid_expenses' in locals():
            print(f"TOTAL UNPAID EXPENSES: ${total_unpaid_expenses:.2f}")
    
    return render_template('dashboard.html', 
                           properties=properties, 
                           total_balance=total_balance,
                           total_fees=total_fees,
                           total_paid=total_paid,
                           due_now=due_now,
                           total_unpaid_expenses=total_unpaid_expenses,
                           today=today,
                           recent_payments=recent_payments,
                           recent_fees=recent_fees,
                           recent_expenses=recent_expenses,
                           user_role=user_role)

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
@login_required
@require_role('admin')
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
                    
                    # Also analyze for expense matching
                    analyzed_payments = reconcile_expenses(analyzed_payments)
                    
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
                                'suggested_fee_id': payment.get('suggested_fee', {}).get('id') if payment.get('suggested_fee') else None,
                                'suggested_expense_id': payment.get('suggested_expense', {}).get('id') if payment.get('suggested_expense') else None
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
                                          unpaid_fees=Fee.query.filter_by(paid=False).all(),
                                          unpaid_expenses=Expense.query.filter_by(paid=False).all())
                
                except Exception as e:
                    flash(f'Error processing CSV: {str(e)}', 'danger')
                    return redirect(request.url)
            else:
                flash('Only CSV files are allowed', 'danger')
                return redirect(request.url)
                
        # Handle transaction confirmation form
        elif request.form.get('action') == 'confirm_matches':
            # Process the transactions
            transaction_ids = request.form.getlist('transaction_id')
            
            # These lists will be populated dynamically for each transaction
            property_ids = []
            fee_ids = []
            expense_ids = []
            
            # Get all the properties and fees for each transaction
            for t_id in transaction_ids:
                property_key = f'property_{t_id}'
                fee_key = f'fee_{t_id}'
                expense_key = f'expense_{t_id}'
                
                property_id = request.form.get(property_key, '')
                fee_id = request.form.get(fee_key, '')
                expense_id = request.form.get(expense_key, '')
                
                # Add to appropriate lists
                property_ids.append(property_id)
                fee_ids.append(fee_id)
                expense_ids.append(expense_id)
                
            # Debug the collected IDs
            print(f"Processing {len(transaction_ids)} transactions")
            print(f"Property IDs: {property_ids}")
            print(f"Fee IDs: {fee_ids}")
            print(f"Expense IDs: {expense_ids}")
            
            confirmed_count = 0
            excluded_count = 0
            
            for i, transaction_id in enumerate(transaction_ids):
                # Check if this transaction is to be confirmed or excluded
                action_key = f'action_{transaction_id}'
                action = request.form.get(action_key)
                
                # Skip if excluded
                if action == 'exclude':
                    excluded_count += 1
                    continue
                
                # Skip if not confirmed
                if action != 'confirm':
                    continue
                
                # Get form data
                property_id = property_ids[i] if i < len(property_ids) and property_ids[i] else None
                fee_id = fee_ids[i] if i < len(fee_ids) and fee_ids[i] and fee_ids[i] != "null" else None
                expense_id = expense_ids[i] if i < len(expense_ids) and expense_ids[i] and expense_ids[i] != "null" else None
                
                # Debug info
                print(f"Transaction {i}: Property ID={property_id}, Fee ID={fee_id}, Expense ID={expense_id}")
                
                # Get the amount directly from indexed hidden form field
                try:
                    # First try to get the indexed amount
                    amount_key = f'amount_{i}'
                    amount_value = request.form.get(amount_key)
                    
                    if amount_value:
                        # If we have the indexed amount value, use it
                        amount = float(amount_value)
                        print(f"Found amount {amount} from indexed field {amount_key}")
                    else:
                        # Try second indexed field format
                        transaction_id_key = f'transaction_id_{i}'
                        transaction_id_index = request.form.get(transaction_id_key)
                        
                        if transaction_id_index:
                            amount_key = f'amount_{transaction_id_index}'
                            amount_value = request.form.get(amount_key)
                            
                            if amount_value:
                                amount = float(amount_value)
                                print(f"Found amount {amount} from transaction indexed field {amount_key}")
                            else:
                                # Fallback to list data
                                amount_list = request.form.getlist('amount')
                                if i < len(amount_list):
                                    amount = float(amount_list[i])
                                    print(f"Found amount {amount} from amount list position {i}")
                                else:
                                    # Final fallback to session data
                                    amount = 0
                                    # Print session keys for debugging
                                    print(f"DEBUG: Session keys: {list(session.keys())}")
                                    session_transactions = session.get('transactions', [])
                                    print(f"DEBUG: Transaction IDs in session: {[tx.get('transaction_id') for tx in session_transactions]}")
                                    
                                    for tx in session_transactions:
                                        if tx.get('transaction_id') == transaction_id:
                                            amount = float(tx.get('amount', 0))
                                            print(f"Found transaction {transaction_id} with amount {amount} from session")
                                            break
                                    
                                    if amount == 0:
                                        print(f"WARNING: Could not find amount for transaction ID {transaction_id}")
                        else:
                            amount = 0
                            print(f"WARNING: Could not find transaction ID for index {i}")
                except (ValueError, IndexError) as e:
                    print(f"Error getting amount for transaction {transaction_id} at index {i}: {str(e)}")
                    amount = 0
                
                # Check if this is an expense - either by amount, transaction ID flag, or index flag
                is_expense = False
                
                # Most reliable: check transaction ID flag
                is_expense_tx_key = f'is_expense_{transaction_id}'
                is_expense_tx_flag = request.form.get(is_expense_tx_key)
                if is_expense_tx_flag and is_expense_tx_flag.lower() == 'true':
                    is_expense = True
                    print(f"Transaction {i} marked as expense by transaction ID flag")
                else:
                    # Second, check index flag
                    is_expense_key = f'is_expense_{i}'
                    is_expense_flag = request.form.get(is_expense_key)
                    if is_expense_flag and is_expense_flag.lower() == 'true':
                        is_expense = True
                        print(f"Transaction {i} marked as expense by index flag")
                    else:
                        # Fallback to amount check
                        is_expense = amount < 0
                        if is_expense:
                            print(f"Transaction {i} identified as expense by negative amount: {amount}")
                
                # Debug expense ID
                print(f"Transaction {i}: Amount={amount}, Is Expense={is_expense}, Expense ID={expense_id}")
                
                # For outgoing payments/expenses
                if is_expense and expense_id:
                    # Try to get expense amount from dedicated field first
                    expense_amount_key = f'expense_amount_{transaction_id}'
                    expense_amount_str = request.form.get(expense_amount_key)
                    if expense_amount_str:
                        try:
                            actual_amount = float(expense_amount_str)
                            print(f"Found expense amount ${actual_amount} from dedicated field")
                        except (ValueError, TypeError):
                            actual_amount = abs(amount)
                    else:
                        # Take abs of negative amount
                        actual_amount = abs(amount)
                    
                    # Get transaction date - use the date from the transaction or today if not available
                    date_str = request.form.get(f'date_{i}')
                    if date_str:
                        try:
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                        except ValueError:
                            date = datetime.now()
                    else:
                        date = datetime.now()
                    
                    # Get transaction reference
                    reference = request.form.get(f'reference_{i}', '')
                    
                    # Mark the expense as paid
                    expense = Expense.query.get(expense_id)
                    if expense:
                        print(f"Found expense to mark as paid: ID={expense.id}, Name={expense.name}, Amount=${expense.amount}")
                        print(f"Transaction date: {date}, amount: ${actual_amount}, reference: {reference}, ID: {transaction_id}")
                        
                        # CRITICAL: Set the paid status
                        expense.paid = True
                        expense.paid_date = datetime.now()
                        expense.matched_transaction_id = transaction_id
                        
                        # Log the activity
                        log_activity(
                            event_type='expense_paid',
                            description=f'Expense "{expense.name}" of ${expense.amount} marked as paid through bank reconciliation (Transaction amount: ${actual_amount})',
                            related_type='Expense',
                            related_id=expense.id
                        )
                        
                        # Create a new payment record with negative amount to track the expense
                        new_payment = Payment(
                            property_id=None,  # No property associated with expense
                            fee_id=None,       # No fee associated with expense
                            amount=-actual_amount,  # Use negative amount to indicate outgoing payment
                            date=date,
                            description=f"Payment for expense: {expense.name}",
                            reference=reference,
                            transaction_id=transaction_id,
                            reconciled=True,
                            confirmed=True
                        )
                        db.session.add(new_payment)
                        
                        # Commit the transaction immediately to ensure it's saved
                        db.session.commit()
                        
                        # Debug info
                        print(f"Created payment record for expense: ID={new_payment.id}, Amount=${new_payment.amount}")
                        
                        confirmed_count += 1
                        
                        # Verify the expense was updated
                        updated_expense = Expense.query.get(expense_id)
                        print(f"VERIFICATION: Expense ID={updated_expense.id}, Paid status is now: {updated_expense.paid}")
                        
                        # For debugging
                        all_expenses = Expense.query.all()
                        print(f"After update, {len(all_expenses)} expenses in database")
                        for exp in all_expenses:
                            print(f"  Expense ID={exp.id}, Name={exp.name}, Amount=${exp.amount}, Paid={exp.paid}, " +
                                  f"Paid Date={exp.paid_date}, Matched Transaction={exp.matched_transaction_id}")
                        
                        # Skip the rest of the processing for this negative transaction
                        continue
                    else:
                        print(f"ERROR: Could not find expense with ID {expense_id}")

                # For incoming payments - skip if no property selected
                if not is_expense and not property_id:
                    continue
                
                # Get transaction details from form
                try:
                    date_list = request.form.getlist('date')
                    if i < len(date_list):
                        date_str = date_list[i]
                    else:
                        # Try to get from session data if available
                        session_transactions = session.get('transactions', [])
                        if i < len(session_transactions):
                            date_str = session_transactions[i]['date']
                        else:
                            # Default to today if we can't find it
                            date_str = datetime.now().strftime('%Y-%m-%d')
                            print(f"WARNING: Could not find date for transaction {i}")
                    
                    # Amount was already parsed above
                    description_list = request.form.getlist('description')
                    description = description_list[i] if i < len(description_list) else "Unknown"
                    
                    reference_list = request.form.getlist('reference')
                    reference = reference_list[i] if i < len(reference_list) else "Unknown"
                    
                    date = datetime.strptime(date_str, '%Y-%m-%d')
                except (ValueError, IndexError) as e:
                    print(f"Error processing date/description/reference for transaction {i}: {str(e)}")
                    date = datetime.now()
                
                # Create payment record for incoming payments only
                # We only need this for positive amounts - negative amounts update the expense record
                if not is_expense:
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
                
                # Update property balance - only for income transactions 
                if not is_expense and property_id:
                    property = Property.query.get(property_id)
                    if property:
                        property.balance += amount
                    
                    # Log the payment activity
                    fee_info = ""
                    if fee_id:
                        fee = Fee.query.get(fee_id)
                        if fee:
                            fee.paid = True
                            fee_info = f" for {fee.description}"
                    
                    # Log the activity
                    log_activity(
                        event_type='payment_reconciled',
                        description=f'Payment of ${amount} reconciled to property {property.unit_number}{fee_info}',
                        related_type='Payment',
                        related_id=new_payment.id
                    )
                
                confirmed_count += 1
            
            db.session.commit()
            
            flash(f'Successfully confirmed {confirmed_count} payments and excluded {excluded_count} transactions.', 'success')
            return redirect(url_for('index'))
    
    # GET request - show previously confirmed payments
    # Include both incoming payments (positive amounts) and outgoing expense payments (negative amounts)
    recently_confirmed = Payment.query.filter_by(confirmed=True).order_by(Payment.created_at.desc()).limit(10).all()
    
    return render_template('reconciliation.html', 
                          transactions=None,
                          properties=Property.query.all(),
                          unpaid_fees=Fee.query.filter_by(paid=False).all(), 
                          recently_confirmed=recently_confirmed)

@app.route('/fees', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def fees():
    """Page for raising new strata fees."""
    properties = Property.query.all()
    periods = BillingPeriod.query.order_by(BillingPeriod.start_date.desc()).all()
    
    if request.method == 'POST':
        # Get fee type and amount
        fee_type = request.form.get('fee_type')
        fee_per_unit = float(request.form.get('fee_per_unit'))
        description = request.form.get('description', '')
        
        # Determine which properties to apply fees to
        if fee_type == 'billing_period':
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
            
            # Get due date (30 days from start date by default)
            billing_due_date = datetime.strptime(request.form.get('billing_due_date'), '%Y-%m-%d')
            fee_due_date = billing_due_date
            
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
            target_properties = properties
            fee_description = f"Strata fee for {period_name}"
            fee_date = start_date
            fee_period = period_name
        else:
            # For opening_balance and ad_hoc fees, use selected properties
            selected_property_ids = request.form.getlist('selected_properties')
            
            if not selected_property_ids:
                flash('Please select at least one property to apply the fee to.', 'warning')
                return redirect(url_for('fees'))
            
            target_properties = Property.query.filter(Property.id.in_(selected_property_ids)).all()
            
            # Set appropriate description and period
            if fee_type == 'opening_balance':
                fee_description = "Opening balance"
                fee_period = "Opening Balance"
            else:  # ad_hoc
                fee_description = description if description else "Ad hoc fee"
                fee_period = f"Ad Hoc {datetime.now().strftime('%Y-%m-%d')}"
                
            # Get manual due date for non-billing period fees
            fee_due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d')
            
            fee_date = datetime.now()
        
        # Create fees for target properties
        for prop in target_properties:
            # Skip properties without owners
            if not prop.get_owner():
                continue
                
            new_fee = Fee(
                property_id=prop.id,
                amount=fee_per_unit,
                date=fee_date,
                due_date=fee_due_date,
                description=fee_description,
                period=fee_period,
                fee_type=fee_type,
                paid=False,
                paid_amount=0.0
            )
            db.session.add(new_fee)
            
            # Update property balance
            prop.balance -= fee_per_unit
            
            # Log the activity
            log_activity(
                event_type=f'fee_{fee_type}_created',
                description=f'{fee_description} for ${fee_per_unit} added to property {prop.unit_number}',
                related_type='Fee',
                related_id=new_fee.id
            )
        
        db.session.commit()
        
        if fee_type == 'billing_period':
            flash(f'Successfully created {period_name} fees for all properties', 'success')
        elif fee_type == 'opening_balance':
            flash(f'Successfully added opening balances to {len(target_properties)} properties', 'success')
        else:
            flash(f'Successfully added ad hoc fees to {len(target_properties)} properties', 'success')
            
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
            'paid_amount': fee.paid_amount if hasattr(fee, 'paid_amount') else 0.0,
            'fee_type': fee.fee_type if hasattr(fee, 'fee_type') else 'billing_period',  # Default to billing_period for existing fees
            'date': fee.date.strftime('%Y-%m-%d'),
            'due_date': fee.due_date.strftime('%Y-%m-%d') if hasattr(fee, 'due_date') and fee.due_date else None,
            'payments': [{'amount': payment.amount, 'date': payment.date.strftime('%Y-%m-%d')} for payment in payments]
        })
    
    return jsonify(fees_data)

@app.route('/api/mark_fee_paid/<int:fee_id>', methods=['POST'])
def mark_fee_paid(fee_id):
    """API endpoint to mark a fee as paid."""
    fee = Fee.query.get_or_404(fee_id)
    
    # Calculate total payments for this fee
    total_payments = sum(payment.amount for payment in fee.payments)
    
    # Update the paid_amount field
    fee.paid_amount = total_payments
    
    # Mark as paid if the total payments cover the fee amount
    if total_payments >= fee.amount:
        fee.paid = True
    else:
        # If partial payment, mark as not fully paid
        fee.paid = False
    
    db.session.commit()
    
    # Get property information for the log
    property = Property.query.get(fee.property_id)
    status = "fully paid" if fee.paid else "partially paid"
    
    # Log the activity
    log_activity(
        event_type='fee_payment_updated',
        description=f'Fee for property {property.unit_number} marked as {status} (${fee.paid_amount}/{fee.amount})',
        related_type='Fee',
        related_id=fee.id
    )
    
    return jsonify({
        'success': True, 
        'paid': fee.paid, 
        'paid_amount': fee.paid_amount,
        'amount': fee.amount
    })

# Setup routes
@app.route('/setup', methods=['GET', 'POST'])
@login_required
@require_role('admin', 'committee')
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
            
            # Log the activity
            log_activity(
                event_type='property_added',
                description=f'Property {unit_number} was added to the system',
                related_type='Property',
                related_id=new_property.id
            )
            
            flash(f'Property {unit_number} added successfully', 'success')
            return redirect(url_for('setup'))
            
        elif action == 'edit_property':
            # Edit existing property
            property_id = request.form.get('property_id')
            property = Property.query.get_or_404(property_id)
            
            old_unit_number = property.unit_number
            property.unit_number = request.form.get('unit_number')
            property.description = request.form.get('description')
            # Entitlement fixed at 1.0
            
            db.session.commit()
            
            # Log the activity
            log_activity(
                event_type='property_updated',
                description=f'Property {old_unit_number} was updated to {property.unit_number}',
                related_type='Property',
                related_id=property.id
            )
            
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
            
            unit_number = property.unit_number
            property_id = property.id
            
            db.session.delete(property)
            db.session.commit()
            
            # Log the activity
            log_activity(
                event_type='property_deleted',
                description=f'Property {unit_number} was deleted from the system',
                related_type='Property',
                related_id=property_id
            )
            
            flash(f'Property {unit_number} deleted successfully', 'success')
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
@login_required
def contacts():
    """Page for managing contacts and owners."""
    user_role = session.get('user_role')
    is_admin_or_committee = user_role in ['admin', 'committee']
    
    # If user is an owner, restrict what they can see
    if user_role == 'owner':
        user = User.query.get(session.get('user_id'))
        if user and user.property_id:
            # Get contacts that are either emergency contacts or related to this property
            property = Property.query.get(user.property_id)
            if not property:
                flash('Your account is not properly linked to a property. Please contact the administrator.', 'warning')
                return redirect(url_for('index'))
            
            # Get all emergency contacts + contacts for this property
            property_contacts_ids = [assoc.contact_id for assoc in property.contact_associations]
            contacts = Contact.query.filter(
                db.or_(
                    Contact.emergency_contact == True,
                    Contact.id.in_(property_contacts_ids)
                )
            ).all()
            
            # Only show this property
            properties = [property]
            
            # Pre-fetch property contacts
            property_contacts = {property.id: []}
            for assoc in property.contact_associations:
                property_contacts[property.id].append({
                    'contact_id': assoc.contact_id,
                    'name': assoc.contact.name,
                    'relationship_type': assoc.relationship_type,
                    'email': assoc.contact.email,
                    'phone': assoc.contact.phone
                })
        else:
            flash('Your account is not properly linked to a property. Please contact the administrator.', 'warning')
            return redirect(url_for('index'))
    else:
        # Admin and committee users can see all contacts and properties
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
            emergency_contact = request.form.get('emergency_contact') == 'on'
            notes = request.form.get('notes')
            
            new_contact = Contact(
                name=name,
                email=email,
                phone=phone,
                is_owner=is_owner,
                emergency_contact=emergency_contact,
                notes=notes
            )
            db.session.add(new_contact)
            db.session.commit()
            
            # Log the activity
            log_activity(
                event_type='contact_added',
                description=f'Contact {name} was added to the system',
                related_type='Contact',
                related_id=new_contact.id
            )
            
            flash(f'Contact {name} added successfully', 'success')
            return redirect(url_for('contacts'))
            
        elif action == 'edit_contact':
            # Edit existing contact
            contact_id = request.form.get('contact_id')
            contact = Contact.query.get_or_404(contact_id)
            
            # Check permission for owners - they can only edit their own contacts
            if session.get('user_role') == 'owner':
                user = User.query.get(session.get('user_id'))
                if user and user.property_id:
                    property = Property.query.get(user.property_id)
                    if property:
                        property_contact_ids = [assoc.contact_id for assoc in property.contact_associations]
                        if int(contact_id) not in property_contact_ids:
                            flash('You do not have permission to edit this contact.', 'danger')
                            return redirect(url_for('contacts'))
            
            contact.name = request.form.get('name')
            contact.email = request.form.get('email')
            contact.phone = request.form.get('phone')
            contact.is_owner = request.form.get('is_owner') == 'on'
            contact.emergency_contact = request.form.get('emergency_contact') == 'on'
            contact.notes = request.form.get('notes')
            
            db.session.commit()
            
            # Log the activity
            log_activity(
                event_type='contact_updated',
                description=f'Contact {contact.name} was updated',
                related_type='Contact',
                related_id=contact.id
            )
            
            flash(f'Contact {contact.name} updated successfully', 'success')
            return redirect(url_for('contacts'))
            
        elif action == 'delete_contact':
            # Delete contact
            contact_id = request.form.get('contact_id')
            contact = Contact.query.get_or_404(contact_id)
            
            # Delete all property associations
            for assoc in contact.property_associations:
                db.session.delete(assoc)
            
            contact_name = contact.name
            contact_id = contact.id
            
            db.session.delete(contact)
            db.session.commit()
            
            # Log the activity
            log_activity(
                event_type='contact_deleted',
                description=f'Contact {contact_name} was deleted from the system',
                related_type='Contact',
                related_id=contact_id
            )
            
            flash(f'Contact {contact_name} deleted successfully', 'success')
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
            
            # Log the activity
            log_activity(
                event_type='property_contact_assigned',
                description=f'{contact.name} was assigned as {relationship_type} of property {property.unit_number}',
                related_type='Property',
                related_id=property.id
            )
            
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
    # Check if user is owner - restrict to only their contacts and emergency contacts
    if session.get('user_role') == 'owner':
        user = User.query.get(session.get('user_id'))
        if user and user.property_id:
            property = Property.query.get(user.property_id)
            if property:
                # Get contact IDs related to this property
                property_contact_ids = [assoc.contact_id for assoc in property.contact_associations]
                # Filter contacts to only include those related to this property or emergency contacts
                contacts = Contact.query.filter(
                    db.or_(
                        Contact.id.in_(property_contact_ids),
                        Contact.emergency_contact == True
                    )
                ).all()
            else:
                return jsonify([])
        else:
            return jsonify([])
    else:
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
            'emergency_contact': contact.emergency_contact,
            'owned_properties': owned_properties,
            'managed_properties': managed_properties,
            'notes': contact.notes
        })
    
    return jsonify(contacts_data)

@app.route('/api/contacts/<int:contact_id>')
def get_contact(contact_id):
    """API endpoint to get a specific contact by ID."""
    contact = Contact.query.get_or_404(contact_id)
    
    # Check permissions for owners - they can only view their own contacts
    # or emergency contacts
    if session.get('user_role') == 'owner':
        user = User.query.get(session.get('user_id'))
        if user and user.property_id:
            property = Property.query.get(user.property_id)
            if property:
                # Get contact IDs related to this property
                property_contact_ids = [assoc.contact_id for assoc in property.contact_associations]
                if contact_id not in property_contact_ids and not contact.emergency_contact:
                    return jsonify({"error": "Access denied"}), 403
    
    owned_properties = [p.unit_number for p in contact.owned_properties]
    managed_properties = [p.unit_number for p in contact.managed_properties]
    
    return jsonify({
        'id': contact.id,
        'name': contact.name,
        'email': contact.email,
        'phone': contact.phone,
        'is_owner': contact.is_owner,
        'emergency_contact': contact.emergency_contact,
        'notes': contact.notes,
        'owned_properties': owned_properties,
        'managed_properties': managed_properties
    })

@app.route('/api/properties/<int:property_id>/contacts')
def get_property_contacts(property_id):
    """API endpoint to get contacts for a specific property."""
    property = Property.query.get_or_404(property_id)
    
    # Check permissions for owners - they can only view their own property contacts
    if session.get('user_role') == 'owner':
        user = User.query.get(session.get('user_id'))
        if user and user.property_id and user.property_id != property_id:
            return jsonify({"error": "Access denied"}), 403
    
    contacts_data = []
    for assoc in property.contact_associations:
        contacts_data.append({
            'contact_id': assoc.contact_id,
            'name': assoc.contact.name,
            'relationship_type': assoc.relationship_type,
            'email': assoc.contact.email,
            'phone': assoc.contact.phone,
            'emergency_contact': assoc.contact.emergency_contact
        })
    
    return jsonify(contacts_data)

# Property detail page
@app.route('/property/<int:property_id>')
@login_required
def property_detail(property_id):
    """Detailed view of a specific property with financial history."""
    today = datetime.now()
    property = Property.query.get_or_404(property_id)
    
    # Check permissions - owner can only see their own property
    user_role = session.get('user_role')
    user_id = session.get('user_id')
    
    if user_role == 'owner':
        user = User.query.get(user_id)
        if user and user.property_id != property_id:
            flash('You do not have permission to view this property.', 'danger')
            return redirect(url_for('index'))
    
    # Get financial data
    total_fees = sum(fee.amount for fee in property.fees)
    total_payments = sum(payment.amount for payment in property.payments)
    outstanding = total_fees - total_payments
    due_now = property.get_due_now_amount(today)
    
    # Get opening balance fee (if exists)
    opening_balance_fee = Fee.query.filter_by(
        property_id=property_id,
        fee_type='opening_balance'
    ).first()
    
    # Get recent fees and payments
    recent_fees = Fee.query.filter_by(property_id=property_id).order_by(Fee.date.desc()).all()
    recent_payments = Payment.query.filter_by(property_id=property_id).order_by(Payment.date.desc()).all()
    
    # Get owner and other contacts
    owner = property.get_owner()
    
    # If user is owner, only show emergency contacts and their own property contacts
    if session.get('user_role') == 'owner':
        contacts = [assoc.contact for assoc in property.contact_associations if
                   assoc.contact.emergency_contact or assoc.contact_id == owner.id]
    else:
        contacts = [assoc.contact for assoc in property.contact_associations]
    
    # Create timeline of activity
    timeline = []
    
    # Add fees to timeline
    for fee in property.fees:
        timeline.append({
            'date': fee.date,
            'type': 'fee',
            'description': f"Fee raised: {fee.description or fee.fee_type}",
            'amount': fee.amount,
            'item': fee
        })
    
    # Add payments to timeline
    for payment in property.payments:
        timeline.append({
            'date': payment.date,
            'type': 'payment',
            'description': f"Payment received: {payment.description or 'No description'}",
            'amount': payment.amount,
            'item': payment
        })
    
    # Sort timeline by date (most recent first)
    timeline.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('property_detail.html',
                          property=property,
                          total_fees=total_fees,
                          total_payments=total_payments,
                          outstanding=outstanding,
                          due_now=due_now,
                          opening_balance_fee=opening_balance_fee,
                          recent_fees=recent_fees,
                          recent_payments=recent_payments,
                          owner=owner,
                          contacts=contacts,
                          timeline=timeline,
                          today=today)
                          
# Activity log page
@app.route('/activity')
@login_required
@require_role('admin', 'committee')
def activity():
    """Page showing system activity logs with filtering."""
    # Get filter parameters
    filter_type = request.args.get('event_type', '')
    filter_id = request.args.get('related_id', '')
    date_range = request.args.get('date_range', 'all')
    
    # Base query
    query = ActivityLog.query
    
    # Apply event type filter
    if filter_type:
        query = query.filter(ActivityLog.event_type.like(f'%{filter_type}%'))
    
    # Apply related object ID filter
    if filter_id and filter_id.isdigit():
        query = query.filter_by(related_object_id=int(filter_id))
    
    # Apply date range filter
    if date_range != 'all':
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if date_range == 'today':
            query = query.filter(ActivityLog.timestamp >= today)
        elif date_range == 'week':
            query = query.filter(ActivityLog.timestamp >= today - timedelta(days=7))
        elif date_range == 'month':
            query = query.filter(ActivityLog.timestamp >= today - timedelta(days=30))
    
    # Get logs in reverse chronological order
    logs = query.order_by(ActivityLog.timestamp.desc()).all()
    
    return render_template('activity.html', 
                          logs=logs,
                          filter_type=filter_type, 
                          filter_id=filter_id,
                          date_range=date_range)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
    
# Expenses Routes
@app.route('/expenses', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def expenses():
    """Page for managing strata expenses."""
    # POST request - create a new expense
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        amount = float(request.form.get('amount'))
        description = request.form.get('description')
        due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d')
        
        # Create a new expense record
        new_expense = Expense(
            name=name,
            amount=amount,
            description=description,
            due_date=due_date,
            paid=False
        )
        
        # Check if an invoice was uploaded
        if 'invoice' in request.files and request.files['invoice'].filename:
            invoice_file = request.files['invoice']
            
            # Generate a secure filename to prevent path traversal
            filename = secure_filename(invoice_file.filename)
            # Add timestamp to filename to prevent collisions
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            # Save the file
            filepath = os.path.join('static/uploads/invoices', filename)
            invoice_file.save(filepath)
            
            # Save the filename in the expense record
            new_expense.invoice_filename = filename
        
        # Save to database
        db.session.add(new_expense)
        db.session.commit()
        
        # Log the activity
        log_activity(
            event_type='expense_added',
            description=f'Added new expense: {name} (${amount:.2f})',
            related_type='Expense',
            related_id=new_expense.id
        )
        
        flash(f'Expense "{name}" has been added successfully.', 'success')
        return redirect(url_for('expenses'))
    
    # GET request - display expenses
    expenses = Expense.query.order_by(Expense.due_date.desc()).all()
    today = datetime.now()
    
    return render_template('expenses.html', expenses=expenses, today=today)

@app.route('/mark_expense_paid', methods=['POST'])
def mark_expense_paid():
    """Mark an expense as paid."""
    expense_id = request.form.get('expense_id')
    paid_date_str = request.form.get('paid_date')
    
    # Convert paid date string to datetime
    if paid_date_str:
        paid_date = datetime.strptime(paid_date_str, '%Y-%m-%d')
    else:
        paid_date = datetime.now()
    
    expense = Expense.query.get_or_404(expense_id)
    expense.paid = True
    expense.paid_date = paid_date
    
    db.session.commit()
    
    # Log the activity
    log_activity(
        event_type='expense_paid',
        description=f'Marked expense "{expense.name}" (${expense.amount:.2f}) as paid',
        related_type='Expense',
        related_id=expense.id
    )
    
    flash(f'Expense "{expense.name}" has been marked as paid.', 'success')
    return redirect(url_for('expenses'))

@app.route('/delete_expense', methods=['POST'])
def delete_expense():
    """Delete an expense."""
    expense_id = request.form.get('expense_id')
    expense = Expense.query.get_or_404(expense_id)
    
    # Store expense details before deletion
    expense_name = expense.name
    expense_amount = expense.amount
    
    # If there's an invoice, delete it
    if expense.invoice_filename:
        try:
            os.remove(os.path.join('static/uploads/invoices', expense.invoice_filename))
        except FileNotFoundError:
            # File might have been deleted or moved
            pass
    
    # Delete from database
    db.session.delete(expense)
    db.session.commit()
    
    # Log the deletion
    log_activity(
        event_type='expense_deleted',
        description=f'Deleted expense: {expense_name} (${expense_amount:.2f})'
    )
    
    flash(f'Expense "{expense_name}" has been deleted.', 'success')
    return redirect(url_for('expenses'))

@app.route('/view_invoice/<int:expense_id>')
def view_invoice(expense_id):
    """View an expense's invoice file."""
    expense = Expense.query.get_or_404(expense_id)
    
    if not expense.invoice_filename:
        flash('No invoice file found for this expense.', 'warning')
        return redirect(url_for('expenses'))
    
    # Return the file for inline display in the browser
    return send_from_directory(
        'static/uploads/invoices',
        expense.invoice_filename,
        as_attachment=False
    )

@app.route('/download_invoice/<int:expense_id>')
def download_invoice(expense_id):
    """Download an expense's invoice file."""
    expense = Expense.query.get_or_404(expense_id)
    
    if not expense.invoice_filename:
        flash('No invoice file found for this expense.', 'warning')
        return redirect(url_for('expenses'))
    
    # Return the file as an attachment for download
    return send_from_directory(
        'static/uploads/invoices',
        expense.invoice_filename,
        as_attachment=True
    )

#
# Email System Routes
#

@app.route('/email/test', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def test_email():
    """Page to test email functionality and configuration."""
    # Check if SMTP is configured
    is_configured = bool(email_service.SMTP_USERNAME and email_service.SMTP_PASSWORD)
    
    if request.method == 'POST':
        test_email = request.form.get('test_email')
        
        if test_email:
            # Try to send a test email
            success = email_service.send_email(
                test_email,
                "StrataHub Test Email",
                "This is a test email from StrataHub to verify the email configuration is working correctly.",
                html_content="""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <h2>StrataHub Test Email</h2>
                    <p>This is a test email from StrataHub to verify the email configuration is working correctly.</p>
                    <p>If you received this email, the email system is working properly!</p>
                    <hr>
                    <p><em>This is an automated test message.</em></p>
                </body>
                </html>
                """
            )
            
            if success:
                flash(f"Test email successfully sent to {test_email}!", "success")
                # Log activity
                log_activity(
                    event_type='email_test',
                    description=f'Test email sent to {test_email}',
                )
            else:
                flash(f"Failed to send test email. Check server logs for details.", "danger")
        
        return redirect(url_for('test_email'))
    
    # For GET requests, show the test page
    return render_template(
        'email_test.html',
        smtp_server=email_service.SMTP_SERVER,
        smtp_port=email_service.SMTP_PORT,
        smtp_username=email_service.SMTP_USERNAME,
        email_sender=email_service.EMAIL_SENDER,
        email_reply_to=email_service.EMAIL_REPLY_TO,
        is_configured=is_configured,
        email_templates=True  # For future template testing
    )

@app.route('/email/template/test', methods=['POST'])
def test_template():
    """Test sending an email using a specific template."""
    template_type = request.form.get('template_type')
    recipient_email = request.form.get('recipient_email')
    
    if not template_type or not recipient_email:
        flash("Both template type and recipient email are required.", "danger")
        return redirect(url_for('test_email'))
    
    # Find a sample item for the template
    success = False
    
    if template_type == 'fee_notification':
        # Get a sample fee
        fee = Fee.query.first()
        if fee and fee.property:
            # Create a temporary contact for testing
            temp_contact = Contact(name="Test Recipient", email=recipient_email)
            success = email_service.send_fee_notification(fee, temp_contact)
            
    elif template_type == 'payment_receipt':
        # Get a sample payment
        payment = Payment.query.filter(Payment.property_id.isnot(None)).first()
        if payment and payment.property:
            # Create a temporary contact for testing
            temp_contact = Contact(name="Test Recipient", email=recipient_email)
            success = email_service.send_payment_receipt(payment, temp_contact)
            
    elif template_type == 'overdue_reminder':
        # Get an overdue fee
        today = datetime.now()
        fee = Fee.query.filter(Fee.due_date < today, Fee.paid == False).first()
        if not fee:  # If no overdue fee, get any fee
            fee = Fee.query.filter(Fee.property_id.isnot(None)).first()
        
        if fee and fee.property:
            # Create a temporary contact for testing
            temp_contact = Contact(name="Test Recipient", email=recipient_email)
            success = email_service.send_overdue_reminder(fee, temp_contact)
            
    elif template_type == 'expense_notification':
        # Get a sample expense
        expense = Expense.query.first()
        if expense:
            success = email_service.send_expense_paid_notification(expense, [recipient_email])
            
    elif template_type == 'financial_summary':
        # Get properties for summary
        properties = Property.query.all()
        if properties:
            success = email_service.send_financial_summary(properties, [recipient_email], "Test Period")
    
    if success:
        flash(f"Test template email ({template_type}) sent successfully to {recipient_email}!", "success")
        # Log activity
        log_activity(
            event_type='email_template_test',
            description=f'Test {template_type} template email sent to {recipient_email}',
        )
    else:
        flash(f"Failed to send template email. Check server logs for details.", "danger")
    
    return redirect(url_for('test_email'))
#
# Strata Settings Routes
#

@app.route('/settings', methods=['GET', 'POST'])
@login_required
@require_role('admin')
def strata_settings():
    """Page for managing strata-wide settings."""
    # Get or create settings
    settings = StrataSettings.get_settings()
    
    if request.method == 'POST':
        # Update settings from form
        settings.strata_name = request.form.get('strata_name')
        settings.address = request.form.get('address')
        settings.admin_email = request.form.get('admin_email')
        settings.bank_account_name = request.form.get('bank_account_name')
        settings.bank_bsb = request.form.get('bank_bsb')
        settings.bank_account_number = request.form.get('bank_account_number')
        
        db.session.commit()
        
        # Log activity
        log_activity(
            event_type='settings_updated',
            description='Strata settings updated',
            related_type='StrataSettings',
            related_id=settings.id
        )
        
        flash("Strata settings updated successfully!", "success")
        return redirect(url_for('strata_settings'))
    
    return render_template('strata_settings.html', settings=settings)


# Context processor to make strata settings available in all templates
@app.context_processor
def inject_strata_settings():
    """Make strata settings available in all templates."""
    return {"strata_settings": StrataSettings.get_settings()}