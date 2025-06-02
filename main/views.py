from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal
from .models import (
    UserProfile, KYCVerification, Transaction,
    Cryptocurrency, Investment, InvestmentPlan, WalletAddress, WithdrawalCode
)
from .utils import (
    send_registration_email,
    send_deposit_confirmation_email,
    send_withdrawal_confirmation_email,
    send_kyc_status_email,
    generate_image_captcha,
    generate_question_captcha,
    generate_slider_captcha
)
from .forms import RegistrationForm, LoginForm, UserProfileForm
import logging
import random
import json

logger = logging.getLogger(__name__)

def generate_advanced_captcha():
    """Generate advanced CAPTCHA with multiple types."""
    captcha_types = ['image', 'question', 'slider']
    captcha_type = random.choice(captcha_types)
    
    if captcha_type == 'image':
        image_data, answer, question = generate_image_captcha()
        return {
            'type': 'image',
            'image_data': image_data,
            'question': question,
            'answer': answer
        }
    elif captcha_type == 'question':
        question, primary_answer, valid_answers = generate_question_captcha()
        return {
            'type': 'question',
            'question': question,
            'answer': primary_answer,
            'valid_answers': valid_answers
        }
    else:  # slider
        slider_data = generate_slider_captcha()
        return {
            'type': 'slider',
            'question': f"Move the slider to {slider_data['target_position']}% position",
            'answer': slider_data['target_position'],
            'slider_data': slider_data
        }

def register(request):
    if request.method == 'POST':
        # Get CAPTCHA data from session
        captcha_data = request.session.get('_captcha_data', {})
        captcha_answer = captcha_data.get('answer')
        
        form = RegistrationForm(request.POST, captcha_answer=captcha_answer)
        logger.debug(f"Registration POST data: {request.POST}")
        
        # Validate CAPTCHA based on type
        captcha_valid = False
        user_answer = request.POST.get('captcha_answer', '').strip()
        
        if captcha_data.get('type') == 'question':
            valid_answers = captcha_data.get('valid_answers', [])
            captcha_valid = user_answer.lower() in [ans.lower() for ans in valid_answers]
        elif captcha_data.get('type') == 'slider':
            try:
                user_position = float(user_answer)
                slider_data = captcha_data.get('slider_data', {})
                min_pos = slider_data.get('min_position', 0)
                max_pos = slider_data.get('max_position', 100)
                captcha_valid = min_pos <= user_position <= max_pos
            except (ValueError, TypeError):
                captcha_valid = False
        else:
            captcha_valid = user_answer.lower() == str(captcha_answer).lower()
        
        if captcha_valid and form.is_valid():
            with transaction.atomic():
                user = form.save()
                logger.debug(f"User created: {user.id}, username: {user.username}, email: {user.email}")
                
                # Update UserProfile fields after creation by the signal
                try:
                    profile = user.profile
                    profile.full_name = form.cleaned_data['full_name']
                    profile.phone = form.cleaned_data.get('phone', '')
                    profile.country = form.cleaned_data.get('country', '')
                    profile.currency = form.cleaned_data.get('currency', 'USD')
                    profile.save()
                    logger.debug(f"UserProfile updated for user: {user.username}")
                except UserProfile.DoesNotExist:
                    logger.error(f"UserProfile not found for user: {user.username}")
                    messages.error(request, 'Profile creation failed. Please contact support.')
                    return redirect('main:login')
                
                # Authenticate the user
                username = user.username
                password = form.cleaned_data['password']
                authenticated_user = authenticate(request, username=username, password=password)
                
                if authenticated_user is not None:
                    login(request, authenticated_user)
                    logger.info(f"New user registered and logged in: {username}, currency: {form.cleaned_data.get('currency', 'USD')}")
                    try:
                        send_registration_email(user)
                    except Exception as e:
                        logger.error(f"Error sending registration email: {e}")
                    
                    messages.success(request, 'Registration successful!')
                    # Clean up session
                    if '_captcha_data' in request.session:
                        del request.session['_captcha_data']
                    return redirect('main:dashboard')
                else:
                    logger.warning(f"Authentication failed after registration for username: {username}")
                    # Check if user exists in database
                    try:
                        user_check = User.objects.get(username=username)
                        logger.debug(f"User exists in database: {user_check.username}, is_active: {user_check.is_active}")
                    except User.DoesNotExist:
                        logger.error(f"User not found in database after creation: {username}")
                    
                    messages.error(request, 'Registration successful, but login failed. Please try logging in.')
                    return redirect('main:login')
        else:
            if not captcha_valid:
                logger.warning(f"Invalid CAPTCHA from IP {request.META.get('REMOTE_ADDR')}")
                messages.error(request, 'Invalid CAPTCHA answer. Please try again.')
            
            logger.warning(f"Failed registration attempt from IP {request.META.get('REMOTE_ADDR')}: {form.errors}")
            for error in form.errors.values():
                messages.error(request, error)
            
            # Generate new CAPTCHA for invalid form
            captcha_data = generate_advanced_captcha()
            request.session['_captcha_data'] = captcha_data
            request.session.modified = True
            logger.debug(f"New CAPTCHA generated: {captcha_data['type']}")
    else:
        # Initial GET request
        captcha_data = generate_advanced_captcha()
        request.session['_captcha_data'] = captcha_data
        request.session.modified = True
        logger.debug(f"Initial CAPTCHA generated: {captcha_data['type']}")
        form = RegistrationForm()
    
    return render(request, 'main/register.html', {
        'form': form,
        'captcha_data': captcha_data
    })



