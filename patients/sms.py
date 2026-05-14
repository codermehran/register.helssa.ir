from django.conf import settings


REGISTER_TEMPLATE = "register"


class KavenegarSMSConfigurationError(Exception):
    """Raised when Kavenegar SMS settings are not configured."""


def _build_kavenegar_api(api_key):
    from kavenegar import KavenegarAPI

    return KavenegarAPI(api_key)


def send_register_sms(mobile):
    """Send the Kavenegar register template with the mobile as token."""

    api_key = getattr(settings, "KAVENEGAR_API_KEY", "")
    if not api_key:
        raise KavenegarSMSConfigurationError("KAVENEGAR_API_KEY is not configured.")

    template = getattr(settings, "KAVENEGAR_REGISTER_TEMPLATE", REGISTER_TEMPLATE)
    api = _build_kavenegar_api(api_key)
    params = {"receptor": mobile, "template": template, "token": mobile}

    return api.verify_lookup(params)
