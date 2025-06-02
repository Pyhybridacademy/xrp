from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from PIL import Image, ImageDraw, ImageFont
import random
import string
import io
import base64
import re
import logging
from .models import UserProfile

logger = logging.getLogger(__name__)

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    full_name = forms.CharField(max_length=100, required=True)
    phone = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=50, required=False)
    currency = forms.ChoiceField(choices=UserProfile.CURRENCY_CHOICES, required=False)
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput, label="")
    captcha_answer = forms.CharField(max_length=10, required=True, label="Enter the result shown in the image")

    BLACKLISTED_CHARS = r'[<>{};#&%`~]'

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def __init__(self, *args, captcha_answer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.captcha_answer = captcha_answer
        if self.data:
            logger.debug(f"Registration form POST data: {self.data}")

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) > 30:
            raise ValidationError("Username cannot exceed 30 characters.")
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        if re.search(self.BLACKLISTED_CHARS, username):
            raise ValidationError("Username contains invalid characters.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email address is already registered.")
        return email

    def clean_full_name(self):
        full_name = self.cleaned_data['full_name']
        if len(full_name) > 100:
            raise ValidationError("Full name cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z\s-]+$', full_name):
            raise ValidationError("Full name can only contain letters, spaces, and hyphens.")
        if re.search(self.BLACKLISTED_CHARS, full_name):
            raise ValidationError("Full name contains invalid characters.")
        return full_name

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if phone and not re.match(r'^\+?[\d\s-]{7,20}$', phone):
            raise ValidationError("Invalid phone number format.")
        return phone

    def clean_honeypot(self):
        honeypot = self.cleaned_data['honeypot']
        if honeypot:
            raise ValidationError("This field should be empty.")
        return honeypot

    def clean_captcha_answer(self):
        captcha_answer = self.cleaned_data.get('captcha_answer')
        correct_answer = self.captcha_answer
        logger.debug(f"Validating CAPTCHA: entered={captcha_answer}, correct={correct_answer}")
        
        if not captcha_answer or not correct_answer:
            logger.warning(f"Missing CAPTCHA data: entered={captcha_answer}, correct={correct_answer}")
            raise ValidationError("CAPTCHA answer is required.")
        
        entered_clean = str(captcha_answer).strip().lower()
        correct_clean = str(correct_answer).strip().lower()
        
        if entered_clean != correct_clean:
            logger.warning(f"Invalid CAPTCHA answer: entered={entered_clean}, correct={correct_clean}")
            raise ValidationError("Incorrect CAPTCHA answer. Please try again.")
        
        return captcha_answer

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_active = True  # Ensure user is active
        if commit:
            try:
                user.save()
                logger.debug(f"User saved in RegistrationForm: username={user.username}, id={user.id}, is_active={user.is_active}")
            except Exception as e:
                logger.error(f"Failed to save user in RegistrationForm: {e}")
                raise
        return user



class LoginForm(forms.Form):
    username_or_email = forms.CharField(max_length=254, required=True, label="Username or Email")
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput, label="")
    captcha_answer = forms.CharField(max_length=10, required=True, label="Enter the result shown in the image")

    BLACKLISTED_CHARS = r'[<>{};#&%`~]'

    def __init__(self, *args, captcha_answer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.captcha_answer = captcha_answer
        if self.data:
            logger.debug(f"Login form POST data: {self.data}")

    def clean_username_or_email(self):
        username_or_email = self.cleaned_data['username_or_email']
        if len(username_or_email) > 254:
            raise ValidationError("Input cannot exceed 254 characters.")
        if re.search(self.BLACKLISTED_CHARS, username_or_email):
            raise ValidationError("Input contains invalid characters.")
        return username_or_email

    def clean_honeypot(self):
        honeypot = self.cleaned_data['honeypot']
        if honeypot:
            raise ValidationError("This field should be empty.")
        return honeypot

    def clean_captcha_answer(self):
        captcha_answer = self.cleaned_data.get('captcha_answer')
        correct_answer = self.captcha_answer
        logger.debug(f"Validating CAPTCHA: entered={captcha_answer}, correct={correct_answer}")
        
        if not captcha_answer or not correct_answer:
            logger.warning(f"Missing CAPTCHA data: entered={captcha_answer}, correct={correct_answer}")
            raise ValidationError("CAPTCHA answer is required.")
        
        entered_clean = str(captcha_answer).strip().lower()
        correct_clean = str(correct_answer).strip().lower()
        
        if entered_clean != correct_clean:
            logger.warning(f"Invalid CAPTCHA answer: entered={entered_clean}, correct={correct_clean}")
            raise ValidationError("Incorrect CAPTCHA answer. Please try again.")
        
        return captcha_answer

class UserProfileForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = UserProfile
        fields = ['full_name', 'phone', 'country', 'currency']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['username'].initial = self.user.username
            self.fields['email'].initial = self.user.email
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if username != self.user.username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if email != self.user.email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email address is already registered.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.username = self.cleaned_data['username']
            self.user.email = self.cleaned_data['email']
            if commit:
                try:
                    self.user.save()
                    logger.debug(f"User updated in UserProfileForm: username={self.user.username}, email={self.user.email}")
                except Exception as e:
                    logger.error(f"Failed to save user in UserProfileForm: {e}")
                    raise
        if commit:
            try:
                profile.save()
                logger.debug(f"UserProfile saved in UserProfileForm: user={self.user.username}")
            except Exception as e:
                logger.error(f"Failed to save UserProfile in UserProfileForm: {e}")
                raise
        return profile