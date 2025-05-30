from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from django.utils import timezone
import logging

# Set up logging
logger = logging.getLogger(__name__)

CURRENCY_CHOICES = (
    ('USD', 'US Dollar ($)'),
    ('EUR', 'Euro (€)'),
    ('GBP', 'British Pound (£)'),
    ('NGN', 'Nigerian Naira (₦)'),
    ('GHS', 'Ghanaian Cedi (₵)'),
    ('KES', 'Kenyan Shilling (KSh)'),
    ('ZAR', 'South African Rand (R)'),
    ('INR', 'Indian Rupee (₹)'),
    ('AUD', 'Australian Dollar (A$)'),
    ('CAD', 'Canadian Dollar (C$)'),
)

class InvestmentPlan(models.Model):
    PLAN_TYPES = (
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('vip', 'VIP'),
        ('platinum', 'Platinum'),
        ('gold', 'Gold'),
    )
    
    name = models.CharField(max_length=50, choices=PLAN_TYPES)
    min_deposit = models.DecimalField(max_digits=15, decimal_places=2)
    max_deposit = models.DecimalField(max_digits=15, decimal_places=2)
    roi_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    duration_days = models.IntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.get_name_display()} Plan ({self.min_deposit} - {self.max_deposit})"

class Cryptocurrency(models.Model):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    wallet_address = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='crypto_logos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"
    
    class Meta:
        verbose_name_plural = "Cryptocurrencies"

# main/models.py
class WalletAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_addresses')
    cryptocurrency = models.ForeignKey('Cryptocurrency', on_delete=models.CASCADE)
    address = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s {self.cryptocurrency.name} Wallet"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    investment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    preferred_cryptocurrency = models.ForeignKey('Cryptocurrency', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class KYCVerification(models.Model):
    ID_TYPES = (
        ('passport', 'Passport'),
        ('drivers_license', 'Driver\'s License'),
        ('national_id', 'National ID'),
    )
    
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    id_type = models.CharField(max_length=20, choices=ID_TYPES)
    id_number = models.CharField(max_length=50)
    id_front = models.ImageField(upload_to='kyc_documents/', null=True)
    id_back = models.ImageField(upload_to='kyc_documents/', null=True)
    selfie = models.ImageField(upload_to='kyc_documents/', null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    rejection_reason = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s KYC Verification"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('investment', 'Investment'),
        ('profit', 'Profit Payment'),
        ('bonus', 'Bonus Payment'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    )
    
    PAYMENT_METHODS = (
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('crypto', 'Cryptocurrency'),
        ('internal', 'Internal Transfer'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True)
    cryptocurrency = models.ForeignKey('Cryptocurrency', on_delete=models.SET_NULL, null=True, blank=True)
    wallet_address = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    payment_proof = models.ImageField(upload_to='payment_proofs/', null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s {self.get_transaction_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        is_newly_completed = False
        if self.pk:
            try:
                old_transaction = Transaction.objects.get(pk=self.pk)
                if old_transaction.status != 'completed' and self.status == 'completed':
                    is_newly_completed = True
                    self.completed_at = timezone.now()
            except Transaction.DoesNotExist:
                pass
        elif self.status == 'completed':
            is_newly_completed = True
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        if is_newly_completed:
            logger.info(f"Transaction {self.id} (Type: {self.transaction_type}, Amount: {self.amount}, User: {self.user.username}) is newly completed. Updating balance.")
            self.update_user_balance()
    
    def update_user_balance(self):
        profile = self.user.profile
        logger.info(f"Before update - User: {self.user.username}, Balance: {profile.balance}, Profit: {profile.profit}, Bonus: {profile.bonus}, Investment: {profile.investment}")
        
        if self.transaction_type == 'deposit' and self.status == 'completed':
            profile.balance += self.amount
        elif self.transaction_type == 'withdrawal' and self.status == 'completed':
            profile.balance -= self.amount
        elif self.transaction_type == 'investment' and self.status == 'completed':
            profile.balance -= self.amount
            profile.investment += self.amount
        elif self.transaction_type == 'profit' and self.status == 'completed':
            profile.profit += self.amount
            profile.balance += self.amount
        elif self.transaction_type == 'bonus' and self.status == 'completed':
            profile.bonus += self.amount
            profile.balance += self.amount
        
        profile.save()
        logger.info(f"After update - User: {self.user.username}, Balance: {profile.balance}, Profit: {profile.profit}, Bonus: {profile.bonus}, Investment: {profile.investment}")

class Investment(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(InvestmentPlan, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    expected_return = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    
    def __str__(self):
        return f"{self.user.username}'s {self.plan.get_name_display()} Investment - {self.amount}"
    
    def save(self, *args, **kwargs):
        if self.pk is None:  # Only on creation
            roi_percentage = self.plan.roi_percentage / Decimal('100')
            self.expected_return = self.amount + (self.amount * roi_percentage)
            self.end_date = timezone.now() + timezone.timedelta(days=self.plan.duration_days)
        
        super().save(*args, **kwargs)


class SiteSettings(models.Model):  # New model for site settings
    site_name = models.CharField(max_length=100, default='Trading Platform')
    logo = models.ImageField(upload_to='site/logo/', null=True, blank=True)
    contact_email = models.EmailField(max_length=254, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    live_chat_enabled = models.BooleanField(default=False)
    live_chat_script_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return "Site Settings"
    
class WithdrawalCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='withdrawal_code')
    code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Withdrawal Code"