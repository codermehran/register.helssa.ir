from django.conf import settings


class KavenegarSMSConfigurationError(Exception):
    """Raised when Kavenegar SMS settings are not configured."""


def _build_kavenegar_api(api_key):
    from kavenegar import KavenegarAPI

    return KavenegarAPI(api_key)


def build_patient_name_token(patient):
    """Build the Kavenegar token from a patient name."""

    return f"{patient.first_name}_{patient.last_name}"


def _get_required_sms_setting(setting_name):
    value = getattr(settings, setting_name, "")
    if not value:
        raise KavenegarSMSConfigurationError(f"{setting_name} is not configured.")

    return value


def _send_template_sms(mobile, name, template):
    api_key = _get_required_sms_setting("KAVENEGAR_API_KEY")

    api = _build_kavenegar_api(api_key)
    params = {"receptor": mobile, "template": template, "token": name}

    return api.verify_lookup(params)


def send_register_sms(mobile, name):
    """Send the Kavenegar register template SMS."""

    template = _get_required_sms_setting("KAVENEGAR_REGISTER_TEMPLATE")
    return _send_template_sms(mobile, name, template)


def send_done_sms(mobile, name):
    """Send the Kavenegar done template SMS."""

    template = _get_required_sms_setting("KAVENEGAR_DONE_TEMPLATE")
    return _send_template_sms(mobile, name, template)
