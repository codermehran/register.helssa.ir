import logging

from django.contrib import admin, messages

from .models import Patient
from .sms import build_patient_name_token, send_done_sms

logger = logging.getLogger(__name__)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "mobile", "created_at")
    search_fields = ("mobile", "first_name", "last_name")
    ordering = ("-created_at",)
    actions = ("send_done_sms_to_patients",)

    @admin.action(description="ارسال پیامک انجام شد برای بیماران انتخاب‌شده")
    def send_done_sms_to_patients(self, request, queryset):
        sent_count = 0
        failed_count = 0

        for patient in queryset:
            try:
                send_done_sms(patient.mobile, build_patient_name_token(patient))
                sent_count += 1
            except Exception:
                failed_count += 1
                logger.exception(
                    "Failed to send Kavenegar done SMS to patient %s.", patient.pk
                )

        if sent_count:
            self.message_user(
                request,
                f"پیامک انجام شد برای {sent_count} بیمار ارسال شد.",
                messages.SUCCESS,
            )

        if failed_count:
            self.message_user(
                request,
                f"ارسال پیامک انجام شد برای {failed_count} بیمار ناموفق بود.",
                messages.ERROR,
            )
