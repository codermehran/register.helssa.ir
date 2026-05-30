from django.conf import settings

REGISTER_TEMPLATE = "register"
DONE_TEMPLATE = "done"


class KavenegarSMSConfigurationError(Exception):
    """Raised when Kavenegar SMS settings are not configured."""


def _build_kavenegar_api(api_key):
    from kavenegar import KavenegarAPI

    return KavenegarAPI(api_key)


def build_patient_name_token(patient):
    """Build the Kavenegar token from a patient name."""

    return f"{patient.first_name}_{patient.last_name}"


def _send_template_sms(mobile, name, template):
    api_key = getattr(settings, "KAVENEGAR_API_KEY", "")
    if not api_key:
        raise KavenegarSMSConfigurationError("KAVENEGAR_API_KEY is not configured.")

    api = _build_kavenegar_api(api_key)
    params = {"receptor": mobile, "template": template, "token": name}

    return api.verify_lookup(params)


def send_register_sms(mobile, name):
    """Send the Kavenegar register template SMS."""

    template = getattr(settings, "KAVENEGAR_REGISTER_TEMPLATE", REGISTER_TEMPLATE)
    return _send_template_sms(mobile, name, template)


def send_done_sms(mobile, name):
    """Send the Kavenegar done template SMS."""

    template = getattr(settings, "KAVENEGAR_DONE_TEMPLATE", DONE_TEMPLATE)
    return _send_template_sms(mobile, name, template)
