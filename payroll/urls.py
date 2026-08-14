from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Gestion des Salariés
    path('employees/', views.employee_list, name='employee_list'),
    path('employee/add/', views.employee_add, name='employee_add'),
    path('employee/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('employee/<int:employee_id>/edit/', views.employee_edit, name='employee_edit'),
    path('employee/<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),

    # Bulletins de Paie & Archives
    path('payslips/', views.payslip_list, name='payslip_list'),
    path('payslips/archived/', views.archived_payslips, name='archived_payslips'),
    path('payslips/generate-monthly/', views.payslip_bulk_create, name='payslip_bulk_create'),
    path('employee/<int:employee_id>/payslip/new/', views.payslip_create, name='payslip_create'),
    path('payslip/<int:payslip_id>/', views.payslip_detail, name='payslip_detail'),
    path('payslip/<int:payslip_id>/pdf/', views.generate_payslip_pdf, name='generate_payslip_pdf'),
    path('payslip/<int:payslip_id>/toggle-hide/', views.toggle_hide_payslip, name='toggle_hide_payslip'),

    # Déclarations Sociale & Fiscale
    path('declarations/irsa/', views.irsa_declaration_view, name='irsa_declaration'),
    path('declarations/cnaps/', views.cnaps_declaration_view, name='cnaps_declaration'),
    path('declarations/sante/', views.health_declaration_view, name='health_declaration'),

    # Récapitulatif Mensuel & Exports
    path('summary/monthly/', views.monthly_summary_view, name='monthly_summary'),
    path('summary/monthly/excel/', views.export_monthly_summary_excel, name='export_monthly_summary_excel'),
    path('summary/monthly/pdf/', views.export_monthly_summary_pdf, name='export_monthly_summary_pdf'),
]