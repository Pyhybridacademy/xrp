from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('', views.admin_dashboard, name='dashboard'),
    path('password/change/', views.admin_password_change, name='password_change'),
    path('profile/', views.admin_profile, name='profile'),
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:user_id>/add-bonus/', views.user_add_bonus, name='user_add_bonus'),
    # KYC Management
    path('kyc/', views.kyc_list, name='kyc_list'),
    path('kyc/<int:kyc_id>/', views.kyc_detail, name='kyc_detail'),
    path('kyc/<int:kyc_id>/approve/', views.kyc_approve, name='kyc_approve'),
    path('kyc/<int:kyc_id>/reject/', views.kyc_reject, name='kyc_reject'),
    # Transaction Management
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    path('transactions/<int:transaction_id>/approve/', views.transaction_approve, name='transaction_approve'),
    path('transactions/<int:transaction_id>/reject/', views.transaction_reject, name='transaction_reject'),
    # Investment Management
    path('investments/', views.investment_list, name='investment_list'),
    path('investments/<int:investment_id>/', views.investment_detail, name='investment_detail'),
    path('investments/<int:investment_id>/complete/', views.investment_complete, name='investment_complete'),
    # Investment Plan Management
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/create/', views.plan_create, name='plan_create'),
    path('plans/<int:plan_id>/edit/', views.plan_edit, name='plan_edit'),
    path('plans/<int:plan_id>/delete/', views.plan_delete, name='plan_delete'),
    # Cryptocurrency Management
    path('cryptocurrencies/', views.crypto_list, name='crypto_list'),
    path('cryptocurrencies/create/', views.crypto_create, name='crypto_create'),
    path('cryptocurrencies/<int:crypto_id>/edit/', views.crypto_edit, name='crypto_edit'),
    path('cryptocurrencies/<int:crypto_id>/delete/', views.crypto_delete, name='crypto_delete'),
    # Site Settings
    path('settings/', views.site_settings, name='site_settings'),
    path('withdrawal-codes/', views.withdrawal_code_list, name='withdrawal_code_list'),
    path('withdrawal-codes/create/', views.withdrawal_code_create, name='withdrawal_code_create'),
    path('withdrawal-codes/<int:code_id>/edit/', views.withdrawal_code_edit, name='withdrawal_code_edit'),
    path('withdrawal-codes/<int:code_id>/delete/', views.withdrawal_code_delete, name='withdrawal_code_delete'),
]