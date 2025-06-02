# main/authentication.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Look for a user with the provided username or email (case-insensitive)
            user = UserModel.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            # Run the default password hasher to reduce timing difference
            UserModel().set_password(password)
        except UserModel.MultipleObjectsReturned:
            # If multiple users are found (unlikely with unique constraints), return None
            return None
        return None