import logging
import threading

from django.conf import settings
from django.db import close_old_connections

from .models import Patient
from .sms import build_patient_name_token, send_done_sms, send_register_sms
from .sms_logs import create_sms_message_log

logger = logging.getLogger(__name__)


def _run_sms_task(function, *args):
    close_old_connections()
    try:
        function(*args)
    except Exception:
        logger.exception("Unhandled error in background SMS task.")
    finally:
        close_old_connections()


def _dispatch_sms_task(function, *args):
    if not getattr(settings, "SMS_SEND_ASYNC", True):
        return function(*args)

    thread = threading.Thread(
        target=_run_sms_task,
        args=(function, *args),
        daemon=True,
        name=f"sms-{function.__name__}",
    )
    thread.start()
    return thread


def _create_sms_message_log_safely(patient, template, token, response=None, error=None):
    try:
        create_sms_message_log(patient, template, token, response=response, error=error)
    except Exception:
        logger.exception("Failed to persist SMS message log for patient %s.", patient.pk)


def _send_register_sms_for_patient(patient_id):
    try:
        patient = Patient.objects.only("id", "first_name", "last_name", "mobile").get(
            pk=patient_id
        )
    except Patient.DoesNotExist:
        logger.warning(
            "Skipped register SMS because patient %s no longer exists.", patient_id
        )
        return

    template = ""
    token = build_patient_name_token(patient)

    try:
        template = settings.KAVENEGAR_REGISTER_TEMPLATE
        response = send_register_sms(patient.mobile, token)
    except Exception as exc:
        _create_sms_message_log_safely(patient, template, token, error=exc)
        logger.exception(
            "Failed to send Kavenegar register SMS to patient %s.", patient.pk
        )
    else:
        _create_sms_message_log_safely(patient, template, token, response=response)


def enqueue_register_sms(patient_id):
    return _dispatch_sms_task(_send_register_sms_for_patient, patient_id)


def _send_done_sms_for_patient(patient):
    template = ""
    token = build_patient_name_token(patient)

    try:
        template = settings.KAVENEGAR_DONE_TEMPLATE
        response = send_done_sms(patient.mobile, token)
    except Exception as exc:
        _create_sms_message_log_safely(patient, template, token, error=exc)
        logger.exception(
            "Failed to send Kavenegar done SMS to patient %s.", patient.pk
        )
    else:
        _create_sms_message_log_safely(patient, template, token, response=response)


def _send_done_sms_for_patients(patient_ids):
    patients = Patient.objects.filter(pk__in=patient_ids).only(
        "id", "first_name", "last_name", "mobile", "done_sms_sent"
    )
    for patient in patients:
        _send_done_sms_for_patient(patient)


def enqueue_done_sms_for_patients(patient_ids):
    return _dispatch_sms_task(_send_done_sms_for_patients, list(patient_ids))
