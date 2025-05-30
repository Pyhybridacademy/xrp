from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection

def update_profile_balance(user_id, balance_change, profit_change=0, loss_change=0):
    """
    Update a user's profile balance, profit, and loss directly using SQL
    to avoid any potential ORM issues.
    """
    with connection.cursor() as cursor:
        # Update the balance
        cursor.execute(
            "UPDATE trading_userprofile SET balance = balance + %s WHERE user_id = %s",
            [balance_change, user_id]
        )
        
        # Update profit if needed
        if profit_change != 0:
            cursor.execute(
                "UPDATE trading_userprofile SET profit = profit + %s WHERE user_id = %s",
                [profit_change, user_id]
            )
        
        # Update loss if needed
        if loss_change != 0:
            cursor.execute(
                "UPDATE trading_userprofile SET loss = loss + %s WHERE user_id = %s",
                [loss_change, user_id]
            )
        
        # Commit the transaction
        connection.commit()


def send_email_notification(subject, template, recipient_list, context):
    """
    Send an email notification using a template.
    
    Args:
        subject (str): Email subject
        template (str): Path to the email template
        recipient_list (list): List of recipient email addresses
        context (dict): Context data for the template
    """
    html_message = render_to_string(template, context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=False,
    )

def send_registration_email(user):
    """Send a welcome email to a newly registered user."""
    subject = 'Welcome to Trading Platform'
    template = 'emails/welcome_email.html'
    recipient_list = [user.email]
    context = {
        'user': user,
        'full_name': user.profile.full_name
    }
    
    send_email_notification(subject, template, recipient_list, context)
    
    # Notify admin about new registration
    send_admin_notification(
        subject="New User Registration",
        message=f"A new user has registered: {user.username} ({user.email})"
    )

def send_deposit_confirmation_email(user, transaction):
    """Send a deposit confirmation email."""
    subject = 'Deposit Received - Trading Platform'
    template = 'emails/deposit_confirmation.html'
    recipient_list = [user.email]
    context = {
        'user': user,
        'full_name': user.profile.full_name,
        'transaction': transaction
    }
    
    send_email_notification(subject, template, recipient_list, context)
    
    # Notify admin about new deposit
    send_admin_notification(
        subject="New Deposit Request",
        message=f"User {user.username} has submitted a deposit request for ${transaction.amount}"
    )

def send_withdrawal_confirmation_email(user, transaction):
    """Send a withdrawal confirmation email."""
    subject = 'Withdrawal Request Received - Trading Platform'
    template = 'emails/withdrawal_confirmation.html'
    recipient_list = [user.email]
    context = {
        'user': user,
        'full_name': user.profile.full_name,
        'transaction': transaction
    }
    
    send_email_notification(subject, template, recipient_list, context)
    
    # Notify admin about new withdrawal
    send_admin_notification(
        subject="New Withdrawal Request",
        message=f"User {user.username} has submitted a withdrawal request for ${transaction.amount}"
    )

def send_kyc_status_email(user, kyc, status):
    """Send a KYC status update email."""
    subject = f'KYC Verification {status.capitalize()} - Trading Platform'
    template = 'emails/kyc_status.html'
    recipient_list = [user.email]
    context = {
        'user': user,
        'full_name': user.profile.full_name,
        'kyc': kyc,
        'status': status
    }
    
    send_email_notification(subject, template, recipient_list, context)

def send_transaction_status_email(user, transaction, status):
    """Send a transaction status update email."""
    transaction_type = transaction.get_transaction_type_display()
    subject = f'{transaction_type} {status.capitalize()} - Trading Platform'
    template = 'emails/transaction_status.html'
    recipient_list = [user.email]
    context = {
        'user': user,
        'full_name': user.profile.full_name,
        'transaction': transaction,
        'status': status,
        'transaction_type': transaction_type
    }
    
    send_email_notification(subject, template, recipient_list, context)

def send_admin_notification(subject, message):
    """Send a notification to all admin users."""
    admin_emails = User.objects.filter(is_staff=True).values_list('email', flat=True)
    
    if admin_emails:
        send_mail(
            subject=f"[ADMIN] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(admin_emails),
            fail_silently=False,
        )

from django.db import connection
from decimal import Decimal

