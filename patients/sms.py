from django.conf import settings

REGISTER_TEMPLATE = "register"
DONE_TEMPLATE = "done"


class KavenegarSMSConfigurationError(Exception):
    """Raised when Kavenegar SMS settings are not configured."""


def _build_kavenegar_api(api_key):
    from kavenegar import KavenegarAPI

    return KavenegarAPI(api_key)


def build_patient_sms_token(patient_or_mobile, name=None):
    """Build the Kavenegar token used for patient template SMS messages."""

    if hasattr(patient_or_mobile, "first_name") and hasattr(
        patient_or_mobile, "last_name"
    ):
        return f"{patient_or_mobile.first_name}_{patient_or_mobile.last_name}"

    return name or patient_or_mobile


def send_patient_template_sms(mobile, token, template):
    """Send a Kavenegar verify_lookup SMS with the given patient template."""

    api_key = getattr(settings, "KAVENEGAR_API_KEY", "")
    if not api_key:
        raise KavenegarSMSConfigurationError("KAVENEGAR_API_KEY is not configured.")

    api = _build_kavenegar_api(api_key)
    params = {"receptor": mobile, "template": template, "token": token}

    return api.verify_lookup(params)


def send_register_sms(mobile, name=None):
    """Send the Kavenegar register template SMS."""

    template = getattr(settings, "KAVENEGAR_REGISTER_TEMPLATE", REGISTER_TEMPLATE)
    token = build_patient_sms_token(mobile, name)
    return send_patient_template_sms(mobile, token, template)


def send_done_sms(mobile, name=None):
    """Send the Kavenegar done template SMS."""

    template = getattr(settings, "KAVENEGAR_DONE_TEMPLATE", DONE_TEMPLATE)
    token = build_patient_sms_token(mobile, name)
    return send_patient_template_sms(mobile, token, template)
