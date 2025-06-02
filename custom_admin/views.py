from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import authenticate, login, update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from main.models import UserProfile, KYCVerification, Transaction, Cryptocurrency, Investment, InvestmentPlan, SiteSettings, WithdrawalCode
from main.utils import send_kyc_status_email, send_bonus_email
import logging
from decimal import Decimal

logger = logging.getLogger('custom_admin')

# Decorator to restrict access to superusers
def superuser_required():
    def check_superuser(user):
        return user.is_authenticated and user.is_superuser
    return user_passes_test(check_superuser, login_url='custom_admin:login')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            logger.info(f"Admin {username} logged in")
            return redirect('custom_admin:dashboard')
        else:
            messages.error(request, 'Invalid credentials or not a superuser.')
            logger.warning(f"Failed login attempt for {username}")
    return render(request, 'custom_admin/login.html')

@superuser_required()
def admin_password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            logger.info(f"Admin {request.user.username} changed password")
            messages.success(request, 'Password changed successfully.')
            return redirect('custom_admin:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'custom_admin/password_change.html', {'form': form})

@superuser_required()
def admin_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        request.user.username = request.POST.get('username')
        request.user.email = request.POST.get('email')
        profile.full_name = request.POST.get('full_name')
        profile.phone = request.POST.get('phone')
        profile.country = request.POST.get('country')
        request.user.save()
        profile.save()
        logger.info(f"Admin {request.user.username} updated profile")
        messages.success(request, 'Profile updated successfully.')
        return redirect('custom_admin:profile')
    return render(request, 'custom_admin/profile.html', {'user': request.user, 'profile': profile})

@superuser_required()
def admin_dashboard(request):
    user_count = User.objects.count()
    kyc_pending = KYCVerification.objects.filter(status='submitted').count()
    transaction_pending = Transaction.objects.filter(status='pending').count()
    active_investments = Investment.objects.filter(status='active').count()
    
    context = {
        'user_count': user_count,
        'kyc_pending': kyc_pending,
        'transaction_pending': transaction_pending,
        'active_investments': active_investments,
    }
    return render(request, 'custom_admin/dashboard.html', context)

@superuser_required()
def user_list(request):
    users = User.objects.all().select_related('profile')
    context = {'users': users}
    return render(request, 'custom_admin/user_list.html', context)

@superuser_required()
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    context = {'user': user}
    return render(request, 'custom_admin/user_detail.html', context)

@superuser_required()
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        profile.full_name = request.POST.get('full_name')
        profile.phone = request.POST.get('phone')
        profile.country = request.POST.get('country')
        profile.currency = request.POST.get('currency', 'USD')
        profile.balance = request.POST.get('balance')
        profile.profit = request.POST.get('profit')
        profile.bonus = request.POST.get('bonus')
        profile.investment = request.POST.get('investment')
        
        user.save()
        profile.save()
        logger.info(f"Admin updated user {user.username} (ID: {user.id})")
        messages.success(request, 'User updated successfully.')
        return redirect('custom_admin:user_detail', user_id=user.id)
    
    context = {'user': user}
    return render(request, 'custom_admin/user_edit.html', context)

@superuser_required()
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        logger.info(f"Admin deleted user {username} (ID: {user_id})")
        messages.success(request, 'User deleted successfully.')
        return redirect('custom_admin:user_list')
    context = {'user': user}
    return render(request, 'custom_admin/user_delete.html', context)

@superuser_required()
def user_add_bonus(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    if request.method == 'POST':
        bonus_amount = request.POST.get('bonus_amount')
        add_to_balance = request.POST.get('add_to_balance') == 'on'
        try:
            bonus_amount = Decimal(bonus_amount)
            if bonus_amount <= 0:
                raise ValueError("Bonus amount must be positive")
            profile.bonus += bonus_amount
            if add_to_balance:
                profile.balance += bonus_amount
            profile.save()
            try:
                send_bonus_email(user, bonus_amount, add_to_balance)
                logger.info(f"Admin added bonus {bonus_amount} to user {user.username} (ID: {user_id})")
            except Exception as e:
                logger.error(f"Error sending bonus email to {user.username}: {e}")
            messages.success(request, f"Bonus of {profile.currency} {bonus_amount} added successfully.")
            return redirect('custom_admin:user_detail', user_id=user.id)
        except ValueError as e:
            messages.error(request, str(e) or 'Invalid bonus amount.')
    return render(request, 'custom_admin/user_add_bonus.html', {'user': user})

@superuser_required()
def user_reset_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not new_password or len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'custom_admin/user_reset_password.html', {'user': user})
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'custom_admin/user_reset_password.html', {'user': user})
        
        user.set_password(new_password)
        user.save()
        logger.info(f"Admin reset password for user {user.username} (ID: {user_id})")
        messages.success(request, f"Password for {user.username} reset successfully. The user can now log in with the new password and change it in their settings.")
        return redirect('custom_admin:user_detail', user_id=user.id)
    
    return render(request, 'custom_admin/user_reset_password.html', {'user': user})