def update_profile_directly(user_id, balance_delta=0, profit_delta=0, loss_delta=0):
    """
    Update a user profile directly using SQL to bypass any potential ORM issues.
    """
    with connection.cursor() as cursor:
        # Get the table name (adjust if your app name is different)
        table_name = 'main_userprofile'
        
        # Update balance if needed
        if balance_delta != 0:
            cursor.execute(
                f"UPDATE {table_name} SET balance = balance + %s WHERE user_id = %s",
                [str(balance_delta), user_id]
            )
        
        # Update profit if needed
        if profit_delta != 0:
            cursor.execute(
                f"UPDATE {table_name} SET profit = profit + %s WHERE user_id = %s",
                [str(profit_delta), user_id]
            )
        
        # Update loss if needed
        if loss_delta != 0:
            cursor.execute(
                f"UPDATE {table_name} SET loss = loss + %s WHERE user_id = %s",
                [str(loss_delta), user_id]
            )
        
        # Get the updated values for verification
        cursor.execute(
            f"SELECT balance, profit, loss FROM {table_name} WHERE user_id = %s",
            [user_id]
        )
        result = cursor.fetchone()
        
        return {
            'balance': result[0] if result else None,
            'profit': result[1] if result else None,
            'loss': result[2] if result else None
        }

def log_transaction_processing(transaction_id, user_id, action, details):
    """
    Log transaction processing details for debugging purposes
    """
    print(f"TRANSACTION {action.upper()} - ID: {transaction_id}, User: {user_id}")
    for key, value in details.items():
        print(f"TRANSACTION {action.upper()} - {key}: {value}")
    
def update_balance_directly(user_id, amount_delta):
    """
    Update a user's balance directly using SQL to bypass any potential ORM issues.
    
    Args:
        user_id: The user ID
        amount_delta: The amount to add (positive) or subtract (negative)
        
    Returns:
        dict: The old and new balance
    """
    with connection.cursor() as cursor:
        # First get the current balance
        cursor.execute(
            "SELECT balance FROM main_userprofile WHERE user_id = %s",
            [user_id]
        )
        result = cursor.fetchone()
        old_balance = result[0] if result else 0
        
        # Update the balance
        cursor.execute(
            "UPDATE main_userprofile SET balance = balance + %s WHERE user_id = %s",
            [str(amount_delta), user_id]
        )
        
        # Get the new balance
        cursor.execute(
            "SELECT balance FROM main_userprofile WHERE user_id = %s",
            [user_id]
        )
        result = cursor.fetchone()
        new_balance = result[0] if result else 0
        
        return {
            'old_balance': old_balance,
            'new_balance': new_balance
        }

# Add this function to your utils.py file

def send_action_notification_email(user, action):
    """Send notification email for a required action"""
    subject = f"Action Required: {action.get_action_type_display()}"
    
    if action.action_type == 'upgrade':
        plan_name = action.target_plan.get_name_display() if action.target_plan else "higher plan"
        message = f"Dear {user.username},\n\nYou are required to upgrade to the {plan_name} investment plan. "
        message += f"The upgrade cost is ${action.amount}.\n\n"
        
    elif action.action_type == 'signal':
        signal_name = action.signal_plan.name if action.signal_plan else "trading signals"
        message = f"Dear {user.username},\n\nYou are required to purchase the {signal_name} package. "
        message += f"The cost is ${action.amount}.\n\n"
    
    # Add custom message if provided
    if action.message:
        message += f"{action.message}\n\n"
    
    message += "Please log in to your account to complete this action.\n\n"
    message += f"This action is {'mandatory' if action.is_mandatory else 'optional'}.\n\n"
    message += "Thank you,\nTrading Platform Team"
    
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return True
    except Exception as e:
        print(f"Error sending email to {user.email}: {str(e)}")
        return False

from django.core.mail import send_mail
from django.conf import settings

def send_kyc_status_email(user, kyc, status):
    subject = f"KYC Verification {status.capitalize()} - Trading Platform"
    message = f"""
    Hello {user.username},

    Your KYC verification has been {status}.

    Details:
    ID Type: {kyc.id_type}
    ID Number: {kyc.id_number}
    Status: {status.capitalize()}
    Reviewed: {kyc.reviewed_at}

    Thank you,
    Trading Platform Team
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def send_bonus_email(user, bonus_amount, add_to_balance):
    subject = "Bonus Added to Your Account - Trading Platform"
    message = f"""
    Hello {user.username},

    A bonus of {user.profile.currency} {bonus_amount} has been added to your account.

    {'This bonus has also been added to your main balance.' if add_to_balance else 'This bonus is available in your bonus balance.'}

    Current Balances:
    Bonus: {user.profile.currency} {user.profile.bonus}
    Main Balance: {user.profile.currency} {user.profile.balance}

    Thank you,
    Trading Platform Team
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )