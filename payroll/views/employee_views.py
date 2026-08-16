from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.models import Company
from ..models import Employee
from ..forms import EmployeeForm


@login_required
def employee_list(request):
    company = get_object_or_404(Company, owner=request.user)
    employees = Employee.objects.filter(company=company)
    return render(request, 'payroll/employee_list.html', {'employees': employees})


@login_required
def employee_add(request):
    company = get_object_or_404(Company, owner=request.user)
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.company = company
            employee.save()
            messages.success(request, f"Le salarié {employee.first_name} {employee.last_name} a été ajouté.")
            return redirect('payroll:dashboard')
    else:
        form = EmployeeForm()
    return render(request, 'payroll/employee_form.html', {'form': form})


@login_required
def employee_detail(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id, company__owner=request.user)
    payslips = employee.payslips.filter(is_archived=False).order_by('-created_at')
    return render(request, 'payroll/employee_detail.html', {
        'employee': employee,
        'payslips': payslips
    })


@login_required
def employee_edit(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id, company__owner=request.user)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Les informations du salarié ont été mises à jour.")
            return redirect('payroll:dashboard')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'payroll/employee_form.html', {'form': form, 'employee': employee})


@login_required
def employee_delete(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id, company__owner=request.user)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, "Salarié supprimé avec succès.")
        return redirect('payroll:dashboard')
    return render(request, 'payroll/employee_confirm_delete.html', {'employee': employee})