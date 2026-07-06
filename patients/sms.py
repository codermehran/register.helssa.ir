import json
import re

from django.conf import settings
import requests


class KavenegarSMSConfigurationError(Exception):
    """Raised when Kavenegar SMS settings are not configured."""


class KavenegarSMSDeliveryError(Exception):
    """Raised when Kavenegar does not accept or answer an SMS request."""


def normalize_kavenegar_token_part(value):
    """Replace every whitespace run with underscores for Kavenegar tokens."""

    return re.sub(r"\s+", "_", value.strip())


def build_patient_name_token(patient):
    """Build the Kavenegar token from a patient name."""

    first_name = normalize_kavenegar_token_part(patient.first_name)
    last_name = normalize_kavenegar_token_part(patient.last_name)
    return f"{first_name}_{last_name}"


def _get_required_sms_setting(setting_name):
    value = getattr(settings, setting_name, "")
    if not value:
        raise KavenegarSMSConfigurationError(f"{setting_name} is not configured.")

    return value


def _get_sms_timeout_seconds():
    try:
        return float(getattr(settings, "KAVENEGAR_REQUEST_TIMEOUT_SECONDS", 10))
    except (TypeError, ValueError):
        return 10.0


def _send_template_sms(mobile, name, template):
    api_key = _get_required_sms_setting("KAVENEGAR_API_KEY")
    params = {"receptor": mobile, "template": template, "token": name}
    url = f"https://api.kavenegar.com/v1/{api_key}/verify/lookup.json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "charset": "utf-8",
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=params,
            timeout=_get_sms_timeout_seconds(),
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException:
        raise KavenegarSMSDeliveryError("Kavenegar request failed.") from None
    except (TypeError, ValueError, json.JSONDecodeError):
        raise KavenegarSMSDeliveryError(
            "Kavenegar returned an invalid response."
        ) from None

    return_info = payload.get("return", {})
    if return_info.get("status") != 200:
        raise KavenegarSMSDeliveryError("Kavenegar rejected the SMS request.")

    return payload.get("entries", payload)


def send_register_sms(mobile, name):
    """Send the Kavenegar register template SMS."""

    template = _get_required_sms_setting("KAVENEGAR_REGISTER_TEMPLATE")
    return _send_template_sms(mobile, name, template)


def send_done_sms(mobile, name):
    """Send the Kavenegar done template SMS."""

    template = _get_required_sms_setting("KAVENEGAR_DONE_TEMPLATE")
    return _send_template_sms(mobile, name, template)
