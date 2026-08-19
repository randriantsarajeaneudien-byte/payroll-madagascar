from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Company
from ..models import Employee, LeaveRequest


@login_required
def leave_dashboard(request):
    company = get_object_or_404(Company, owner=request.user)
    employees = Employee.objects.filter(company=company)
    leave_requests = LeaveRequest.objects.filter(employee__company=company).order_by('-created_at')

    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        leave_type = request.POST.get('leave_type')
        reason = request.POST.get('reason')

        employee = get_object_or_404(Employee, id=employee_id, company=company)

        LeaveRequest.objects.create(
            employee=employee,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            reason=reason,
            status='pending'
        )
        messages.success(request, "Demande de congé ajoutée avec succès.")
        return redirect('payroll:leave_dashboard')

    return render(request, 'payroll/leaves.html', {
        'employees': employees,
        'leave_requests': leave_requests,
    })


@login_required
def update_leave_status(request, pk, status):
    company = get_object_or_404(Company, owner=request.user)
    leave_req = get_object_or_404(LeaveRequest, pk=pk, employee__company=company)

    if status in ['approved', 'rejected']:
        leave_req.status = status
        leave_req.save()
        messages.success(request, f"Le statut du congé a été mis à jour : {leave_req.get_status_display()}")

    return redirect('payroll:leave_dashboard')