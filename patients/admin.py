import ast
import logging
from datetime import datetime, timezone as datetime_timezone

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Exists, OuterRef
from django.utils.html import format_html, format_html_join

from .datetime import format_tehran_jalali
from .models import SMSMessageLog, Patient
from .sms import build_patient_name_token, send_done_sms
from .sms_logs import create_sms_message_log

logger = logging.getLogger(__name__)


class PatientAdminForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = "__all__"
        widgets = {
            "national_code": forms.TextInput(
                attrs={
                    "class": "vTextField",
                    "data-copy-national-code": "true",
                    "dir": "ltr",
                    "inputmode": "numeric",
                    "maxlength": "10",
                }
            )
        }


SMS_RESPONSE_LABELS = {
    "messageid": "شناسه پیامک",
    "message": "متن پیام",
    "status": "کد وضعیت",
    "statustext": "وضعیت سرویس",
    "sender": "فرستنده",
    "receptor": "گیرنده",
    "date": "زمان سرویس",
    "cost": "هزینه",
}


def _format_sms_response_value(key, value):
    if key != "date":
        return value

    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return value

    return format_tehran_jalali(
        datetime.fromtimestamp(timestamp, tz=datetime_timezone.utc)
    )


def _parse_sms_response(response):
    if not response:
        return []

    try:
        parsed_response = ast.literal_eval(response)
    except (ValueError, SyntaxError):
        return response

    if isinstance(parsed_response, dict):
        return [parsed_response]

    if isinstance(parsed_response, list):
        return [item for item in parsed_response if isinstance(item, dict)]

    return response


def format_sms_response(response):
    parsed_response = _parse_sms_response(response)
    if not parsed_response:
        return "-"

    if isinstance(parsed_response, str):
        return format_html(
            '<div style="white-space: pre-wrap; direction: rtl; text-align: right;">{}</div>',
            parsed_response,
        )

    cards = []
    for item in parsed_response:
        rows = []
        for key, label in SMS_RESPONSE_LABELS.items():
            value = item.get(key)
            if value in (None, ""):
                continue
            value = _format_sms_response_value(key, value)
            rows.append(
                format_html(
                    '<div style="display: grid; grid-template-columns: minmax(96px, 128px) minmax(0, 1fr); gap: 10px; padding: 9px 0; border-bottom: 1px solid rgba(128,128,128,.18);">'
                    '<strong style="color: #8aa0b2; font-weight: 700;">{}</strong>'
                    '<span style="white-space: pre-wrap; overflow-wrap: anywhere; direction: rtl; text-align: right;">{}</span>'
                    "</div>",
                    label,
                    value,
                )
            )

        cards.append(
            format_html(
                '<div style="box-sizing: border-box; width: min(100%, 720px); padding: 10px 14px; border: 1px solid rgba(128,128,128,.24); border-radius: 8px; line-height: 1.9; direction: rtl; text-align: right;">{}</div>',
                format_html_join("", "{}", ((row,) for row in rows)),
            )
        )

    return format_html_join("", "{}", ((card,) for card in cards))


class SMSMessageLogInline(admin.TabularInline):
    model = SMSMessageLog
    extra = 0
    can_delete = False
    fields = (
        "created_at_jalali",
        "template",
        "token",
        "status",
        "formatted_response",
        "formatted_error",
    )
    readonly_fields = fields
    ordering = ("-created_at",)

    @admin.display(description="زمان ارسال", ordering="created_at")
    def created_at_jalali(self, obj):
        return format_tehran_jalali(obj.created_at)

    @admin.display(description="پاسخ سرویس")
    def formatted_response(self, obj):
        return format_sms_response(obj.response)

    @admin.display(description="خطا")
    def formatted_error(self, obj):
        if not obj.error:
            return "-"
        return format_html(
            '<div style="white-space: pre-wrap; overflow-wrap: anywhere; direction: rtl; text-align: right;">{}</div>',
            obj.error,
        )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    form = PatientAdminForm
    list_display = (
        "first_name",
        "last_name",
        "national_code",
        "sms_sent_indicator",
        "created_at_jalali",
    )
    search_fields = ("mobile", "national_code", "first_name", "last_name")
    ordering = ("-created_at",)
    actions = ("send_done_sms_to_patients",)
    inlines = (SMSMessageLogInline,)

    class Media:
        css = {"all": ("patients/admin/copy_national_code.css",)}
        js = ("patients/admin/copy_national_code.js",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        successful_done_sms_logs = SMSMessageLog.objects.filter(
            patient=OuterRef("pk"),
            status=SMSMessageLog.STATUS_SUCCESS,
            template=getattr(settings, "KAVENEGAR_DONE_TEMPLATE", ""),
        )
        return queryset.annotate(
            has_successful_done_sms=Exists(successful_done_sms_logs)
        )

    @admin.display(
        description="پیامک انجام شد",
        boolean=True,
        ordering="has_successful_done_sms",
    )
    def sms_sent_indicator(self, obj):
        return getattr(obj, "has_successful_done_sms", False)

    @admin.display(description="زمان ثبت", ordering="created_at")
    def created_at_jalali(self, obj):
        return format_tehran_jalali(obj.created_at)

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
    list_display = ("patient", "mobile", "template", "status", "created_at_jalali")
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
        "formatted_response",
        "formatted_error",
        "created_at_jalali",
    )
    fields = readonly_fields
    ordering = ("-created_at",)

    @admin.display(description="زمان ارسال", ordering="created_at")
    def created_at_jalali(self, obj):
        return format_tehran_jalali(obj.created_at)

    @admin.display(description="پاسخ سرویس")
    def formatted_response(self, obj):
        return format_sms_response(obj.response)

    @admin.display(description="خطا")
    def formatted_error(self, obj):
        if not obj.error:
            return "-"
        return format_html(
            '<div style="white-space: pre-wrap; overflow-wrap: anywhere; direction: rtl; text-align: right;">{}</div>',
            obj.error,
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
