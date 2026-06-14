import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SMSMessageLog, Patient
from .sms import build_patient_name_token, send_register_sms

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Patient)
def send_register_sms_after_patient_created(sender, instance, created, **kwargs):
    """Send the Kavenegar register template after a new patient is committed."""

    if not created:
        return

    def _send_sms():
        template = getattr(settings, "KAVENEGAR_REGISTER_TEMPLATE", "")
        token = build_patient_name_token(instance)

        try:
            response = send_register_sms(instance.mobile, token)
        except Exception as exc:
            SMSMessageLog.objects.create(
                patient=instance,
                mobile=instance.mobile,
                template=template,
                token=token,
                status=SMSMessageLog.STATUS_FAILED,
                error=str(exc),
            )
            logger.exception(
                "Failed to send Kavenegar register SMS to patient %s.", instance.pk
            )
        else:
            SMSMessageLog.objects.create(
                patient=instance,
                mobile=instance.mobile,
                template=template,
                token=token,
                status=SMSMessageLog.STATUS_SUCCESS,
                response=str(response),
            )

    transaction.on_commit(_send_sms)
