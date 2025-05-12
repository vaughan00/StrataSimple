import pandas as pd
import re
import hashlib
from datetime import datetime
from io import StringIO

from app import db
from models import Property, Payment, Fee, ActivityLog

def log_activity(event_type, description, related_type=None, related_id=None):
    """
    Record an activity log entry.
    
    Args:
        event_type (str): Type of event (e.g., 'property_added', 'payment_reconciled')
        description (str): Human-readable description of what happened
        related_type (str, optional): Type of related object (e.g., 'Property', 'Fee')
        related_id (int, optional): ID of the related object
    """
    log_entry = ActivityLog(
        event_type=event_type,
        description=description,
        related_object_type=related_type,
        related_object_id=related_id
    )
    db.session.add(log_entry)
    db.session.commit()

def process_csv(csv_content):
    """
    Process CSV bank statement and extract payment information.
    Returns a list of payment dictionaries.
    """
    # Read CSV content
    df = pd.read_csv(StringIO(csv_content))
    
    # Normalize column names (lowercase and remove spaces)
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    
    # Try to identify relevant columns
    date_col = next((col for col in df.columns if 'date' in col), None)
    description_col = next((col for col in df.columns if 'description' in col or 'particulars' in col or 'narration' in col), None)
    amount_col = next((col for col in df.columns if 'amount' in col or 'credit' in col), None)
    reference_col = next((col for col in df.columns if 'reference' in col), None)
    
    # Validate required columns exist
    if not (date_col and amount_col):
        raise ValueError("CSV file must contain date and amount columns")
    
    # Initialize description and reference columns if they don't exist
    if not description_col:
        df['description'] = ''
        description_col = 'description'
    
    if not reference_col:
        # Use description as reference if no reference column
        df['reference'] = df[description_col]
        reference_col = 'reference'
    
    # Extract payments from DataFrame
    payments = []
    
    for _, row in df.iterrows():
        # Skip rows with no amount or negative amounts (outgoing payments)
        try:
            amount_value = row[amount_col]
            amount = float(amount_value) if not pd.isna(amount_value) else 0
            if amount <= 0:
                continue
        except (TypeError, ValueError):
            continue
        
        # Parse date
        try:
            date_str = str(row[date_col])
            # Try different date formats
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
                try:
                    date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format works, use today's date
                date = datetime.now()
        except Exception:
            date = datetime.now()
        
        # Get description and reference values safely
        try:
            description_value = row[description_col]
            description = str(description_value) if not pd.isna(description_value) else ''
        except Exception:
            description = ''
            
        try:
            reference_value = row[reference_col]
            reference = str(reference_value) if not pd.isna(reference_value) else ''
        except Exception:
            reference = ''
        
        # Create a unique transaction ID based on date, amount, and description/reference
        # This helps with duplicate detection
        transaction_data = f"{date.strftime('%Y-%m-%d')}-{amount:.2f}-{description}-{reference}"
        transaction_id = hashlib.md5(transaction_data.encode()).hexdigest()
        
        # Create payment dictionary
        payment = {
            'date': date,
            'amount': amount,
            'description': description,
            'reference': reference,
            'transaction_id': transaction_id
        }
        
        payments.append(payment)
    
    return payments

def check_for_duplicates(payments):
    """
    Check each payment for potential duplicates in the database.
    Adds is_duplicate flag to payment dictionaries.
    """
    for payment in payments:
        # Check if a payment with the same transaction_id already exists
        existing_payment = Payment.query.filter_by(transaction_id=payment['transaction_id']).first()
        
        if existing_payment:
            payment['is_duplicate'] = True
        else:
            # Also check by date, amount, and description for extra safety
            similar_payments = Payment.query.filter(
                Payment.date.between(
                    payment['date'].replace(hour=0, minute=0, second=0),
                    payment['date'].replace(hour=23, minute=59, second=59)
                ),
                Payment.amount == payment['amount'],
                Payment.description == payment['description']
            ).all()
            
            payment['is_duplicate'] = len(similar_payments) > 0
    
    return payments

