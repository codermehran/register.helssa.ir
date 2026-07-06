from django.conf import settings

from .models import SMSMessageLog


def create_sms_message_log(patient, template, token, response=None, error=None):
    """Persist one SMS delivery attempt for admin auditing."""

    is_success = error is None
    sms_log = SMSMessageLog.objects.create(
        patient=patient,
        mobile=patient.mobile,
        template=template,
        token=token,
        status=(
            SMSMessageLog.STATUS_SUCCESS if is_success else SMSMessageLog.STATUS_FAILED
        ),
        response="" if response is None else str(response),
        error="" if error is None else str(error),
    )

    done_template = getattr(settings, "KAVENEGAR_DONE_TEMPLATE", "")
    if patient and is_success and done_template and template == done_template:
        type(patient).objects.filter(pk=patient.pk, done_sms_sent=False).update(
            done_sms_sent=True
        )

    return sms_log
