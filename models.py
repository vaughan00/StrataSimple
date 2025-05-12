from datetime import datetime
from app import db

class Contact(db.Model):
    """Model for owners and contacts."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    is_owner = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with properties through association model
    property_associations = db.relationship("ContactProperty", back_populates="contact", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Contact {self.name}>"
        
    @property
    def owned_properties(self):
        """Get properties owned by this contact"""
        return [assoc.property for assoc in self.property_associations 
                if assoc.relationship_type == 'owner']
                
    @property
    def managed_properties(self):
        """Get properties managed by this contact"""
        return [assoc.property for assoc in self.property_associations 
                if assoc.relationship_type == 'manager']

class Property(db.Model):
    """Model for individual properties (units) in the strata."""
    id = db.Column(db.Integer, primary_key=True)
    unit_number = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(200))
    balance = db.Column(db.Float, default=0.0)
    entitlement = db.Column(db.Float, default=1.0)  # All properties now have fixed entitlement of 1.0
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with payments
    payments = db.relationship('Payment', backref='property', lazy=True)
    # Relationship with fees
    fees = db.relationship('Fee', backref='property', lazy=True)
    # Relationship with contacts through association model
    contact_associations = db.relationship("ContactProperty", back_populates="property", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Property {self.unit_number}>"
        
    def get_owner(self):
        """Get the owner contact for this property"""
        for contact_assoc in self.contact_associations:
            if contact_assoc.relationship_type == 'owner':
                return contact_assoc.contact
        return None
        
    def get_manager(self):
        """Get the manager contact for this property"""
        for contact_assoc in self.contact_associations:
            if contact_assoc.relationship_type == 'manager':
                return contact_assoc.contact
        return None

# Association model for relationship between Contact and Property
class ContactProperty(db.Model):
    """Model for the relationship between contacts and properties."""
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), primary_key=True)
    relationship_type = db.Column(db.String(50), nullable=False)  # e.g., 'owner', 'manager', 'tenant'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    contact = db.relationship("Contact", back_populates="property_associations")
    property = db.relationship("Property", back_populates="contact_associations")
    
    def __repr__(self):
        return f"<ContactProperty {self.relationship_type}>"

class Payment(db.Model):
    """Model for payments made by property owners."""
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=True)  # Nullable because it might not be assigned yet
    fee_id = db.Column(db.Integer, db.ForeignKey('fee.id'), nullable=True)  # Associated fee, if any
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(200))
    reference = db.Column(db.String(100))  # Reference number from bank statement
    reconciled = db.Column(db.Boolean, default=False)
    is_duplicate = db.Column(db.Boolean, default=False)  # Flag for potential duplicates
    confirmed = db.Column(db.Boolean, default=False)  # Whether the match has been confirmed by user
    transaction_id = db.Column(db.String(100), nullable=True)  # Unique identifier for the transaction (for duplicate detection)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add relationship to fee
    fee = db.relationship('Fee', backref='payments', lazy=True, foreign_keys=[fee_id])
    
    def __repr__(self):
        return f"<Payment {self.amount} for Property {self.property_id}>"

class Fee(db.Model):
    """Model for strata fees charged to properties."""
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)  # Issue date
    due_date = db.Column(db.DateTime, nullable=False)  # Date when fee must be paid by
    description = db.Column(db.String(200))
    period = db.Column(db.String(50))  # e.g., "Q1 2023", "July 2023"
    paid = db.Column(db.Boolean, default=False)
    fee_type = db.Column(db.String(50), default="billing_period")  # Options: billing_period, opening_balance, ad_hoc
    paid_amount = db.Column(db.Float, default=0.0)  # Track partial payments
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
