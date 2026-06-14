import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Patient
from .sms import build_patient_name_token, send_register_sms
from .sms_logs import create_sms_message_log

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Patient)
def send_register_sms_after_patient_created(sender, instance, created, **kwargs):
    """Send the Kavenegar register template after a new patient is committed."""

    if not created:
        return

    def _send_sms():
        template = ""
        token = build_patient_name_token(instance)

        try:
            template = settings.KAVENEGAR_REGISTER_TEMPLATE
            response = send_register_sms(instance.mobile, token)
        except Exception as exc:
            create_sms_message_log(instance, template, token, error=exc)
            logger.exception(
                "Failed to send Kavenegar register SMS to patient %s.", instance.pk
            )
        else:
            create_sms_message_log(instance, template, token, response=response)

    transaction.on_commit(_send_sms)