# main/views.py
def login_view(request):
    if request.method == 'POST':
        # Get CAPTCHA data from session
        captcha_data = request.session.get('_captcha_data', {})
        captcha_answer = captcha_data.get('answer', '')
        
        form = LoginForm(request.POST, captcha_answer=captcha_answer)
        logger.debug(f"Login POST data: {request.POST}")
        
        # Validate CAPTCHA based on type
        captcha_valid = False
        user_answer = request.POST.get('captcha_answer', '').strip()
        
        if captcha_data.get('type') == 'question':
            valid_answers = captcha_data.get('valid_answers', [])
            captcha_valid = user_answer.lower() in [str(ans).lower() for ans in valid_answers]
        elif captcha_data.get('type') == 'slider':
            try:
                user_position = float(user_answer)
                slider_data = captcha_data.get('slider_data', {})
                min_pos = slider_data.get('min_position', 0)
                max_pos = slider_data.get('max_position', 100)
                captcha_valid = min_pos <= user_position <= max_pos
            except (ValueError, TypeError):
                captcha_valid = False
        else:
            captcha_valid = user_answer.lower() == str(captcha_answer).lower()
        
        if captcha_valid and form.is_valid():
            username_or_email = form.cleaned_data['username_or_email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username_or_email, password=password)
            if user is not None:
                login(request, user)
                if '_captcha_data' in request.session:
                    del request.session['_captcha_data']
                logger.info(f"User logged in: {username_or_email}")
                messages.success(request, 'Login successful.')
                return redirect('main:dashboard')
            else:
                logger.warning(f"Failed login attempt for {username_or_email} from IP {request.META.get('REMOTE_ADDR')}")
                messages.error(request, 'Invalid username/email or password.')
        else:
            if not captcha_valid:
                logger.warning(f"Invalid CAPTCHA from IP {request.META.get('REMOTE_ADDR')}")
                messages.error(request, 'Invalid CAPTCHA answer. Please try again.')
            
            logger.warning(f"Failed login attempt from IP {request.META.get('REMOTE_ADDR')}: {form.errors}")
            for error in form.errors.values():
                messages.error(request, error)
        
        # Generate new CAPTCHA for any failed attempt
        captcha_data = generate_advanced_captcha()
        request.session['_captcha_data'] = captcha_data
        request.session.modified = True
    else:
        captcha_data = generate_advanced_captcha()
        request.session['_captcha_data'] = captcha_data
        request.session.modified = True
        form = LoginForm()
    
    return render(request, 'main/login.html', {
        'form': form,
        'captcha_data': captcha_data
    })

def refresh_captcha(request):
    """AJAX endpoint to refresh CAPTCHA."""
    if request.method == 'POST':
        captcha_data = generate_advanced_captcha()
        request.session['_captcha_data'] = captcha_data
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'captcha_data': captcha_data
        })
    
    return JsonResponse({'success': False})

