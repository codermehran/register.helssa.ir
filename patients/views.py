from django.contrib import messages
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import redirect, render

from .forms import DUPLICATE_MOBILE_ERROR, PatientRegistrationForm

SAVE_ERROR = "در ذخیره‌سازی اطلاعات مشکلی رخ داد. لطفاً دوباره تلاش کنید."


def register_patient(request):
    """Display and process the patient registration form."""

    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError:
                form.add_error("mobile", DUPLICATE_MOBILE_ERROR)
            except DatabaseError:
                form.add_error(None, SAVE_ERROR)
            else:
                messages.success(request, "ثبت‌نام شما با موفقیت انجام شد.")
                return redirect("patients:register")
    else:
        form = PatientRegistrationForm()

    return render(request, "patients/register.html", {"form": form})


register = register_patient
