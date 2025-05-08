from datetime import datetime
from app import db

class Property(db.Model):
    """Model for individual properties (units) in the strata."""
    id = db.Column(db.Integer, primary_key=True)
    unit_number = db.Column(db.String(10), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    owner_email = db.Column(db.String(120))
    balance = db.Column(db.Float, default=0.0)
    entitlement = db.Column(db.Float, default=1.0)  # Share of strata fees (e.g., based on unit size)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with payments
    payments = db.relationship('Payment', backref='property', lazy=True)
    # Relationship with fees
    fees = db.relationship('Fee', backref='property', lazy=True)
    
    def __repr__(self):
        return f"<Property {self.unit_number}>"

class Payment(db.Model):
    """Model for payments made by property owners."""
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(200))
    reference = db.Column(db.String(100))  # Reference number from bank statement
    reconciled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Payment {self.amount} for Property {self.property_id}>"

class Fee(db.Model):
    """Model for strata fees charged to properties."""
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(200))
    period = db.Column(db.String(50))  # e.g., "Q1 2023", "July 2023"
    paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Fee {self.amount} for Property {self.property_id}>"

class BillingPeriod(db.Model):
    """Model for billing periods."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Q1 2023", "July 2023"
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<BillingPeriod {self.name}>"
