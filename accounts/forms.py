from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from disposable_email_domains import blocklist
from .models import Company


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        label="Mot de passe"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        label="Confirmer le mot de passe"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Nom d'utilisateur"}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'exemple@email.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()

        if not email:
            raise ValidationError("L'adresse e-mail est obligatoire.")

        # 1. Empêcher la réutilisation d'un même e-mail
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Un compte existe déjà avec cette adresse e-mail.")

        # 2. Bloquer les e-mails temporaires via le package disposable-email-domains
        domain = email.split('@')[-1]
        if domain in blocklist:
            raise ValidationError(
                "Les adresses e-mail temporaires ou jetables ne sont pas autorisées. "
                "Veuillez utiliser une adresse e-mail valide."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Les mots de passe ne correspondent pas.")
        return cleaned_data

    def save(self, commit=True):
        # Sauvegarde de l'utilisateur avec le mot de passe correctement haché
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'nif', 'stat', 'cnaps_no']
        labels = {
            'name': "Nom de la société",
            'address': "Adresse complète",
            'nif': "NIF",
            'stat': "STAT",
            'cnaps_no': "N° CNaPS",
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: SARL Miara-Maniry'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lot II M 40 Antananarivo'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° Identification Fiscale'}),
            'stat': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° Statistique'}),
            'cnaps_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° d\'affiliation CNaPS'}),
        }