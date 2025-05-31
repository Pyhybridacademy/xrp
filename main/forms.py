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

logger = logging.getLogger(__name__)

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    full_name = forms.CharField(max_length=100, required=True)
    phone = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=50, required=False)
    currency = forms.ChoiceField(choices=(('USD', 'US Dollar ($)'), ('EUR', 'Euro (€)'), ('GBP', 'British Pound (£)')), required=False)
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
        return username

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
        
        # Clean and compare answers
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

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput, label="")
    captcha_answer = forms.CharField(max_length=10, required=True, label="Enter the result shown in the image")

    BLACKLISTED_CHARS = r'[<>{};#&%`~]'

    def __init__(self, *args, captcha_answer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.captcha_answer = captcha_answer
        if self.data:
            logger.debug(f"Login form POST data: {self.data}")

    def clean_username(self):
        username = self.cleaned_data['username']
        if len(username) > 30:
            raise ValidationError("Username cannot exceed 30 characters.")
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        if re.search(self.BLACKLISTED_CHARS, username):
            raise ValidationError("Username contains invalid characters.")
        return username

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
        
        # Clean and compare answers
        entered_clean = str(captcha_answer).strip().lower()
        correct_clean = str(correct_answer).strip().lower()
        
        if entered_clean != correct_clean:
            logger.warning(f"Invalid CAPTCHA answer: entered={entered_clean}, correct={correct_clean}")
            raise ValidationError("Incorrect CAPTCHA answer. Please try again.")
        
        return captcha_answer
