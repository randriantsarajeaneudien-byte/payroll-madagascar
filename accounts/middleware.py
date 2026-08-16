from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch


class SubscriptionAndSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # On ne contrôle que les utilisateurs connectés qui ne sont pas superutilisateurs
        if request.user.is_authenticated and not request.user.is_superuser:

            # Liste complète des noms d'URL autorisées sans restriction
            allowed_names = [
                'accounts:payment_page',
                'accounts:banned_page',
                'accounts:logout',
                'accounts:company_create',  # Pour permettre la création de la 1ère entreprise
                'accounts:login',
                'accounts:register',
            ]

            allowed_paths = []
            for url_name in allowed_names:
                try:
                    allowed_paths.append(reverse(url_name))
                except NoReverseMatch:
                    pass

            # Si l'URL demandée n'est ni dans l'admin, ni dans la liste autorisée
            if not request.path.startswith('/admin/') and request.path not in allowed_paths:
                company = request.user.companies.first()

                # Case 1 : L'utilisateur n'a pas encore créé d'entreprise
                if not company:
                    return redirect('accounts:company_create')

                # Case 2 : L'entreprise est bannie
                if company.is_banned:
                    return redirect('accounts:banned_page')

                # Case 3 : Limite d'essais atteinte et aucun abonnement valide
                if not company.can_generate_payslip():
                    return redirect('accounts:payment_page')

        return self.get_response(request)