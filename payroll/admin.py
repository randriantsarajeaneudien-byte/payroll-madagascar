from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Employee, Payslip
from .utils.calculations import calculate_madagascar_payroll


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_filter = ('company', 'contract_type')
    search_fields = ('last_name', 'first_name', 'cin')

    def get_list_display(self, request):
        if request.user.is_superuser:
            return ('last_name', 'first_name', 'company', 'job_title', 'base_salary', 'leave_balance')
        return ('last_name', 'first_name', 'company', 'job_title', 'leave_balance')


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_filter = ('month', 'year', 'employee__company')
    search_fields = ('employee__first_name', 'employee__last_name')

    def get_list_display(self, request):
        # Affiche les salaires uniquement au Superadmin, sinon masque les chiffres
        if request.user.is_superuser:
            return ('employee', 'month', 'year', 'gross_salary_display', 'net_payable_display', 'download_pdf_link')
        return ('employee', 'month', 'year', 'masked_salary', 'download_pdf_link')

    def gross_salary_display(self, obj):
        return f"{obj.gross_salary:,.2f} Ar"
    gross_salary_display.short_description = "SALAIRE BRUT"

    def net_payable_display(self, obj):
        return f"{obj.net_payable:,.2f} Ar"
    net_payable_display.short_description = "NET À PAYER"

    def masked_salary(self, obj):
        return "•••••••• Ar"
    masked_salary.short_description = "MONTANTS"

    # Calcul automatique lors de la sauvegarde dans l'admin
    def save_model(self, request, obj, form, change):
        calc = calculate_madagascar_payroll(
            base_salary=obj.employee.base_salary,
            overtime=obj.overtime_amount,
            bonus=obj.bonuses,
            advance=obj.advances,
            children=obj.employee.children_count
        )
        obj.gross_salary = calc['gross_salary']
        obj.cnaps_employee = calc['cnaps_employee']
        obj.smids_employee = calc['smids_employee']
        obj.taxable_base = calc['taxable_base']
        obj.irsa = calc['irsa']
        obj.net_payable = calc['net_payable']
        obj.cnaps_employer = calc['cnaps_employer']
        obj.smids_employer = calc['smids_employer']
        obj.fmfp_employer = calc['fmfp_employer']

        super().save_model(request, obj, form, change)

    def download_pdf_link(self, obj):
        if obj.id:
            url = reverse('payroll:generate_payslip_pdf', args=[obj.id])
            return format_html(
                '<a class="button" style="background-color: #2b6cb0; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none;" href="{}" target="_blank">Télécharger PDF</a>',
                url
            )
        return "-"
    download_pdf_link.short_description = "ACTION PDF"