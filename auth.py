"""
Authentication module for StrataHub application.
Provides functionality for magic link authentication and role-based access control.
"""

from functools import wraps
from flask import abort, redirect, render_template, request, session, url_for, flash
from datetime import datetime

from app import app, db
from models import User, Property, Contact, ContactProperty
import email_service
from utils import log_activity

# Email obfuscation function
def obfuscate_email(email):
    """Mask an email address for display purposes."""
    if not email or '@' not in email:
        return ""
        
    local, domain = email.split('@')
    
    # Mask local part, but keep first and last character
    if len(local) <= 2:
        masked_local = local[0] + '*' if len(local) > 1 else local
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    # Mask domain, but keep TLD
    domain_parts = domain.split('.')
    if len(domain_parts[0]) <= 2:
        masked_domain = domain_parts[0][0] + '*' if len(domain_parts[0]) > 1 else domain_parts[0]
    else:
        masked_domain = domain_parts[0][0] + '*' * (len(domain_parts[0]) - 2) + domain_parts[0][-1]
    
    # Add back the TLD
    masked_domain += '.' + '.'.join(domain_parts[1:])
    
    return f"{masked_local}@{masked_domain}"

# Role-based access control decorator
def require_role(*roles):
    """
    Decorator to restrict route access based on user role.
    Usage: @require_role('admin') or @require_role('admin', 'committee')
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('login'))
                
            user_role = session.get('user_role')
            if user_role not in roles:
                log_activity(
                    event_type='access_denied',
                    description=f"Access denied to {request.path} for user with role '{user_role}'",
                    related_type='User',
                    related_id=session.get('user_id')
                )
                return abort(403)
                
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Login check decorator (any authenticated user)
def login_required(f):
    """
    Decorator to ensure the user is logged in.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            # Store the original URL for redirecting after login
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# Routes for authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page using magic link authentication.
    Step 1: User selects their property
    Step 2: Display masked email and send magic link
    """
    # Check if user is already logged in
    if session.get('user_id'):
        return redirect(url_for('index'))
    
    # Get all properties for selection
    properties = Property.query.order_by(Property.unit_number).all()
    
    # Variable to hold confirmed email when selected
    property_data = None
    
    if request.method == 'POST':
        # Step 1: Property selection
        if 'property_id' in request.form and not request.form.get('send_link'):
            property_id = request.form.get('property_id')
            
            # Get the property
            selected_property = Property.query.get(property_id)
            if not selected_property:
                flash("Please select a valid property.", "danger")
                return render_template('login.html', properties=properties)
            
            # Find the owner's email for this property
            owner = selected_property.get_owner()
            if not owner or not owner.email:
                flash("No email address found for this property owner. Please contact the administrator.", "danger")
                return render_template('login.html', properties=properties)
            
            # Obfuscate the email for display
            masked_email = obfuscate_email(owner.email)
            
            # Prepare data for the template
            property_data = {
                'id': selected_property.id,
                'unit_number': selected_property.unit_number,
                'email': owner.email,
                'masked_email': masked_email,
                'owner_name': owner.name
            }
            
            return render_template('login.html', properties=properties, property_data=property_data)
        
        # Step 2: Confirm and send magic link
        elif 'property_id' in request.form and 'email' in request.form and request.form.get('send_link'):
            property_id = request.form.get('property_id')
            email = request.form.get('email')
            
            # Check if there's a user with this email
            user = User.query.filter_by(email=email).first()
            
            # If no user exists, create one
            if not user:
                user = User(
                    email=email,
                    role='owner',  # Default role is owner
                    property_id=property_id
                )
                db.session.add(user)
                db.session.commit()
                
                log_activity(
                    event_type='user_created',
                    description=f"New user created with email {email} for property {property_id}",
                    related_type='User',
                    related_id=user.id
                )
            
            # Generate login token
            token = user.generate_login_token()
            db.session.commit()
            
            # Build the magic link
            magic_link = url_for('verify_login', token=token, _external=True)
            
            # Get property for contextual information
            user_property = Property.query.get(property_id)
            strata_name = "Your Strata"
            
            # Try to get strata name from settings
            try:
                from models import StrataSettings
                settings = StrataSettings.get_settings()
                strata_name = settings.strata_name
            except:
                pass
            
            # Send the magic link email
            subject = f"{strata_name} - Your Login Link"
            
            text_content = f"""