def suggest_property_matches(payments):
    """
    Suggest potential property matches for each payment based on reference or description.
    Adds suggestions to payment dictionaries.
    """
    # Get all properties
    properties = Property.query.all()
    
    for payment in payments:
        # Try to find property by unit number or owner name in reference or description
        text_to_search = f"{payment['reference']} {payment['description']}".lower()
        
        # Find property match
        matched_property = None
        match_confidence = 0  # 0-100 scale
        
        for prop in properties:
            # Check for various unit number patterns (with and without the word "unit")
            unit_number = prop.unit_number.lower()
            
            # Direct match: exact unit number
            unit_pattern = re.compile(r'\b' + re.escape(unit_number) + r'\b')
            if unit_pattern.search(text_to_search):
                matched_property = prop
                match_confidence = 90  # High confidence for exact unit number match
                break
                
            # Pattern with "unit" word: "unit X", "unit: X", etc.
            unit_word_pattern = re.compile(r'\bunit\s*[\s:]?\s*' + re.escape(unit_number) + r'\b', re.IGNORECASE)
            if unit_word_pattern.search(text_to_search):
                matched_property = prop
                match_confidence = 90  # High confidence for unit pattern match
                break
                
            # Enhanced unit number detection for various formats including "unit 101" 
            unit_num_match = re.search(r'\bunit\s*[\s:]?\s*(\d+)\b', text_to_search, re.IGNORECASE)
            if unit_num_match:
                extracted_unit_number = unit_num_match.group(1)
                
                # Direct match with this property's unit number
                if extracted_unit_number == unit_number:
                    matched_property = prop
                    match_confidence = 90  # High confidence for unit number match
                    break
                    
                # Check if this extracted unit exists in our database
                exact_match_exists = False
                exact_match_prop = None
                for check_prop in properties:
                    if check_prop.unit_number == extracted_unit_number:
                        exact_match_exists = True
                        exact_match_prop = check_prop
                        break
                        
                # If we found an exact match with another property, suggest that property
                if exact_match_exists and exact_match_prop:
                    # If we're already processing that property, let it match when we get to it
                    if exact_match_prop.id == prop.id:
                        matched_property = prop
                        match_confidence = 95  # Very high confidence
                        break
                
                # If no exact match in database and we allow partial matching
                elif not exact_match_exists and len(properties) < 10:  # Only for small number of properties
                    # Check for substring match (e.g., unit_number "1" in "101")
                    if unit_number in extracted_unit_number:
                        matched_property = prop
                        match_confidence = 60  # Medium confidence for partial match
                        break
                    
                    # For payments without specific unit number matches, assign to first property
                    # This helps with transactions like "unit 102" when we only have units 1-4
                    if prop == properties[0]:  # Only for the first property in the list
                        matched_property = prop
                        match_confidence = 50  # Low confidence
                        # Don't break, a better match might exist
                
            # Simple numeric match for short descriptions
            if unit_number.isdigit() and unit_number in text_to_search and len(text_to_search) < 10:
                matched_property = prop
                match_confidence = 80  # Good confidence for numeric match in short text
                break
            
            # Check if there's an owner contact for this property
            owner_contact = prop.get_owner()
            if owner_contact:
                # Check if owner name is in the text (split into words for more flexible matching)
                owner_parts = owner_contact.name.lower().split()
                if all(part in text_to_search for part in owner_parts if len(part) > 2):
                    matched_property = prop
                    match_confidence = 70  # Medium confidence for owner name match
                    break
            
        # No automatic matching for generic "strata fee" mentions
        # We'll handle these in the UI by letting the user select the right property
        
        # Add property suggestion to payment
        if matched_property:
            owner = matched_property.get_owner()
            owner_name = "No owner assigned"
            if owner is not None:
                owner_name = owner.name
                
            payment['suggested_property'] = {
                'id': matched_property.id,
                'unit_number': matched_property.unit_number,
                'owner': owner_name,
                'confidence': match_confidence
            }
        else:
            payment['suggested_property'] = None
    
    return payments

