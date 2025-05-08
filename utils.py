import pandas as pd
import re
from datetime import datetime
from io import StringIO

from app import db
from models import Property

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
        
        # Create payment dictionary
        payment = {
            'date': date,
            'amount': amount,
            'description': str(row[description_col]) if pd.notnull(row[description_col]) else '',
            'reference': str(row[reference_col]) if pd.notnull(row[reference_col]) else ''
        }
        
        payments.append(payment)
    
    return payments

def match_payments_to_properties(payments):
    """
    Match payments to properties based on reference or description.
    Returns two lists: matched payments and unmatched payments.
    """
    matched = []
    unmatched = []
    
    # Get all properties
    properties = Property.query.all()
    
    for payment in payments:
        # Try to find property by unit number or owner name in reference or description
        text_to_search = f"{payment['reference']} {payment['description']}".lower()
        
        # Find property match
        matched_property = None
        
        for prop in properties:
            # Check if unit number is in the text
            unit_pattern = re.compile(r'\b' + re.escape(prop.unit_number.lower()) + r'\b')
            if unit_pattern.search(text_to_search):
                matched_property = prop
                break
            
            # Check if owner name is in the text (split into words for more flexible matching)
            owner_parts = prop.owner_name.lower().split()
            if all(part in text_to_search for part in owner_parts if len(part) > 2):
                matched_property = prop
                break
        
        # If property matched, add to matched list
        if matched_property:
            payment_with_property = payment.copy()
            payment_with_property['property_id'] = matched_property.id
            payment_with_property['unit_number'] = matched_property.unit_number
            payment_with_property['owner_name'] = matched_property.owner_name
            matched.append(payment_with_property)
        else:
            unmatched.append(payment)
    
    return matched, unmatched
