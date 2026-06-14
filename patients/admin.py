import logging

from django.conf import settings
from django.contrib import admin, messages

from .models import SMSMessageLog, Patient
from .sms import build_patient_name_token, send_done_sms

logger = logging.getLogger(__name__)


class SMSMessageLogInline(admin.TabularInline):
    model = SMSMessageLog
    extra = 0
    can_delete = False
    fields = ("created_at", "template", "token", "status", "response", "error")
    readonly_fields = fields
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "mobile", "created_at")
    search_fields = ("mobile", "first_name", "last_name")
    ordering = ("-created_at",)
    actions = ("send_done_sms_to_patients",)
    inlines = (SMSMessageLogInline,)

    @admin.action(description="ارسال پیامک انجام شد برای بیماران انتخاب‌شده")
    def send_done_sms_to_patients(self, request, queryset):
        sent_count = 0
        failed_count = 0
        template = getattr(settings, "KAVENEGAR_DONE_TEMPLATE", "")

        for patient in queryset:
            token = build_patient_name_token(patient)

            try:
                response = send_done_sms(patient.mobile, token)
            except Exception as exc:
                failed_count += 1
                SMSMessageLog.objects.create(
                    patient=patient,
                    mobile=patient.mobile,
                    template=template,
                    token=token,
                    status=SMSMessageLog.STATUS_FAILED,
                    error=str(exc),
                )
                logger.exception(
                    "Failed to send Kavenegar done SMS to patient %s.", patient.pk
                )
            else:
                sent_count += 1
                SMSMessageLog.objects.create(
                    patient=patient,
                    mobile=patient.mobile,
                    template=template,
                    token=token,
                    status=SMSMessageLog.STATUS_SUCCESS,
                    response=str(response),
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


@admin.register(SMSMessageLog)
class SMSMessageLogAdmin(admin.ModelAdmin):
    list_display = ("patient", "mobile", "template", "status", "created_at")
    list_filter = ("status", "template", "created_at")
    search_fields = (
        "patient__first_name",
        "patient__last_name",
        "mobile",
        "template",
        "token",
    )
    readonly_fields = (
        "patient",
        "mobile",
        "template",
        "token",
        "status",
        "response",
        "error",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
