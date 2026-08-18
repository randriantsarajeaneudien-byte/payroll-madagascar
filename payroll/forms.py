from django import forms
from .models import Employee, Payslip, PayrollSettings


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name', 'last_name', 'cin', 'job_title',
            'contract_type', 'hire_date', 'department',
            'category', 'cnaps_no', 'children_count', 'base_salary',
            'total_advance_balance',
            'leave_balance'  # Permet la saisie/modification du solde de congés restants
        ]
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'cin': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_type': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'cnaps_no': forms.TextInput(attrs={'class': 'form-control'}),
            'children_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'total_advance_balance': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'leave_balance': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.0'}),
        }


MONTH_CHOICES = [
    ('Janvier', 'Janvier'),
    ('Février', 'Février'),
    ('Mars', 'Mars'),
    ('Avril', 'Avril'),
    ('Mai', 'Mai'),
    ('Juin', 'Juin'),
    ('Juillet', 'Juillet'),
    ('Août', 'Août'),
    ('Septembre', 'Septembre'),
    ('Octobre', 'Octobre'),
    ('Novembre', 'Novembre'),
    ('Décembre', 'Décembre'),
]


class PayslipCreateForm(forms.ModelForm):
    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Mois"
    )

    class Meta:
        model = Payslip
        fields = [
            'month',
            'year',
            'working_days',
            'absence_days',
            'paid_leave_days',     # NOUVEAU : Jours de congé payé pris
            'daily_absence_rate',
            'overtime_hours',
            'overtime_amount',
            'bonuses',
            'advances'
        ]
        widgets = {
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'working_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'absence_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'paid_leave_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'daily_absence_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'overtime_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'bonuses': forms.NumberInput(attrs={'class': 'form-control'}),
            'advances': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Montant à déduire ce mois'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre les champs numériques facultatifs avec une valeur par défaut à 0
        optional_numeric_fields = [
            'absence_days', 'paid_leave_days', 'daily_absence_rate',
            'overtime_hours', 'overtime_amount', 'bonuses', 'advances'
        ]
        for field in optional_numeric_fields:
            if field in self.fields:
                self.fields[field].required = False
                self.fields[field].initial = 0


# ==============================================================================
# Formulaire pour les paramètres de paie de l'entreprise
# ==============================================================================
class PayrollSettingsForm(forms.ModelForm):
    class Meta:
        model = PayrollSettings
        fields = [
            'cnaps_employee_rate',
            'cnaps_employer_rate',
            'smids_employee_rate',  # AJOUTÉ
            'smids_employer_rate',
            'fmfp_employer_rate',
        ]
        widgets = {
            'cnaps_employee_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'cnaps_employer_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'smids_employee_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}), # AJOUTÉ
            'smids_employer_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'fmfp_employer_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }