"""
Email service module for StrataHub application.
Provides functionality to send various types of emails using standard SMTP.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from email.utils import formataddr

# Load email configuration from environment variables
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', SMTP_USERNAME)
EMAIL_REPLY_TO = os.environ.get('EMAIL_REPLY_TO', EMAIL_SENDER)

# Import models for fee and property access (only if needed)
try:
    from models import Fee, Property, Contact, Expense
except ImportError:
    # For testing without app context
    Fee, Property, Contact, Expense = None, None, None, None

def send_email(to_email, subject, text_content, html_content=None, cc=None, bcc=None):
    """
    Send an email using SMTP.
    
    Args:
        to_email (str or list): Recipient email address(es)
        subject (str): Email subject
        text_content (str): Plain text content
        html_content (str, optional): HTML content
        cc (str or list, optional): CC recipient(s)
        bcc (str or list, optional): BCC recipient(s)
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    # Use global variables
    global EMAIL_SENDER
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("SMTP credentials not configured. Email not sent.")
        return False
        
    # Convert to_email to list if it's a string
    if isinstance(to_email, str):
        to_email = [to_email]
    
    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    
    # Set the sender
    sender_name = "StrataHub"
    msg['From'] = formataddr((sender_name, EMAIL_SENDER))
    
    # Set recipients
    msg['To'] = ', '.join(to_email)
    
    # Add CC and BCC if provided
    all_recipients = to_email.copy()
    if cc:
        if isinstance(cc, str):
            cc = [cc]
        msg['Cc'] = ', '.join(cc)
        all_recipients.extend(cc)
    
    if bcc:
        if isinstance(bcc, str):
            bcc = [bcc]
        all_recipients.extend(bcc)
        
    # Add Reply-To header
    if EMAIL_REPLY_TO:
        msg['Reply-To'] = EMAIL_REPLY_TO
    
    # Add text part
    text_part = MIMEText(text_content, 'plain')
    msg.attach(text_part)
    
    # Add HTML part if provided
    if html_content:
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
    
    try:
        # Connect to server and send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        
        # Debug info for troubleshooting
        print(f"Attempting to connect to {SMTP_SERVER}:{SMTP_PORT} with username: {SMTP_USERNAME}")
        
        # Special handling for Gmail
        if SMTP_SERVER and SMTP_SERVER.lower() == "smtp.gmail.com":
            try:
                # Use standard authentication method
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                
                # When using Gmail, the sender must be the authenticated user
                # or Gmail will reject the message or change the from address
                if EMAIL_SENDER != SMTP_USERNAME:
                    print(f"Note: For Gmail, the sender {EMAIL_SENDER} should match the authenticated username {SMTP_USERNAME}")
                    if not EMAIL_SENDER.endswith('@gmail.com'):
                        original_sender = EMAIL_SENDER
                        EMAIL_SENDER = SMTP_USERNAME
                        msg.replace_header("From", formataddr((sender_name, EMAIL_SENDER)))
                        print(f"Note: Changed sender from {original_sender} to {EMAIL_SENDER} to comply with Gmail requirements")
            
            except Exception as gmail_error:
                print(f"Gmail authentication error: {gmail_error}")
                print("Note: For Gmail, you need to use an 'App Password' generated in your Google Account settings.")
                print("Visit https://myaccount.google.com/apppasswords to create one.")
                return False
        else:
            # Standard SMTP authentication for non-Gmail servers
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Send the email
        server.sendmail(EMAIL_SENDER, all_recipients, msg.as_string())
        server.close()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        if "support.google.com/mail/?p=BadCredentials" in str(e):
            print("\nImportant: For Gmail, you need to use an 'App Password' instead of your regular password.")
            print("1. Visit https://myaccount.google.com/apppasswords")
            print("2. Sign in with your Google Account")
            print("3. Select 'App passwords' under 'Security'")
            print("4. Generate a new App Password for 'Mail' on 'Other'")
            print("5. Use that 16-character password as your SMTP_PASSWORD\n")
        return False

def send_fee_notification(fee, contact):
    """
    Send notification about a new fee to a property owner.
    
    Args:
        fee (Fee): The fee object
        contact (Contact): The contact receiving the notification
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    property_unit = fee.property.unit_number
    subject = f"New Fee Notification - Unit {property_unit}"
    
    due_date = fee.due_date.strftime("%d %B %Y")
    fee_type = fee.fee_type.replace('_', ' ').title()
    
    text_content = f"""
Dear {contact.name},

A new fee has been added to your account for Unit {property_unit}.

Fee Details:
- Amount: ${fee.amount:.2f}
- Type: {fee_type}
- Description: {fee.description}
- Due Date: {due_date}

Please ensure payment is made by the due date to avoid any late fees.