@login_required
def logout_view(request):
    logout(request)
    return redirect('main:home')

@login_required
def kyc_verification(request):
    try:
        kyc = KYCVerification.objects.get(user=request.user)
        kyc_exists = True
    except KYCVerification.DoesNotExist:
        kyc = None
        kyc_exists = False
    
    logger.info(f"KYC exists: {kyc_exists}, Status: {kyc.status if kyc else 'None'}")
    
    if request.method == 'POST' and not (kyc_exists and kyc.status in ['approved', 'submitted']):
        logger.info(f"request.FILES: {request.FILES}")
        # Validate id_type and id_number
        if not request.POST.get('id_type') or not request.POST.get('id_number'):
            logger.error(f"Missing id_type or id_number: id_type={request.POST.get('id_type')}, id_number={request.POST.get('id_number')}")
            messages.error(request, 'Please provide both ID type and ID number.')
            return redirect('main:kyc_verification')
        
        # Validate all files
        if 'id_front' not in request.FILES or 'id_back' not in request.FILES or 'selfie' not in request.FILES:
            logger.error(f"Missing files: id_front={bool('id_front' in request.FILES)}, id_back={bool('id_back' in request.FILES)}, selfie={bool('selfie' in request.FILES)}")
            messages.error(request, 'Please upload all required documents.')
            return redirect('main:kyc_verification')
        
        if kyc_exists:
            kyc.id_type = request.POST.get('id_type')
            kyc.id_number = request.POST.get('id_number')
            kyc.status = 'submitted'
            kyc.submitted_at = timezone.now()
            kyc.id_front = request.FILES['id_front']
            kyc.id_back = request.FILES['id_back']
            kyc.selfie = request.FILES['selfie']
            kyc.rejection_reason = None
            kyc.save()
        else:
            kyc = KYCVerification.objects.create(
                user=request.user,
                id_type=request.POST.get('id_type'),
                id_number=request.POST.get('id_number'),
                id_front=request.FILES['id_front'],
                id_back=request.FILES['id_back'],
                selfie=request.FILES['selfie'],
                status='submitted',
                submitted_at=timezone.now()
            )
        
        try:
            send_kyc_status_email(request.user, kyc, 'submitted')
        except Exception as e:
            logger.error(f"Error sending KYC submission email: {e}")
        
        messages.success(request, 'KYC verification submitted successfully.')
        return redirect('main:dashboard')
    
    context = {'kyc': kyc}
    return render(request, 'main/kyc_verification.html', context)

@login_required
def deposit(request):
    try:
        kyc = KYCVerification.objects.get(user=request.user)
        kyc_approved = kyc.status == 'approved'
    except KYCVerification.DoesNotExist:
        kyc_approved = False
    
    cryptocurrencies = Cryptocurrency.objects.filter(is_active=True)
    profile = request.user.profile
    
    if request.method == 'POST' and kyc_approved:
        try:
            amount = Decimal(request.POST.get('amount'))
        except (ValueError, TypeError):
            logger.error(f"Invalid amount provided: {request.POST.get('amount')}")
            messages.error(request, 'Invalid deposit amount.')
            return redirect('main:deposit')
            
        payment_method = request.POST.get('payment_method')
        
        # Validate amount
        if amount < Decimal('10'):
            messages.error(request, f'Minimum deposit amount is 10 {profile.currency}.')
            return redirect('main:deposit')
        
        new_transaction = Transaction(
            user=request.user,
            transaction_type='deposit',
            amount=amount,
            payment_method=payment_method,
            status='pending'
        )
        
        if payment_method == 'crypto':
            crypto_id = request.POST.get('cryptocurrency')
            if crypto_id:
                try:
                    cryptocurrency = Cryptocurrency.objects.get(id=crypto_id)
                    new_transaction.cryptocurrency_id = cryptocurrency.id
                except Cryptocurrency.DoesNotExist:
                    messages.error(request, 'Invalid cryptocurrency selected.')
                    return redirect('main:deposit')
            
            # Require payment proof for crypto deposits
            if 'payment_proof' not in request.FILES:
                messages.error(request, 'Please upload payment proof for cryptocurrency deposits.')
                return redirect('main:deposit')
            new_transaction.payment_proof = request.FILES['payment_proof']
        
        new_transaction.save()
        
        try:
            send_deposit_confirmation_email(request.user, new_transaction)
        except Exception as e:
            logger.error(f"Error sending deposit confirmation email: {e}")
        
        messages.success(request, 'Deposit request submitted successfully.')
        return redirect('main:dashboard')
    
    deposits = Transaction.objects.filter(
        user=request.user,
        transaction_type='deposit'
    ).order_by('-created_at')[:5]
    
    context = {
        'kyc_approved': kyc_approved,
        'deposits': deposits,
        'cryptocurrencies': cryptocurrencies,
        'profile': profile,
        'currency': profile.currency
    }
    return render(request, 'main/deposit.html', context)

