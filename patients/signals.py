import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Patient
from .sms import build_patient_sms_token, send_register_sms

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Patient)
def send_register_sms_after_patient_created(sender, instance, created, **kwargs):
    """Send the Kavenegar register template after a new patient is committed."""

    if not created:
        return

    def _send_sms():
        try:
            send_register_sms(instance.mobile, build_patient_sms_token(instance))
        except Exception:
            logger.exception(
                "Failed to send Kavenegar register SMS to patient %s.", instance.pk
            )

    transaction.on_commit(_send_sms)
