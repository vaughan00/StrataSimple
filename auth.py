"""
Authentication module for StrataHub application.
Provides functionality for magic link authentication and role-based access control.
"""

import os
import secrets
import string  # Required for token generation
from datetime import datetime, timedelta
from functools import wraps
from flask import render_template, redirect, url_for, request, flash, session, abort
from app import app, db
from models import Property, Contact, User
import email_service

def obfuscate_email(email):
    """Mask an email address for display purposes."""
    if not email or '@' not in email:
        return ""
    
    username, domain = email.split('@', 1)
    if len(username) <= 2:
        visible_username = username[0] + '*'
    else:
        visible_username = username[0] + '*' * (len(username) - 2) + username[-1]
    
    domain_parts = domain.split('.')
    visible_domain = domain_parts[0][0] + '*' * (len(domain_parts[0]) - 1)
    
    return f"{visible_username}@{visible_domain}.{domain_parts[-1]}"

def require_role(*roles):
    """
    Decorator to restrict route access based on user role.
    Usage: @require_role('admin') or @require_role('admin', 'committee')
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Check if user is logged in
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            # Check if user has required role
            user_role = session.get('user_role')
            if user_role not in roles:
                return redirect(url_for('access_denied'))
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def login_required(f):
    """
    Decorator to ensure the user is logged in.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page using magic link authentication.
    Step 1: User selects their property
    Step 2: Display masked email and send magic link
    """
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    # Get all properties for selection
    properties = Property.query.all()
    
    # Process form submission
    if request.method == 'POST':
        # Step 2 - Send login link
        if request.form.get('send_link') == 'true':
            property_id = request.form.get('property_id')
            email = request.form.get('email')
            
            if not property_id or not email:
                flash('Invalid request. Please try again.', 'danger')
                return redirect(url_for('login'))
            
            # Find or create user
            user = User.query.filter_by(email=email).first()
            if not user:
                # Create new user with 'owner' role
                user = User()
                user.email = email
                user.role = 'owner'
                user.property_id = property_id
                db.session.add(user)
            
            # Generate a secure token
            token = user.generate_login_token()
            db.session.commit()
            
            # Send magic link email
            login_url = url_for('verify_login', token=token, _external=True)
            property_obj = Property.query.get(property_id)
            
            unit_text = ""
            if property_obj and property_obj.unit_number:
                unit_text = f" for unit {property_obj.unit_number}"
            
            # Prepare email content
            subject = "StrataHub Login Link"
            text_content = f"""
            Hello,
            
            Someone requested a login link for StrataHub{unit_text}.
            
            Click the link below to log in:
            {login_url}
            
            This link will expire in 30 minutes and can only be used once.
            
            If you did not request this link, please ignore this email.
            
            Regards,
            StrataHub Team
            """
            
            unit_html = ""
            if property_obj and property_obj.unit_number:
                unit_html = f" for unit <strong>{property_obj.unit_number}</strong>"
            
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>StrataHub Login</h2>
                <p>Hello,</p>
                <p>Someone requested a login link for StrataHub{unit_html}.</p>
                <p><a href="{login_url}" style="display: inline-block; background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Click here to log in</a></p>
                <p style="font-size: 0.9em; color: #666;">This link will expire in 30 minutes and can only be used once.</p>
                <p style="font-size: 0.9em; color: #666;">If you did not request this link, please ignore this email.</p>
                <p>Regards,<br>StrataHub Team</p>
            </div>
            """
            
            # Send email
            success = email_service.send_email(
                to_email=email,
                subject=subject,
                text_content=text_content,
                html_content=html_content
            )
            
            if success:
                flash('Login link sent! Please check your email.', 'success')
                return redirect(url_for('login_confirm'))
            else:
                flash('Failed to send login link. Please try again or contact support.', 'danger')
                return redirect(url_for('login'))
        
        # Step 1 - Property selection
        property_id = request.form.get('property_id')
        if property_id:
            property = Property.query.get(property_id)
            if property:
                # Get property owner's email
                owner = property.get_owner()
                if owner and owner.email:
                    # Display masked email and confirm
                    return render_template('login.html', property_data={
                        'id': property.id,
                        'unit_number': property.unit_number,
                        'owner_name': owner.name,
                        'email': owner.email,
                        'masked_email': obfuscate_email(owner.email)
                    })
                else:
                    flash('No owner email found for this property.', 'warning')
            else:
                flash('Invalid property selected.', 'danger')
    
    # Display property selection form
    return render_template('login.html', properties=properties)

@app.route('/login/confirm')
def login_confirm():
    """Confirmation page after sending magic link."""
    return render_template('login_confirm.html')

@app.route('/verify_login')
def verify_login():
    """
    Verifies the magic link token and logs in the user.
    """
    token = request.args.get('token')
    if not token:
        flash('Invalid login link.', 'danger')
        return redirect(url_for('login'))
    
    # Find user with this token
    user = User.query.filter_by(token=token).first()
    if not user or not user.is_token_valid(token):
        flash('Invalid or expired login link. Please request a new one.', 'danger')
        return redirect(url_for('login'))
    
    # Valid token - log the user in
    session['user_id'] = user.id
    session['user_email'] = user.email
    session['user_role'] = user.role
    if user.property_id:
        property = Property.query.get(user.property_id)
        if property:
            session['user_property'] = property.unit_number
    
    # Update last login timestamp and invalidate the token
    user.update_last_login()
    user.invalidate_token()
    db.session.commit()
    
    flash(f'Welcome! You are now logged in as {user.email}.', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """
    Logs out the user by clearing the session.
    """
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/access-denied')
def access_denied():
    """
    Access denied page for unauthorized users.
    """
    return render_template('access_denied.html')

@app.context_processor
def inject_user_data():
    """Make user data available in all templates."""
    return {
        'user': {
            'user_id': session.get('user_id'),
            'user_email': session.get('user_email'),
            'user_role': session.get('user_role'),
            'user_property': session.get('user_property')
        }
    }

@app.errorhandler(403)
def forbidden_error(error):
    return redirect(url_for('access_denied'))