@login_required
def withdraw(request):
    try:
        kyc = KYCVerification.objects.get(user=request.user)
        kyc_approved = kyc.status == 'approved'
    except KYCVerification.DoesNotExist:
        kyc_approved = False
    
    cryptocurrencies = Cryptocurrency.objects.filter(is_active=True)
    profile = request.user.profile
    wallet_addresses = request.user.wallet_addresses.filter(is_active=True)
    
    if request.method == 'POST' and kyc_approved:
        try:
            amount = Decimal(request.POST.get('amount'))
        except (ValueError, TypeError):
            logger.error(f"Invalid withdrawal amount: {request.POST.get('amount')}")
            messages.error(request, 'Invalid withdrawal amount.')
            return redirect('main:withdraw')
            
        wallet_id = request.POST.get('wallet_id')
        
        if amount > profile.balance:
            messages.error(request, f'Insufficient balance for withdrawal: {amount} {profile.currency} > {profile.balance} {profile.currency}')
            return redirect('main:withdraw')
        
        try:
            wallet = request.user.wallet_addresses.get(id=wallet_id)
        except WalletAddress.DoesNotExist:
            messages.error(request, 'Invalid wallet address selected.')
            return redirect('main:withdraw')
        
        # Store details in session for authentication
        request.session['pending_withdrawal'] = {
            'amount': str(amount),
            'wallet_id': wallet_id,
            'cryptocurrency_id': wallet.cryptocurrency.id
        }
        request.session.modified = True
        return redirect('main:withdrawal_auth')
    
    withdrawals = Transaction.objects.filter(
        user=request.user,
        transaction_type='withdrawal'
    ).order_by('-created_at')[:5]
    
    context = {
        'kyc_approved': kyc_approved,
        'withdrawals': withdrawals,
        'balance': profile.balance,
        'currency': profile.currency,
        'cryptocurrencies': cryptocurrencies,
        'wallet_addresses': wallet_addresses,
        'profile': profile
    }
    return render(request, 'main/withdraw.html', context)

