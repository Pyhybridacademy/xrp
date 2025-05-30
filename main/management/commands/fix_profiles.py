from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal
from main.models import UserProfile, Trade, Transaction

class Command(BaseCommand):
    help = 'Fix user profile balances, profits, and losses'

    def handle(self, *args, **options):
        users = User.objects.all()
        self.stdout.write(f"Checking {users.count()} user profiles...")
        
        for user in users:
            try:
                profile = user.profile
                self.stdout.write(f"Processing {user.username}...")
                
                # Get completed deposits
                deposits = Transaction.objects.filter(
                    user=user,
                    transaction_type='deposit',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                # Get completed withdrawals
                withdrawals = Transaction.objects.filter(
                    user=user,
                    transaction_type='withdrawal',
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                # Get open trades (money currently in trades)
                open_trades = Trade.objects.filter(
                    user=user,
                    status='open'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                # Get closed trades with profit
                profits = Trade.objects.filter(
                    user=user,
                    status='closed',
                    result='profit'
                ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
                
                # Get closed trades with loss (stored as negative values)
                losses_from_trades = Trade.objects.filter(
                    user=user,
                    status='closed',
                    result='loss'
                ).aggregate(total=Sum('profit_loss'))['total'] or Decimal('0')
                losses = abs(losses_from_trades)  # Convert to positive for the loss field
                
                # Calculate expected balance
                # Start with deposits
                expected_balance = deposits
                # Subtract withdrawals
                expected_balance -= withdrawals
                # Subtract open trades (money tied up in trades)
                expected_balance -= open_trades
                
                # For closed trades, we need to add back the principal and the profit/loss
                closed_trades = Trade.objects.filter(user=user, status='closed')
                for trade in closed_trades:
                    # Add back the principal amount
                    expected_balance += trade.amount
                    # Add the profit or loss (profit_loss is positive for profit, negative for loss)
                    expected_balance += trade.profit_loss
                
                # Print current values
                self.stdout.write(f"  Current balance: {profile.balance}")
                self.stdout.write(f"  Current profit: {profile.profit}")
                self.stdout.write(f"  Current loss: {profile.loss}")
                
                # Print expected values
                self.stdout.write(f"  Expected balance: {expected_balance}")
                self.stdout.write(f"  Expected profit: {profits}")
                self.stdout.write(f"  Expected loss: {losses}")
                
                # Update if different
                if (profile.balance != expected_balance or 
                    profile.profit != profits or 
                    profile.loss != losses):
                    
                    self.stdout.write(self.style.WARNING(f"  Updating {user.username}'s profile..."))
                    
                    profile.balance = expected_balance
                    profile.profit = profits
                    profile.loss = losses
                    profile.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"  Updated {user.username}'s profile successfully"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"  {user.username}'s profile is correct"))
                
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"No profile found for {user.username}"))
