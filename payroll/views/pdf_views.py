from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from ..models import Payslip
from ..utils.pdf_generator import generate_payslip_pdf_response

@login_required
def generate_payslip_pdf(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id)
    return generate_payslip_pdf_response(payslip, request.user)