@login_required
def investments(request):
    try:
        kyc = KYCVerification.objects.get(user=request.user)
        kyc_approved = kyc.status == 'approved'
    except KYCVerification.DoesNotExist:
        kyc_approved = False
    
    profile = request.user.profile
    
    if not kyc_approved:
        messages.warning(request, 'You need to complete KYC verification to access investment features.')
        return redirect('main:kyc_verification')
    
    plans = InvestmentPlan.objects.filter(is_active=True)
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        try:
            amount = Decimal(request.POST.get('amount'))
        except (ValueError, TypeError):
            logger.error(f"Invalid amount provided for user {request.user.username}: {request.POST.get('amount')}")
            messages.error(request, 'Invalid investment amount.')
            return redirect('main:investments')
        
        if not plan_id:
            logger.error(f"No plan_id provided for user {request.user.username}")
            messages.error(request, 'No investment plan selected.')
            return redirect('main:investments')
        
        try:
            plan = InvestmentPlan.objects.get(id=plan_id, is_active=True)
            
            if amount < plan.min_deposit or amount > plan.max_deposit:
                logger.warning(f"Investment amount {amount} {profile.currency} out of range for plan {plan.name} (min: {plan.min_deposit}, max: {plan.max_deposit})")
                messages.error(request, f'Investment amount must be between {plan.min_deposit} {profile.currency} and {plan.max_deposit} {profile.currency}.')
                return redirect('main:investments')
            
            if amount > profile.balance:
                logger.warning(f"Insufficient balance for user {request.user.username}: {amount} {profile.currency} > {profile.balance} {profile.currency}")
                messages.error(request, f'Insufficient balance for investment: {amount} {profile.currency} > {profile.balance} {profile.currency}')
                return redirect('main:investments')
            
            with transaction.atomic():
                logger.info(f"Creating investment for user {request.user.username}, amount: {amount} {profile.currency}, plan: {plan.name}")
                
                # Create investment
                investment = Investment(
                    user=request.user,
                    plan=plan,
                    amount=amount,
                    status='active'
                )
                investment.save()
                
                # Create transaction record
                new_transaction = Transaction(
                    user=request.user,
                    transaction_type='investment',
                    amount=amount,
                    payment_method='internal',
                    status='completed',
                    completed_at=timezone.now()
                )
                new_transaction.save()
                
                logger.info(f"Investment transaction created: ID {new_transaction.id}, amount: {amount} {profile.currency}")
                
                messages.success(
                    request, 
                    f'Investment of {amount} {profile.currency} in {plan.name} plan successful.'
                )
                return redirect('main:dashboard')
            
        except InvestmentPlan.DoesNotExist:
            logger.error(f"Investment plan {plan_id} does not exist for user {request.user.username}")
            messages.error(request, 'Invalid investment plan selected.')
            return redirect('main:investments')
    
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    ).order_by('-start_date')
    
    completed_investments = Investment.objects.filter(
        user=request.user,
        status='completed'
    ).order_by('-end_date')[:10]
    
    context = {
        'plans': plans,
        'active_investments': active_investments,
        'completed_investments': completed_investments,
        'balance': profile.balance,
        'currency': profile.currency,
        'investment': profile.investment,
        'profile': profile
    }
    return render(request, 'main/investments.html', context)

@login_required
def dashboard(request):
    try:
        kyc = KYCVerification.objects.get(user=request.user)
        if kyc.status not in ['approved', 'submitted']:
            messages.warning(request, 'Please complete KYC verification to access your dashboard.')
            return redirect('main:kyc_verification')
        kyc_status = kyc.status
    except KYCVerification.DoesNotExist:
        messages.warning(request, 'Please complete KYC verification to access your dashboard.')
        return redirect('main:kyc_verification')
    
    profile = request.user.profile
    transactions = Transaction.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    total_deposits = Transaction.objects.filter(
        user=request.user, 
        transaction_type='deposit',
        status='completed'
    ).count()
    
    total_withdrawals = Transaction.objects.filter(
        user=request.user, 
        transaction_type='withdrawal',
        status='completed'
    ).count()
    
    active_investments = Investment.objects.filter(
        user=request.user,
        status='active'
    ).order_by('-start_date')[:3]
    
    context = {
        'profile': profile,
        'transactions': transactions,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'active_investments': active_investments,
        'kyc_status': kyc_status,
        'balance': profile.balance,
        'currency': profile.currency,
        'profit': profile.profit,
        'bonus': profile.bonus,
        'investment': profile.investment
    }
    return render(request, 'main/dashboard.html', context)

