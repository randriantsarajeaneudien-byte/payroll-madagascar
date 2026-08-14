from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def smart_home_redirect(request):
    # Si l'utilisateur est connecté, on l'envoie vers le dashboard
    if request.user.is_authenticated:
        return redirect('payroll:dashboard')
    # S'il n'est pas connecté, on l'envoie vers la page de connexion
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    # Inclusion des URLs des applications
    path('accounts/', include('accounts.urls')),
    path('payroll/', include('payroll.urls')),
    # Redirection dynamique de la racine (http://127.0.0.1:8000/)
    path('', smart_home_redirect, name='home'),
]