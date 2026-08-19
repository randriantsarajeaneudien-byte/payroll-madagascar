from django.urls import path
from .views import (
    dashboard_views,
    employee_views,
    payslip_views,
    declaration_views,
    summary_views,
    pdf_views,
    settings_views,
    attendance_views,
    leave_views,  # Importation des vues de congés
)

app_name = 'payroll'

urlpatterns = [
    # Dashboard (Route racine /payroll/ ET /payroll/dashboard/)
    path('', dashboard_views.dashboard, name='dashboard'),
    path('dashboard/', dashboard_views.dashboard),

    # Gestion des Salariés
    path('employees/', employee_views.employee_list, name='employee_list'),
    path('employee/add/', employee_views.employee_add, name='employee_add'),
    path('employee/<int:employee_id>/', employee_views.employee_detail, name='employee_detail'),
    path('employee/<int:employee_id>/edit/', employee_views.employee_edit, name='employee_edit'),
    path('employee/<int:employee_id>/delete/', employee_views.employee_delete, name='employee_delete'),

    # API AJAX pour le calcul dynamique des absences dans le formulaire de paie
    path('api/calculate-attendance/', payslip_views.api_calculate_attendance, name='api_calculate_attendance'),

    # Bulletins de Paie & Archives
    path('payslips/', payslip_views.payslip_list, name='payslip_list'),
    path('payslips/archived/', payslip_views.archived_payslips, name='archived_payslips'),
    path('payslips/generate-monthly/', payslip_views.payslip_bulk_create, name='payslip_bulk_create'),
    path('employee/<int:employee_id>/payslip/new/', payslip_views.payslip_create, name='payslip_create'),
    path('payslip/<int:payslip_id>/', payslip_views.payslip_detail, name='payslip_detail'),

    # Route de recalcul ajoutée ici :
    path('payslip/<int:payslip_id>/recalculate/', payslip_views.payslip_recalculate, name='payslip_recalculate'),

    path('payslip/<int:payslip_id>/pdf/', pdf_views.generate_payslip_pdf, name='generate_payslip_pdf'),
    path('payslip/<int:payslip_id>/toggle-hide/', payslip_views.toggle_hide_payslip, name='toggle_hide_payslip'),

    # Suivi des Présences
    path('attendance/', attendance_views.attendance_dashboard, name='attendance_dashboard'),
    # Nouvelle route pour exporter la feuille de présence en PDF
    path('attendance/export-pdf/', attendance_views.export_attendance_pdf, name='export_attendance_pdf'),

    # Gestion des Congés
    path('leaves/', leave_views.leave_dashboard, name='leave_dashboard'),
    path('leaves/<int:pk>/update/<str:status>/', leave_views.update_leave_status, name='update_leave_status'),

    # Déclarations Sociales & Fiscales
    path('declarations/irsa/', declaration_views.irsa_declaration_view, name='irsa_declaration'),
    path('declarations/cnaps/', declaration_views.cnaps_declaration_view, name='cnaps_declaration'),
    path('declarations/sante/', declaration_views.health_declaration_view, name='health_declaration'),

    # Récapitulatif Mensuel & Exports
    path('summary/monthly/', summary_views.monthly_summary_view, name='monthly_summary'),
    path('summary/monthly/excel/', summary_views.export_monthly_summary_excel, name='export_monthly_summary_excel'),
    path('summary/monthly/pdf/', summary_views.export_monthly_summary_pdf, name='export_monthly_summary_pdf'),

    # Paramètres de Paie de l'entreprise
    path('settings/', settings_views.payroll_settings_view, name='payroll_settings'),
]