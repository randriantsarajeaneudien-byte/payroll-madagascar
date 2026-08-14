from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch


class SubscriptionAndSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # On ne vérifie que si l'utilisateur est connecté et n'est pas un Superadmin
        if request.user.is_authenticated and not request.user.is_superuser:

            # Gestion sécurisée des URLs autorisées sans blocage (Correction ici : accounts:logout)
            allowed_paths = []
            for url_name in ['accounts:payment_page', 'accounts:banned_page', 'accounts:logout']:
                try:
                    allowed_paths.append(reverse(url_name))
                except NoReverseMatch:
                    pass

            # Si la requête n'est ni vers l'admin ni vers une URL autorisée
            if not request.path.startswith('/admin/') and request.path not in allowed_paths:
                company = request.user.companies.first()

                if company:
                    # 1. SI BANNI : Redirection vers la page Banni
                    if company.is_banned:
                        return redirect('accounts:banned_page')

                    # 2. SI 3 ESSAIS ÉPUISÉS : Redirection vers la page de Paiement
                    elif not company.can_generate_payslip():
                        return redirect('accounts:payment_page')

        response = self.get_response(request)
        return response