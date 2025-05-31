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

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import string
import io
import base64
import math

def generate_image_captcha():
    """Generate an image-based CAPTCHA with mathematical expression or text."""
    
    # Choose CAPTCHA type
    captcha_type = random.choice(['math', 'text', 'word_math'])
    
    if captcha_type == 'math':
        return generate_math_image_captcha()
    elif captcha_type == 'text':
        return generate_text_image_captcha()
    else:
        return generate_word_math_captcha()

def generate_math_image_captcha():
    """Generate mathematical expression CAPTCHA."""
    # Generate random math problem
    operations = [
        lambda: (random.randint(10, 50), random.randint(1, 20), '+'),
        lambda: (random.randint(20, 80), random.randint(1, 30), '-'),
        lambda: (random.randint(2, 12), random.randint(2, 9), '*'),
    ]
    
    num1, num2, op = random.choice(operations)()
    
    if op == '+':
        answer = num1 + num2
    elif op == '-':
        answer = num1 - num2
    else:  # multiplication
        answer = num1 * num2
    
    question = f"{num1} {op} {num2} = ?"
    
    # Create image
    img = Image.new('RGB', (200, 80), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add some noise
    for _ in range(100):
        x = random.randint(0, 200)
        y = random.randint(0, 80)
        draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))
    
    # Draw text with some distortion
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Add text with slight rotation and color variation
    text_color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
    
    # Calculate text position to center it
    bbox = draw.textbbox((0, 0), question, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (200 - text_width) // 2
    y = (80 - text_height) // 2
    
    draw.text((x, y), question, fill=text_color, font=font)
    
    # Add some lines for distraction
    for _ in range(3):
        start = (random.randint(0, 200), random.randint(0, 80))
        end = (random.randint(0, 200), random.randint(0, 80))
        draw.line([start, end], fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)), width=1)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}", str(answer), f"Solve: {question}"

def generate_text_image_captcha():
    """Generate text-based CAPTCHA."""
    # Generate random string
    chars = string.ascii_uppercase + string.digits
    text = ''.join(random.choices(chars, k=5))
    
    # Create image
    img = Image.new('RGB', (150, 60), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add background noise
    for _ in range(200):
        x = random.randint(0, 150)
        y = random.randint(0, 60)
        draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))
    
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()
    
    # Draw each character with slight variations
    x_offset = 10
    for char in text:
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        y_offset = random.randint(10, 20)
        draw.text((x_offset, y_offset), char, fill=color, font=font)
        x_offset += random.randint(20, 30)
    
    # Add distraction lines
    for _ in range(5):
        start = (random.randint(0, 150), random.randint(0, 60))
        end = (random.randint(0, 150), random.randint(0, 60))
        draw.line([start, end], fill=(random.randint(150, 200), random.randint(150, 200), random.randint(150, 200)), width=1)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}", text.lower(), f"Enter the text shown in the image"

def generate_word_math_captcha():
    """Generate word-based math CAPTCHA."""
    numbers_word = {
        1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
        6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten'
    }
    
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 5)
    operation = random.choice(['plus', 'minus'])
    
    if operation == 'plus':
        answer = num1 + num2
        question = f"{numbers_word[num1]} plus {numbers_word[num2]}"
    else:
        if num1 < num2:
            num1, num2 = num2, num1
        answer = num1 - num2
        question = f"{numbers_word[num1]} minus {numbers_word[num2]}"
    
    # Create image
    img = Image.new('RGB', (250, 80), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add noise
    for _ in range(150):
        x = random.randint(0, 250)
        y = random.randint(0, 80)
        draw.point((x, y), fill=(random.randint(200, 255), random.randint(200, 255), random.randint(200, 255)))
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    bbox = draw.textbbox((0, 0), question, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (250 - text_width) // 2
    y = (80 - text_height) // 2
    
    color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
    draw.text((x, y), question, fill=color, font=font)
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}", str(answer), f"Solve: {question} = ?"

def generate_question_captcha():
    """Generate question-based CAPTCHA."""
    questions = [
        ("What color is the sky on a clear day?", ["blue", "blu"]),
        ("How many days are in a week?", ["7", "seven"]),
        ("What is the opposite of hot?", ["cold", "cool"]),
        ("What do bees make?", ["honey"]),
        ("What is 2 + 2?", ["4", "four"]),
        ("What animal says 'meow'?", ["cat", "kitten"]),
        ("What is the first month of the year?", ["january", "jan"]),
        ("How many wheels does a bicycle have?", ["2", "two"]),
        ("What do you use to write with a pen?", ["ink"]),
        ("What is the opposite of up?", ["down"]),
        ("What color do you get when you mix red and white?", ["pink"]),
        ("What is the capital of France?", ["paris"]),
        ("How many minutes are in an hour?", ["60", "sixty"]),
        ("What season comes after winter?", ["spring"]),
        ("What is the largest ocean on Earth?", ["pacific"]),
    ]
    
    question, valid_answers = random.choice(questions)
    return question, valid_answers[0], valid_answers

def generate_slider_captcha():
    """Generate slider puzzle CAPTCHA data."""
    # Create a simple puzzle where user needs to move slider to specific position
    target_position = random.randint(70, 90)  # Target position (70-90% of slider)
    tolerance = 5  # Allow 5% tolerance
    
    return {
        'target_position': target_position,
        'tolerance': tolerance,
        'min_position': target_position - tolerance,
        'max_position': target_position + tolerance
    }
