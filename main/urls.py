from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('refresh-captcha/', views.refresh_captcha, name='refresh_captcha'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('kyc-verification/', views.kyc_verification, name='kyc_verification'),
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('investments/', views.investments, name='investments'),
    path('settings/', views.settings, name='settings'),
    path('withdraw/auth/', views.withdrawal_auth, name='withdrawal_auth'),
    path('about/', views.about, name='about'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('demo/', views.demo, name='demo'),
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='main/password_reset_form.html',
             email_template_name='main/password_reset_email.html',
             subject_template_name='main/password_reset_subject.txt',
             success_url=reverse_lazy('main:password_reset_done')
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='main/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='main/password_reset_confirm.html',
             success_url=reverse_lazy('main:password_reset_complete')
         ), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='main/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]