Thank you,
StrataHub Management
"""
    
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>New Fee Notification</h2>
    <p>Dear {contact.name},</p>
    <p>A new fee has been added to your account for <strong>Unit {property_unit}</strong>.</p>
    
    <div style="background: #f7f7f7; padding: 15px; border-left: 4px solid #0066cc; margin: 20px 0;">
        <h3 style="margin-top: 0;">Fee Details:</h3>
        <ul>
            <li><strong>Amount:</strong> ${fee.amount:.2f}</li>
            <li><strong>Type:</strong> {fee_type}</li>
            <li><strong>Description:</strong> {fee.description}</li>
            <li><strong>Due Date:</strong> {due_date}</li>
        </ul>
    </div>
    
    <p>Please ensure payment is made by the due date to avoid any late fees.</p>
    
    <p>Thank you,<br>
    StrataHub Management</p>
</body>
</html>
"""
    
    return send_email(contact.email, subject, text_content, html_content)

def send_payment_receipt(payment, contact):
    """
    Send a receipt for a payment to a property owner.
    
    Args:
        payment (Payment): The payment object
        contact (Contact): The contact receiving the receipt
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    property_unit = payment.property.unit_number
    subject = f"Payment Receipt - Unit {property_unit}"
    
    payment_date = payment.date.strftime("%d %B %Y")
    
    text_content = f"""
Dear {contact.name},

Thank you for your payment for Unit {property_unit}.

Payment Details:
- Amount: ${payment.amount:.2f}
- Date: {payment_date}
- Reference: {payment.reference or 'N/A'}

This payment has been applied to your account.

Thank you,
StrataHub Management
"""
    
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Payment Receipt</h2>
    <p>Dear {contact.name},</p>
    <p>Thank you for your payment for <strong>Unit {property_unit}</strong>.</p>
    
    <div style="background: #f0f9f0; padding: 15px; border-left: 4px solid #00cc66; margin: 20px 0;">
        <h3 style="margin-top: 0;">Payment Details:</h3>
        <ul>
            <li><strong>Amount:</strong> ${payment.amount:.2f}</li>
            <li><strong>Date:</strong> {payment_date}</li>
            <li><strong>Reference:</strong> {payment.reference or 'N/A'}</li>
        </ul>
    </div>
    
    <p>This payment has been applied to your account.</p>
    
    <p>Thank you,<br>
    StrataHub Management</p>
</body>
</html>
"""
    
    return send_email(contact.email, subject, text_content, html_content)

def send_overdue_reminder(fee, contact):
    """
    Send a reminder about an overdue fee to a property owner.
    
    Args:
        fee (Fee): The fee object
        contact (Contact): The contact receiving the reminder
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    property_unit = fee.property.unit_number
    subject = f"OVERDUE: Fee Payment Reminder - Unit {property_unit}"
    
    due_date = fee.due_date.strftime("%d %B %Y")
    today = datetime.now().strftime("%d %B %Y")
    days_overdue = (datetime.now().date() - fee.due_date.date()).days
    
    text_content = f"""
Dear {contact.name},

This is a reminder that a fee payment for Unit {property_unit} is now OVERDUE.

Fee Details:
- Amount: ${fee.amount:.2f}
- Description: {fee.description}
- Due Date: {due_date} ({days_overdue} days overdue)
- Remaining Amount: ${fee.remaining_amount():.2f}

Please make the payment as soon as possible to avoid further late fees.

Thank you,
StrataHub Management
"""
    
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #cc0000;">OVERDUE: Fee Payment Reminder</h2>
    <p>Dear {contact.name},</p>
    <p>This is a reminder that a fee payment for <strong>Unit {property_unit}</strong> is now <strong style="color: #cc0000;">OVERDUE</strong>.</p>
    
    <div style="background: #fff0f0; padding: 15px; border-left: 4px solid #cc0000; margin: 20px 0;">
        <h3 style="margin-top: 0;">Fee Details:</h3>
        <ul>
            <li><strong>Amount:</strong> ${fee.amount:.2f}</li>
            <li><strong>Description:</strong> {fee.description}</li>
            <li><strong>Due Date:</strong> {due_date} (<strong>{days_overdue} days overdue</strong>)</li>
            <li><strong>Remaining Amount:</strong> ${fee.remaining_amount():.2f}</li>
        </ul>
    </div>
    
    <p>Please make the payment as soon as possible to avoid further late fees.</p>
    
    <p>Thank you,<br>
    StrataHub Management</p>
</body>
</html>
"""
    
    return send_email(contact.email, subject, text_content, html_content)

def send_expense_paid_notification(expense, admin_emails):
    """
    Send a notification that an expense has been paid.
    
    Args:
        expense (Expense): The expense object
        admin_emails (list): List of administrator email addresses
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    subject = f"Expense Payment Confirmation: {expense.name}"
    
    paid_date = expense.paid_date.strftime("%d %B %Y") if expense.paid_date else 'Unknown'
    
    text_content = f"""
Expense Payment Confirmation

The following expense has been marked as paid:

Expense Details:
- Name: {expense.name}
- Amount: ${expense.amount:.2f}
- Description: {expense.description}
- Paid Date: {paid_date}

