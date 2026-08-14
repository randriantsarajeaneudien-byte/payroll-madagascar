from django.urls import path
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from . import views

app_name = 'accounts'

urlpatterns = [
    # Redirection de /accounts/ vers la page d'inscription
    path('', lambda request: redirect('accounts:register'), name='index'),

    # Inscription, Connexion et Déconnexion
    path('register/', views.register_view, name='register'),
    path('login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # Configuration de la société
    path('company/new/', views.company_create_view, name='company_create'),

    # --- ROUTES SÉCURITÉ ET PAIEMENT ---
    path('subscription/pay/', views.payment_page, name='payment_page'),
    path('account/banned/', views.banned_page, name='banned_page'),
]