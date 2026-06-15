import logging

from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Exists, OuterRef

from .models import SMSMessageLog, Patient
from .sms import build_patient_name_token, send_done_sms
from .sms_logs import create_sms_message_log

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

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "national_code",
        "sms_sent_indicator",
        "created_at",
    )
    search_fields = ("mobile", "national_code", "first_name", "last_name")
    ordering = ("-created_at",)
    actions = ("send_done_sms_to_patients",)
    inlines = (SMSMessageLogInline,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        successful_sms_logs = SMSMessageLog.objects.filter(
            patient=OuterRef("pk"), status=SMSMessageLog.STATUS_SUCCESS
        )
        return queryset.annotate(has_successful_sms=Exists(successful_sms_logs))

    @admin.display(description="پیامک", boolean=True, ordering="has_successful_sms")
    def sms_sent_indicator(self, obj):
        return getattr(obj, "has_successful_sms", False)

    @admin.action(description="ارسال پیامک انجام شد برای بیماران انتخاب‌شده")
    def send_done_sms_to_patients(self, request, queryset):
        api_key = getattr(settings, "KAVENEGAR_API_KEY", "")
        template = getattr(settings, "KAVENEGAR_DONE_TEMPLATE", "")
        if not api_key or not template:
            self.message_user(
                request,
                "تنظیمات سامانه پیامک (KAVENEGAR_API_KEY یا "
                "KAVENEGAR_DONE_TEMPLATE) پیکربندی نشده است.",
                messages.ERROR,
            )
            return

        sent_count = 0
        failed_count = 0

        for patient in queryset:
            token = build_patient_name_token(patient)

            try:
                response = send_done_sms(patient.mobile, token)
            except Exception as exc:
                failed_count += 1
                create_sms_message_log(patient, template, token, error=exc)
                logger.exception(
                    "Failed to send Kavenegar done SMS to patient %s.", patient.pk
                )
            else:
                sent_count += 1
                create_sms_message_log(patient, template, token, response=response)

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

    def has_delete_permission(self, request, obj=None):
        return False