Hello,

Here is your secure login link for {strata_name}:
{magic_link}

This link is valid for 30 minutes and can only be used once.
If you did not request this link, please ignore this email.

Thank you,
{strata_name} Management
"""
            
            html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Your Secure Login Link</h2>
    <p>Hello,</p>
    <p>Here is your secure login link for {strata_name}:</p>
    <p>
        <a href="{magic_link}" style="display: inline-block; background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
            Login to StrataHub
        </a>
    </p>
    <p style="color: #666; font-size: 0.9em;">
        This link is valid for 30 minutes and can only be used once.
        If you did not request this link, please ignore this email.
    </p>
    <p>
        Thank you,<br>
        {strata_name} Management
    </p>
</body>
</html>
"""
            
            success = email_service.send_email(
                to_email=email,
                subject=subject,
                text_content=text_content,
                html_content=html_content
            )
            
            log_activity(
                event_type='login_link_sent',
                description=f"Login link sent to {email} for property {user_property.unit_number if user_property else property_id}",
                related_type='User',
                related_id=user.id
            )
            
            if success:
                flash("Login link sent! Please check your email.", "success")
            else:
                flash("Error sending login link. Please try again or contact support.", "danger")
            
            return redirect(url_for('login_confirm'))
    
    return render_template('login.html', properties=properties)

@app.route('/login/confirm')
def login_confirm():
    """Confirmation page after sending magic link."""
    return render_template('login_confirm.html')

@app.route('/auth/verify')
def verify_login():
    """
    Verifies the magic link token and logs in the user.
    """
    token = request.args.get('token')
    
    if not token:
        flash("Invalid login link. Please try again.", "danger")
        return redirect(url_for('login'))
    
    # Find the user with this token
    user = User.query.filter_by(token=token).first()
    
    if not user:
        flash("Invalid login link. Please try again.", "danger")
        return redirect(url_for('login'))
    
    # Check if token is valid
    if not user.is_token_valid(token):
        flash("This login link has expired. Please request a new one.", "danger")
        return redirect(url_for('login'))
    
    # Valid token, log the user in
    session['user_id'] = user.id
    session['user_email'] = user.email
    session['user_role'] = user.role
    
    if user.property_id:
        user_property = Property.query.get(user.property_id)
        if user_property:
            session['user_property'] = user_property.unit_number
    
    # Update last login and invalidate the token
    user.update_last_login()
    user.invalidate_token()
    db.session.commit()
    
    log_activity(
        event_type='user_login',
        description=f"User {user.email} logged in",
        related_type='User',
        related_id=user.id
    )
    
    # Check if there's a next URL stored in the session
    next_url = session.pop('next_url', None)
    if next_url:
        return redirect(next_url)
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """
    Logs out the user by clearing the session.
    """
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    
    if user_id:
        log_activity(
            event_type='user_logout',
            description=f"User {user_email} logged out",
            related_type='User',
            related_id=user_id
        )
    
    # Clear the session
    session.clear()
    
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/access-denied')
def access_denied():
    """
    Access denied page for unauthorized users.
    """
    return render_template('access_denied.html')

# Inject user data into templates
@app.context_processor
def inject_user_data():
    """Make user data available in all templates."""
    user_data = {
        'user_id': session.get('user_id'),
        'user_email': session.get('user_email'),
        'user_role': session.get('user_role'),
        'user_property': session.get('user_property')
    }
    return {"user": user_data}

# Register error handler for 403 errors
@app.errorhandler(403)
def forbidden_error(error):
    return render_template('access_denied.html'), 403