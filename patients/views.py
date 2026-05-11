from django.conf import settings
from django.contrib import messages
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import redirect, render
from django.templatetags.static import static

from .forms import DUPLICATE_MOBILE_ERROR, PatientRegistrationForm

SAVE_ERROR = "در ذخیره‌سازی اطلاعات مشکلی رخ داد. لطفاً دوباره تلاش کنید."
SHARE_TITLE = "ثبت‌نام بیماران | سامانه امن پذیرش"
SHARE_DESCRIPTION = (
    "ثبت‌نام اولیه بیماران در سامانه امن پذیرش؛ اطلاعات شما فقط برای ثبت‌نام "
    "و تماس بعدی استفاده می‌شود."
)
SHARE_IMAGE_PATH = "patients/images/share-logo.png"
SITE_LOGO_PATH = "patients/images/site-logo.png"


def _static_source_exists(path):
    """Return whether a project-level static asset has been provided."""

    return (settings.BASE_DIR / "patients" / "static" / path).exists()


def _absolute_static_url(request, path):
    """Build an absolute URL for a static asset that may use a relative STATIC_URL."""

    static_url = static(path)
    if not static_url.startswith("/"):
        static_url = f"/{static_url}"

    return request.build_absolute_uri(static_url)


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

    share_meta = {
        "title": SHARE_TITLE,
        "description": SHARE_DESCRIPTION,
        "url": request.build_absolute_uri(request.path),
        "image": _absolute_static_url(request, SHARE_IMAGE_PATH),
        "image_width": "1200",
        "image_height": "630",
    }
    site_logo = None
    if _static_source_exists(SITE_LOGO_PATH):
        site_logo = {
            "url": _absolute_static_url(request, SITE_LOGO_PATH),
            "alt": "لوگوی سامانه ثبت‌نام بیماران",
        }

    return render(
        request,
        "patients/register.html",
        {"form": form, "share_meta": share_meta, "site_logo": site_logo},
    )


register = register_patient
