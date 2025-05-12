import pandas as pd
import re
import hashlib
from datetime import datetime
from io import StringIO

from app import db
from models import Property, Payment, Fee

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
        amount = float(row[amount_col]) if pd.notnull(row[amount_col]) else 0
        if amount <= 0:
            continue
        
        # Parse date
        date_str = str(row[date_col])
        try:
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
        
        description = str(row[description_col]) if pd.notnull(row[description_col]) else ''
        reference = str(row[reference_col]) if pd.notnull(row[reference_col]) else ''
        
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
                    
            # Check for "strata fee" as a generic match for any property
            if "strata fee" in text_to_search or "fee" in text_to_search:
                matched_property = prop
                match_confidence = 50  # Lower confidence for generic fee mention
                # Don't break, keep looking for better matches
        
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