This is an automated notification from StrataHub Management.
"""
    
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Expense Payment Confirmation</h2>
    <p>The following expense has been marked as paid:</p>
    
    <div style="background: #f0f0f9; padding: 15px; border-left: 4px solid #6666cc; margin: 20px 0;">
        <h3 style="margin-top: 0;">Expense Details:</h3>
        <ul>
            <li><strong>Name:</strong> {expense.name}</li>
            <li><strong>Amount:</strong> ${expense.amount:.2f}</li>
            <li><strong>Description:</strong> {expense.description}</li>
            <li><strong>Paid Date:</strong> {paid_date}</li>
        </ul>
    </div>
    
    <p>This is an automated notification from StrataHub Management.</p>
</body>
</html>
"""
    
    return send_email(admin_emails, subject, text_content, html_content)

def send_financial_summary(properties, admin_emails, period=None):
    """
    Send a financial summary for the strata properties.
    
    Args:
        properties (list): List of Property objects
        admin_emails (list): List of administrator email addresses
        period (str, optional): Period description (e.g., "April 2025")
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    period_text = f" - {period}" if period else ""
    subject = f"Financial Summary Report{period_text}"
    
    today = datetime.now().strftime("%d %B %Y")
    
    # Calculate totals
    total_fees = sum(sum(f.amount for f in p.fees) for p in properties)
    total_paid = sum(sum(p.amount for p in prop.payments if p.amount > 0) for prop in properties)
    overdue_fees = sum(f.remaining_amount() for p in properties for f in p.fees if f.is_overdue())
    
    # Build property table for text and HTML
    text_property_rows = []
    html_property_rows = []
    
    for prop in properties:
        owner = prop.get_owner()
        owner_name = owner.name if owner else "No owner assigned"
        
        total_prop_fees = sum(f.amount for f in prop.fees)
        total_prop_paid = sum(p.amount for p in prop.payments if p.amount > 0)
        balance = total_prop_paid - total_prop_fees
        
        text_property_rows.append(
            f"- Unit {prop.unit_number} | Owner: {owner_name} | Fees: ${total_prop_fees:.2f} | "
            f"Paid: ${total_prop_paid:.2f} | Balance: ${balance:.2f}"
        )
        
        status = "Paid" if balance >= 0 else "Outstanding"
        color = "#00cc66" if balance >= 0 else "#cc0000"
        
        html_property_rows.append(f"""
        <tr>
            <td>{prop.unit_number}</td>
            <td>{owner_name}</td>
            <td>${total_prop_fees:.2f}</td>
            <td>${total_prop_paid:.2f}</td>
            <td style="color: {color};">${balance:.2f}</td>
            <td><span style="color: {color};">{status}</span></td>
        </tr>
        """)
    
    text_content = f"""
Financial Summary Report{period_text}
Generated on: {today}

SUMMARY:
- Total Fees: ${total_fees:.2f}
- Total Payments: ${total_paid:.2f}
- Overdue Amount: ${overdue_fees:.2f}
- Net Position: ${total_paid - total_fees:.2f}

PROPERTY DETAILS:
{"".join(text_property_rows)}

This is an automated report from StrataHub Management.
"""
    
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Financial Summary Report{period_text}</h2>
    <p>Generated on: {today}</p>
    
    <div style="background: #f7f7f7; padding: 15px; border-left: 4px solid #0066cc; margin: 20px 0;">
        <h3 style="margin-top: 0;">Summary:</h3>
        <ul>
            <li><strong>Total Fees:</strong> ${total_fees:.2f}</li>
            <li><strong>Total Payments:</strong> ${total_paid:.2f}</li>
            <li><strong>Overdue Amount:</strong> ${overdue_fees:.2f}</li>
            <li><strong>Net Position:</strong> ${total_paid - total_fees:.2f}</li>
        </ul>
    </div>
    
    <h3>Property Details:</h3>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <thead>
            <tr style="background-color: #333; color: white;">
                <th style="padding: 8px; text-align: left;">Unit</th>
                <th style="padding: 8px; text-align: left;">Owner</th>
                <th style="padding: 8px; text-align: left;">Total Fees</th>
                <th style="padding: 8px; text-align: left;">Paid</th>
                <th style="padding: 8px; text-align: left;">Balance</th>
                <th style="padding: 8px; text-align: left;">Status</th>
            </tr>
        </thead>
        <tbody>
            {"".join(html_property_rows)}
        </tbody>
    </table>
    
    <p>This is an automated report from StrataHub Management.</p>
</body>
</html>
"""
    
    return send_email(admin_emails, subject, text_content, html_content)

def test_email_connection():
    """
    Test the email connection by sending a test email to the configured sender.
    
    Returns:
        bool: True if connection works, False otherwise
    """
    subject = "StrataHub Email System Test"
    text_content = f"""
This is a test email from StrataHub.
If you're seeing this, the email system is configured correctly.

Email configuration:
- SMTP Server: {SMTP_SERVER}
- SMTP Port: {SMTP_PORT}
- Username: {SMTP_USERNAME}
- Sender: {EMAIL_SENDER}

Timestamp: {datetime.now()}
"""
    
    return send_email(SMTP_USERNAME, subject, text_content)