def suggest_fee_matches(payments):
    """
    Suggest potential fee matches for each payment that has a suggested property.
    Adds fee suggestions to payment dictionaries.
    """
    for payment in payments:
        # Initialize with None as default
        payment['suggested_fee'] = None
        
        # Skip if no suggested property
        suggested_property = payment.get('suggested_property')
        if not suggested_property:
            continue
        
        # Get property ID (safely)
        property_id = suggested_property.get('id')
        if not property_id:
            continue
        
        # Get unpaid fees for this property, ordered by date (oldest first)
        try:
            unpaid_fees = Fee.query.filter_by(
                property_id=property_id,
                paid=False
            ).order_by(Fee.date.asc()).all()
        except Exception:
            # If any database error occurs, skip
            continue
        
        # Try to find a matching fee by amount
        matching_fee = None
        for fee in unpaid_fees:
            try:
                # Exact match
                if abs(fee.amount - payment['amount']) < 0.01:
                    matching_fee = fee
                    break
                # Close match (within 5%)
                elif abs(fee.amount - payment['amount']) / fee.amount < 0.05:
                    matching_fee = fee
                    break
            except (TypeError, ValueError, ZeroDivisionError):
                # Skip this fee if there's any calculation error
                continue
        
        # If no fee matches by amount, suggest the oldest unpaid fee
        if not matching_fee and unpaid_fees:
            matching_fee = unpaid_fees[0]
        
        # Add fee suggestion to payment
        if matching_fee:
            try:
                payment['suggested_fee'] = {
                    'id': matching_fee.id,
                    'amount': matching_fee.amount,
                    'period': matching_fee.period,
                    'exact_match': abs(matching_fee.amount - payment['amount']) < 0.01
                }
            except Exception:
                # If any error occurs while creating the suggestion dict, skip
                payment['suggested_fee'] = None
    
    return payments

def analyze_payments(payments):
    """
    Complete analysis of payments: check duplicates, suggest properties and fees.
    Returns analyzed payments.
    """
    payments = check_for_duplicates(payments)
    payments = suggest_property_matches(payments)
    payments = suggest_fee_matches(payments)
    return payments
    
def reconcile_expenses(transactions):
    """
    Analyze bank transactions to find potential expense matches.
    For each transaction with a negative amount (outgoing payment), try to match with unpaid expenses.
    
    Args:
        transactions: List of transaction dictionaries with date, amount, description
        
    Returns:
        transactions: Updated with suggested_expense field
    """
    from models import Expense
    
    # Debug the transaction data
    print("EXPENSE MATCHING DEBUG:")
    for i, t in enumerate(transactions):
        print(f"Transaction {i}: Amount={t['amount']}, {'EXPENSE' if t['amount'] < 0 else 'INCOME'}")
    
    # Only process negative transactions (outgoing payments)
    for transaction in transactions:
        # Skip positive transactions (incoming payments)
        if transaction['amount'] >= 0:
            transaction['suggested_expense'] = None
            continue
            
        # Convert to positive amount for comparison with expenses
        positive_amount = abs(transaction['amount'])
        
        # Find unpaid expenses that match the amount
        matching_expenses = Expense.query.filter_by(
            paid=False, 
            amount=positive_amount
        ).all()
        
        if matching_expenses:
            # For now, just suggest the first match
            # Future enhancement: Implement fuzzy matching on description or date proximity
            transaction['suggested_expense'] = {
                'id': matching_expenses[0].id,
                'name': matching_expenses[0].name,
                'description': matching_expenses[0].description,
                'amount': matching_expenses[0].amount,
                'due_date': matching_expenses[0].due_date.strftime('%Y-%m-%d'),
                'exact_match': True
            }
        else:
            # Try to find close matches (within 5% of the amount)
            close_expenses = Expense.query.filter(
                Expense.paid == False,
                Expense.amount > positive_amount * 0.95,
                Expense.amount < positive_amount * 1.05
            ).all()
            
            if close_expenses:
                transaction['suggested_expense'] = {
                    'id': close_expenses[0].id,
                    'name': close_expenses[0].name,
                    'description': close_expenses[0].description,
                    'amount': close_expenses[0].amount,
                    'due_date': close_expenses[0].due_date.strftime('%Y-%m-%d'),
                    'exact_match': False
                }
            else:
                transaction['suggested_expense'] = None
                
    return transactions