@login_required
def settings(request):
    profile = request.user.profile
    cryptocurrencies = Cryptocurrency.objects.filter(is_active=True)
    wallet_addresses = request.user.wallet_addresses.filter(is_active=True)
    
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            form = UserProfileForm(request.POST, instance=profile, user=request.user)
            if form.is_valid():
                form.save()
                logger.info(f"Profile updated for user {request.user.username}: currency={form.cleaned_data['currency']}")
                messages.success(request, 'Profile updated successfully.')
                return redirect('main:settings')
            else:
                logger.error(f"Profile update failed for user {request.user.username}: {form.errors}")
                for error in form.errors.values():
                    messages.error(request, error)
        
        elif 'add_wallet' in request.POST:
            crypto_id = request.POST.get('cryptocurrency')
            wallet_address = request.POST.get('wallet_address')
            if crypto_id and wallet_address:
                try:
                    cryptocurrency = Cryptocurrency.objects.get(id=crypto_id)
                    WalletAddress.objects.create(
                        user=request.user,
                        cryptocurrency=cryptocurrency,
                        address=wallet_address
                    )
                    messages.success(request, 'Wallet address added successfully.')
                except Cryptocurrency.DoesNotExist:
                    messages.error(request, 'Invalid cryptocurrency selected.')
                return redirect('main:settings')
            else:
                messages.error(request, 'Please provide both cryptocurrency and wallet address.')
            return redirect('main:settings')
        
        elif 'delete_wallet' in request.POST:
            wallet_id = request.POST.get('wallet_id')
            try:
                wallet = WalletAddress.objects.get(id=wallet_id, user=request.user)
                wallet.delete()
                messages.success(request, 'Wallet address deleted successfully.')
            except WalletAddress.DoesNotExist:
                messages.error(request, 'Invalid wallet address.')
            return redirect('main:settings')
        
        elif 'password_change' in request.POST:
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('main:settings')
            
            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
                return redirect('main:settings')
            
            request.user.set_password(new_password)
            request.user.save()
            
            user = authenticate(request, username=request.user.username, password=new_password)
            login(request, user)
            
            logger.info(f"Password changed for user {request.user.username}")
            messages.success(request, 'Password changed successfully.')
            return redirect('main:settings')
    
    else:
        form = UserProfileForm(instance=profile, user=request.user)
    
    context = {
        'form': form,
        'cryptocurrencies': cryptocurrencies,
        'wallet_addresses': wallet_addresses,
        'profile': profile,
        'currency': profile.currency
    }
    return render(request, 'main/settings.html', context)

@login_required
def withdrawal_auth(request):
    if 'pending_withdrawal' not in request.session:
        messages.error(request, 'No pending withdrawal found.')
        return redirect('main:withdraw')
    
    withdrawal_data = request.session['pending_withdrawal']
    
    if request.method == 'POST':
        code = request.POST.get('auth_code')
        try:
            withdrawal_code = WithdrawalCode.objects.get(user=request.user)
            if code != withdrawal_code.code:
                messages.error(request, 'Invalid withdrawal code.')
                return redirect('main:withdrawal_auth')
            
            amount = Decimal(withdrawal_data['amount'])
            wallet_id = withdrawal_data['wallet_id']
            crypto_id = withdrawal_data['cryptocurrency_id']
            
            profile = request.user.profile
            if amount > profile.balance:
                messages.error(request, f'Insufficient balance for withdrawal: {amount} {profile.currency} > {profile.balance} {profile.currency}')
                return redirect('main:withdraw')
            
            wallet = WalletAddress.objects.get(id=wallet_id, user=request.user)
            
            profile.balance -= amount
            profile.save()
            
            new_transaction = Transaction(
                user=request.user,
                transaction_type='withdrawal',
                amount=amount,
                wallet_address=wallet.address,
                status='pending',
                cryptocurrency_id=crypto_id
            )
            new_transaction.save()
            
            try:
                send_withdrawal_confirmation_email(request.user, new_transaction)
            except Exception as e:
                logger.error(f"Error sending withdrawal confirmation email: {e}")
            
            # Clear session data
            del request.session['pending_withdrawal']
            request.session.modified = True
            
            messages.success(request, 'Withdrawal request submitted successfully.')
            return redirect('main:dashboard')
        
        except WithdrawalCode.DoesNotExist:
            messages.error(request, 'No withdrawal code assigned. Please contact support.')
            return redirect('main:withdraw')
    
    return render(request, 'main/withdrawal_auth.html')

# Static Pages
def home(request):
    return render(request, 'main/home.html')

def about(request):
    return render(request, 'main/about.html')

def terms(request):
    return render(request, 'main/terms.html')

def privacy(request):
    return render(request, 'main/privacy.html')

def demo(request):
    return render(request, 'main/demo.html')

# Custom Error Views
def custom_404(request, exception):
    logger.error(f"404 Error: {request.path}")
    return render(request, 'main/404.html', status=404)

def custom_403(request, exception):
    logger.error(f"403 Error: {request.path} - User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
    return render(request, 'main/403.html', status=403)

def custom_500(request):
    logger.error(f"500 Error: {request.path}")
    return render(request, 'main/500.html', status=500)