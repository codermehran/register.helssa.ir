from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Patient
from .sms_tasks import enqueue_register_sms


@receiver(post_save, sender=Patient)
def send_register_sms_after_patient_created(sender, instance, created, **kwargs):
    """Send the Kavenegar register template after a new patient is committed."""

    if not created:
        return

    transaction.on_commit(lambda: enqueue_register_sms(instance.pk))