@superuser_required()
def login_as_user(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can perform this action.')
        return redirect('custom_admin:user_detail', user_id=user_id)
    
    # Store admin user ID before logout
    admin_user_id = request.user.id
    logger.debug(f"Before impersonation: admin_user_id={admin_user_id}, session={request.session.items()}")
    
    # Set session variables for impersonation
    request.session['admin_user_id'] = admin_user_id
    request.session['is_impersonating'] = True
    request.session.modified = True
    logger.debug(f"After setting session: session={request.session.items()}")
    
    # Log out the admin
    logout(request)
    
    # Log in as the target user, specifying the backend
    login(request, target_user, backend='main.authentication.EmailOrUsernameModelBackend')
    
    # Verify session state after login
    logger.debug(f"After login as {target_user.username}: session={request.session.items()}")
    
    # Log the action
    logger.info(f"Admin {admin_user_id} started impersonating user {target_user.username} (ID: {user_id})")
    messages.info(request, f"You are now logged in as {target_user.username}.")
    return redirect('main:dashboard')

@superuser_required()
def exit_login_as_user(request):
    admin_user_id = request.session.get('admin_user_id')
    is_impersonating = request.session.get('is_impersonating')
    
    if not admin_user_id or not is_impersonating:
        logger.warning("Attempted to exit impersonation without active session.")
        messages.error(request, 'No active impersonation session.')
        return redirect('custom_admin:dashboard')
    
    # Get the admin user
    admin_user = get_object_or_404(User, id=admin_user_id)
    
    # Log out the impersonated user and log in as the admin
    current_user = request.user
    logout(request)
    login(request, admin_user)
    
    # Clear impersonation session data
    request.session.pop('admin_user_id', None)
    request.session.pop('is_impersonating', None)
    request.session.modified = True
    
    logger.info(f"Admin {admin_user.username} stopped impersonating user {current_user.username}")
    messages.success(request, 'Returned to admin session.')
    return redirect('custom_admin:dashboard')

    
@superuser_required()
def kyc_list(request):
    kycs = KYCVerification.objects.all().select_related('user')
    context = {'kycs': kycs}
    return render(request, 'custom_admin/kyc_list.html', context)

@superuser_required()
def kyc_detail(request, kyc_id):
    kyc = get_object_or_404(KYCVerification, id=kyc_id)
    if not kyc.id_front or not kyc.id_back or not kyc.selfie:
        logger.warning(f"KYC ID {kyc_id} for user {kyc.user.username} is missing files: "
                      f"id_front={'present' if kyc.id_front else 'missing'}, "
                      f"id_back={'present' if kyc.id_back else 'missing'}, "
                      f"selfie={'present' if kyc.selfie else 'missing'}")
    context = {'kyc': kyc}
    return render(request, 'custom_admin/kyc_detail.html', context)

@superuser_required()
def kyc_approve(request, kyc_id):
    kyc = get_object_or_404(KYCVerification, id=kyc_id)
    if request.method == 'POST':
        kyc.status = 'approved'
        kyc.reviewed_at = timezone.now()
        kyc.save()
        try:
            send_kyc_status_email(kyc.user, kyc, 'approved')
            logger.info(f"Admin approved KYC for user {kyc.user.username} (KYC ID: {kyc_id})")
        except Exception as e:
            logger.error(f"Error sending KYC approval email for user {kyc.user.username}: {e}")
        messages.success(request, 'KYC approved successfully.')
        return redirect('custom_admin:kyc_list')
    context = {'kyc': kyc}
    return render(request, 'custom_admin/kyc_approve.html', context)

@superuser_required()
def kyc_reject(request, kyc_id):
    kyc = get_object_or_404(KYCVerification, id=kyc_id)
    if request.method == 'POST':
        kyc.status = 'rejected'
        kyc.reviewed_at = timezone.now()
        kyc.save()
        try:
            send_kyc_status_email(kyc.user, kyc, 'rejected')
            logger.info(f"Admin rejected KYC for user {kyc.user.username} (KYC ID: {kyc_id})")
        except Exception as e:
            logger.error(f"Error sending KYC rejection email for user {kyc.user.username}: {e}")
        messages.success(request, 'KYC rejected successfully.')
        return redirect('custom_admin:kyc_list')
    context = {'kyc': kyc}
    return render(request, 'custom_admin/kyc_reject.html', context)

@superuser_required()
def transaction_list(request):
    transactions = Transaction.objects.all().select_related('user', 'cryptocurrency')
    context = {'transactions': transactions}
    return render(request, 'custom_admin/transaction_list.html', context)

@superuser_required()
def transaction_detail(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)
    context = {'transaction': transaction}
    return render(request, 'custom_admin/transaction_detail.html', context)

@superuser_required()
def transaction_approve(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)
    if request.method == 'POST':
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save()
        logger.info(f"Admin approved transaction {transaction.id} for user {transaction.user.username}")
        messages.success(request, 'Transaction approved successfully.')
        return redirect('custom_admin:transaction_list')
    context = {'transaction': transaction}
    return render(request, 'custom_admin/transaction_approve.html', context)

@superuser_required()
def transaction_reject(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)
    if request.method == 'POST':
        transaction.status = 'rejected'
        transaction.completed_at = timezone.now()
        transaction.save()
        logger.info(f"Admin rejected transaction {transaction.id} for user {transaction.user.username}")
        messages.success(request, 'Transaction rejected successfully.')
        return redirect('custom_admin:transaction_list')
    context = {'transaction': transaction}
    return render(request, 'custom_admin/transaction_reject.html', context)

@superuser_required()
def investment_list(request):
    investments = Investment.objects.all().select_related('user', 'plan')
    context = {'investments': investments}
    return render(request, 'custom_admin/investment_list.html', context)

@superuser_required()
def investment_detail(request, investment_id):
    investment = get_object_or_404(Investment, id=investment_id)
    context = {'investment': investment}
    return render(request, 'custom_admin/investment_detail.html', context)

@superuser_required()
def investment_complete(request, investment_id):
    investment = get_object_or_404(Investment, id=investment_id)
    # Calculate profit and total return for template
    roi_percentage = investment.plan.roi_percentage
    profit = (investment.amount * Decimal(roi_percentage)) / Decimal(100)
    total_return = investment.amount + profit
    
    if request.method == 'POST':
        if investment.status == 'active':
            # Update UserProfile
            profile = investment.user.profile
            profile.profit += profit
            profile.balance += total_return  # Return initial amount + profit
            profile.save()
            
            # Update Investment
            investment.status = 'completed'
            investment.end_date = timezone.now()
            investment.save()
            
            logger.info(f"Admin completed investment {investment.id} for user {investment.user.username} with profit {profit}")
            messages.success(request, f"Investment completed. Profit of {profile.currency} {profit} added to user's balance.")
        else:
            messages.error(request, 'Only active investments can be completed.')
        return redirect('custom_admin:investment_detail', investment_id=investment.id)
    
    context = {
        'investment': investment,
        'profit': profit,
        'total_return': total_return,
    }
    return render(request, 'custom_admin/investment_complete.html', context)

@superuser_required()
def plan_list(request):
    plans = InvestmentPlan.objects.all()
    context = {'plans': plans}
    return render(request, 'custom_admin/plan_list.html', context)

@superuser_required()
def plan_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        min_deposit = request.POST.get('min_deposit')
        max_deposit = request.POST.get('max_deposit')
        duration_days = request.POST.get('duration_days')
        roi_percentage = request.POST.get('roi_percentage')
        is_active = request.POST.get('is_active') == 'on'
        
        plan = InvestmentPlan(
            name=name,
            min_deposit=min_deposit,
            max_deposit=max_deposit,
            duration_days=duration_days,
            roi_percentage=roi_percentage,
            is_active=is_active
        )
        plan.save()
        logger.info(f"Admin created investment plan {plan.name} (ID: {plan.id})")
        messages.success(request, 'Investment plan created successfully.')
        return redirect('custom_admin:plan_list')
    
    return render(request, 'custom_admin/plan_create.html')

@superuser_required()
def plan_edit(request, plan_id):
    plan = get_object_or_404(InvestmentPlan, id=plan_id)
    if request.method == 'POST':
        plan.name = request.POST.get('name')
        plan.min_deposit = request.POST.get('min_deposit')
        plan.max_deposit = request.POST.get('max_deposit')
        plan.duration_days = request.POST.get('duration_days')
        plan.roi_percentage = request.POST.get('roi_percentage')
        plan.is_active = request.POST.get('is_active') == 'on'
        plan.save()
        logger.info(f"Admin updated investment plan {plan.name} (ID: {plan.id})")
        messages.success(request, 'Investment plan updated successfully.')
        return redirect('custom_admin:plan_list')
    
    context = {'plan': plan}
    return render(request, 'custom_admin/plan_edit.html', context)

@superuser_required()
def plan_delete(request, plan_id):
    plan = get_object_or_404(InvestmentPlan, id=plan_id)
    if request.method == 'POST':
        name = plan.name
        plan.delete()
        logger.info(f"Admin deleted investment plan {name} (ID: {plan_id})")
        messages.success(request, 'Investment plan deleted successfully.')
        return redirect('custom_admin:plan_list')
    context = {'plan': plan}
    return render(request, 'custom_admin/plan_delete.html', context)

@superuser_required()
def crypto_list(request):
    cryptocurrencies = Cryptocurrency.objects.all()
    context = {'cryptocurrencies': cryptocurrencies}
    return render(request, 'custom_admin/crypto_list.html', context)

@superuser_required()
def crypto_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        symbol = request.POST.get('symbol')
        wallet_address = request.POST.get('wallet_address')
        is_active = request.POST.get('is_active') == 'on'
        
        crypto = Cryptocurrency(
            name=name,
            symbol=symbol,
            wallet_address=wallet_address,
            is_active=is_active
        )
        crypto.save()
        logger.info(f"Admin created cryptocurrency {crypto.name} (ID: {crypto.id})")
        messages.success(request, 'Cryptocurrency created successfully.')
        return redirect('custom_admin:crypto_list')
    
    return render(request, 'custom_admin/crypto_create.html')

@superuser_required()
def crypto_edit(request, crypto_id):
    crypto = get_object_or_404(Cryptocurrency, id=crypto_id)
    if request.method == 'POST':
        crypto.name = request.POST.get('name')
        crypto.symbol = request.POST.get('symbol')
        crypto.wallet_address = request.POST.get('wallet_address')
        crypto.is_active = request.POST.get('is_active') == 'on'
        crypto.save()
        logger.info(f"Admin updated cryptocurrency {crypto.name} (ID: {crypto.id})")
        messages.success(request, 'Cryptocurrency updated successfully.')
        return redirect('custom_admin:crypto_list')
    
    context = {'crypto': crypto}
    return render(request, 'custom_admin/crypto_edit.html', context)

@superuser_required()
def crypto_delete(request, crypto_id):
    crypto = get_object_or_404(Cryptocurrency, id=crypto_id)
    if request.method == 'POST':
        name = crypto.name
        crypto.delete()
        logger.info(f"Admin deleted cryptocurrency {name} (ID: {crypto_id})")
        messages.success(request, 'Cryptocurrency deleted successfully.')
        return redirect('custom_admin:crypto_list')
    context = {'crypto': crypto}
    return render(request, 'custom_admin/crypto_delete.html', context)

@superuser_required()
def site_settings(request):
    settings, _ = SiteSettings.objects.get_or_create(id=1)
    if request.method == 'POST':
        settings.site_name = request.POST.get('site_name')
        settings.contact_email = request.POST.get('contact_email')
        settings.contact_phone = request.POST.get('contact_phone')
        settings.live_chat_enabled = request.POST.get('live_chat_enabled') == 'on'
        settings.live_chat_script_url = request.POST.get('live_chat_script_url')
        if 'logo' in request.FILES:
            settings.logo = request.FILES['logo']
        settings.save()
        logger.info(f"Admin updated site settings")
        messages.success(request, 'Site settings updated successfully.')
        return redirect('custom_admin:site_settings')
    return render(request, 'custom_admin/site_settings.html', {'settings': settings})

@superuser_required()
def withdrawal_code_list(request):
    codes = WithdrawalCode.objects.all().select_related('user')
    context = {'codes': codes}
    return render(request, 'custom_admin/withdrawal_code_list.html', context)

@superuser_required()
def withdrawal_code_create(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        code = request.POST.get('code')
        try:
            user = User.objects.get(id=user_id)
            if WithdrawalCode.objects.filter(user=user).exists():
                messages.error(request, 'User already has a withdrawal code.')
            else:
                WithdrawalCode.objects.create(user=user, code=code)
                logger.info(f"Admin created withdrawal code for user {user.username}")
                messages.success(request, 'Withdrawal code created successfully.')
            return redirect('custom_admin:withdrawal_code_list')
        except User.DoesNotExist:
            messages.error(request, 'Invalid user selected.')
    
    users = User.objects.all()
    context = {'users': users}
    return render(request, 'custom_admin/withdrawal_code_create.html', context)

@superuser_required()
def withdrawal_code_edit(request, code_id):
    code = get_object_or_404(WithdrawalCode, id=code_id)
    if request.method == 'POST':
        new_code = request.POST.get('code')
        code.code = new_code
        code.save()
        logger.info(f"Admin updated withdrawal code for user {code.user.username}")
        messages.success(request, 'Withdrawal code updated successfully.')
        return redirect('custom_admin:withdrawal_code_list')
    
    context = {'code': code}
    return render(request, 'custom_admin/withdrawal_code_edit.html', context)

@superuser_required()
def withdrawal_code_delete(request, code_id):
    code = get_object_or_404(WithdrawalCode, id=code_id)
    if request.method == 'POST':
        username = code.user.username
        code.delete()
        logger.info(f"Admin deleted withdrawal code for user {username}")
        messages.success(request, 'Withdrawal code deleted successfully.')
        return redirect('custom_admin:withdrawal_code_list')
    context = {'code': code}
    return render(request, 'custom_admin/withdrawal_code_delete.html', context)