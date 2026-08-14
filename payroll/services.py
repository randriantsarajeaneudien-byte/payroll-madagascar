# payroll/services.py
from .models import Payslip


def calculate_payroll(employee, period):
    # Logique de calcul du salaire, taxes, cotisations...
    gross_salary = employee.base_salary
    deductions = gross_salary * 0.1  # exemple
    net_salary = gross_salary - deductions

    payslip = Payslip.objects.create(
        employee=employee,
        period=period,
        gross_salary=gross_salary,
        net_salary=net_salary
    )
    return payslip