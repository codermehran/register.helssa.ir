from pathlib import Path
from unittest.mock import patch

from django.db import DatabaseError, IntegrityError
from django.test import TestCase
from django.urls import reverse

from .forms import DUPLICATE_MOBILE_ERROR, PatientRegistrationForm
from .views import (
    SHARE_DESCRIPTION,
    SHARE_IMAGE_PATH,
    SHARE_TITLE,
    SITE_LOGO_PATH,
)
from .models import Patient


class PatientModelTests(TestCase):
    def test_mobile_field_is_unique(self):
        self.assertTrue(Patient._meta.get_field("mobile").unique)


class PatientRegistrationFormTests(TestCase):
    def test_valid_registration_form(self):
        form = PatientRegistrationForm(
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "09123456789",
            }
        )

        self.assertTrue(form.is_valid())

    def test_mobile_must_be_exactly_eleven_digits(self):
        form = PatientRegistrationForm(
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "0912345678",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["mobile"],
            ["شماره را ۱۱ رقمی وارد کنید."],
        )

    def test_mobile_must_contain_only_digits(self):
        form = PatientRegistrationForm(
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "0912345678a",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["mobile"],
            ["فقط عدد وارد کنید."],
        )

    def test_mobile_must_start_with_09(self):
        form = PatientRegistrationForm(
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "08123456789",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["mobile"],
            ["شماره موبایل با 09 شروع شود."],
        )

    def test_mobile_must_be_unique(self):
        Patient.objects.create(
            first_name="Existing",
            last_name="Patient",
            mobile="09123456789",
        )
        form = PatientRegistrationForm(
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "09123456789",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["mobile"],
            [DUPLICATE_MOBILE_ERROR],
        )

    def test_required_field_messages_are_persian(self):
        form = PatientRegistrationForm(data={})

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["first_name"], ["نام را وارد کنید."])
        self.assertEqual(
            form.errors["last_name"], ["نام خانوادگی را وارد کنید."]
        )
        self.assertEqual(
            form.errors["mobile"], ["شماره موبایل را وارد کنید."]
        )


class RegisterPatientViewTests(TestCase):
    def test_get_register_patient_displays_empty_form(self):
        response = self.client.get(reverse("patients:register"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "patients/register.html")
        self.assertIsInstance(response.context["form"], PatientRegistrationForm)
        self.assertFalse(response.context["form"].is_bound)

    def test_register_template_uses_persian_labels_and_submit_text(self):
        response = self.client.get(reverse("patients:register"))

        self.assertContains(response, "ثبت‌نام بیماران")
        self.assertContains(response, "نام")
        self.assertContains(response, "نام خانوادگی")
        self.assertContains(response, "شماره موبایل")
        self.assertContains(response, ">ثبت‌نام</button>")

    def test_register_template_includes_share_preview_metadata(self):
        response = self.client.get(reverse("patients:register"))

        share_image_url = f"http://testserver/static/{SHARE_IMAGE_PATH}"
        self.assertContains(response, f"<title>{SHARE_TITLE}</title>")
        self.assertContains(
            response, f'<meta name="description" content="{SHARE_DESCRIPTION}">'
        )
        self.assertContains(
            response, f'<meta property="og:title" content="{SHARE_TITLE}">'
        )
        self.assertContains(
            response,
            f'<meta property="og:description" content="{SHARE_DESCRIPTION}">',
        )
        self.assertContains(
            response, '<meta property="og:url" content="http://testserver/">'
        )
        self.assertContains(
            response, f'<meta property="og:image" content="{share_image_url}">'
        )
        self.assertContains(
            response, '<meta property="og:image:type" content="image/png">'
        )
        self.assertContains(
            response, '<meta name="twitter:card" content="summary_large_image">'
        )
        self.assertContains(
            response, f'<meta name="twitter:image" content="{share_image_url}">'
        )

    def test_logo_instructions_document_required_image_files(self):
        instructions = Path("logo.md").read_text()

        self.assertIn(SHARE_IMAGE_PATH, instructions)
        self.assertIn(SITE_LOGO_PATH, instructions)
        self.assertIn("1200×630", instructions)
        self.assertIn("512×512", instructions)

    def test_missing_site_logo_does_not_render_broken_image(self):
        response = self.client.get(reverse("patients:register"))

        self.assertNotContains(response, 'class="hero__logo"')
        self.assertNotContains(response, '<link rel="icon" type="image/png"')

    def test_site_logo_renders_after_file_is_provided(self):
        logo_path = Path("patients/static") / SITE_LOGO_PATH
        logo_path.parent.mkdir(parents=True, exist_ok=True)
        logo_path.write_bytes(b"\x89PNG\r\n\x1a\n")
        try:
            response = self.client.get(reverse("patients:register"))
        finally:
            logo_path.unlink(missing_ok=True)

        site_logo_url = f"http://testserver/static/{SITE_LOGO_PATH}"
        self.assertContains(response, 'class="hero__logo"')
        self.assertContains(response, f'src="{site_logo_url}"')
        self.assertContains(response, f'href="{site_logo_url}"')

    def test_register_form_disables_submit_button_after_submit_with_javascript(self):
        response = self.client.get(reverse("patients:register"))

        self.assertContains(response, 'data-registration-form')
        self.assertContains(response, 'data-submit-button')
        self.assertContains(response, 'data-submitting-text="در حال ثبت..."')
        self.assertContains(response, 'submitButton.disabled = true')

    def test_register_button_has_disabled_styles(self):
        css = Path("patients/static/patients/css/style.css").read_text()

        self.assertIn(".form-card button:disabled", css)
        self.assertIn("cursor: not-allowed", css)
        self.assertIn("--color-button-disabled", css)

    def test_register_template_uses_decorative_inline_svg_icons(self):
        response = self.client.get(reverse("patients:register"))

        self.assertContains(response, 'class="icon form-field__icon"', count=3)
        self.assertContains(response, 'focusable="false"')
        self.assertContains(response, 'aria-hidden="true"')

    def test_register_styles_use_short_motion_and_reduced_motion_override(self):
        css = Path("patients/static/patients/css/style.css").read_text()

        self.assertIn("@keyframes form-card-enter", css)
        self.assertIn("animation: form-card-enter 320ms ease-out both", css)
        self.assertIn("transition: background 0.2s ease", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("transition-duration: 1ms !important", css)
        self.assertIn("animation: none", css)

    def test_register_template_uses_rtl_persian_html_attributes(self):
        response = self.client.get(reverse("patients:register"))

        self.assertContains(response, '<html lang="fa" dir="rtl">')

    def test_register_form_uses_persian_placeholders_and_ltr_mobile(self):
        response = self.client.get(reverse("patients:register"))

        self.assertContains(response, 'autocomplete="given-name"')
        self.assertContains(response, 'placeholder="مثلاً علی"')
        self.assertContains(response, 'autocomplete="family-name"')
        self.assertContains(response, 'placeholder="مثلاً رضایی"')
        self.assertContains(response, 'autocomplete="tel"')
        self.assertContains(response, 'aria-describedby="mobile-help"')
        self.assertContains(response, 'dir="ltr"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'maxlength="11"')
        self.assertContains(response, 'placeholder="09123456789"')
        self.assertContains(
            response, "شماره موبایل باید ۱۱ رقمی و با 09 شروع شود."
        )

    def test_register_template_styles_messages_as_alert_cards(self):
        response = self.client.get(reverse("patients:register"))

        self.assertContains(response, 'class="message-stack"', count=0)

        response = self.client.post(
            reverse("patients:register"),
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "09123456789",
            },
            follow=True,
        )

        self.assertContains(response, 'class="message-stack"')
        self.assertContains(response, 'message-card message-card--success')
        self.assertContains(response, 'class="message-card__icon"')
        self.assertContains(response, 'class="icon icon--status"')
        self.assertContains(response, 'aria-hidden="true"')
        self.assertNotContains(response, "✓")

    def test_field_errors_render_below_each_field(self):
        response = self.client.post(
            reverse("patients:register"),
            data={"first_name": "", "last_name": "", "mobile": "08123456789"},
        )

        self.assertContains(response, 'aria-label="خطاهای نام"')
        self.assertContains(response, "نام را وارد کنید.")
        self.assertContains(response, 'aria-label="خطاهای نام خانوادگی"')
        self.assertContains(response, "نام خانوادگی را وارد کنید.")
        self.assertContains(response, 'aria-label="خطاهای شماره موبایل"')
        self.assertContains(response, "شماره موبایل با 09 شروع شود.")

    def test_invalid_post_preserves_submitted_values(self):
        response = self.client.post(
            reverse("patients:register"),
            data={
                "first_name": "علی",
                "last_name": "احمدی",
                "mobile": "08123456789",
            },
        )

        self.assertContains(response, 'value="علی"')
        self.assertContains(response, 'value="احمدی"')
        self.assertContains(response, 'value="08123456789"')

    def test_post_valid_form_saves_patient_redirects_and_adds_success_message(self):
        response = self.client.post(
            reverse("patients:register"),
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "09123456789",
            },
        )

        self.assertRedirects(response, reverse("patients:register"))
        self.assertTrue(
            Patient.objects.filter(
                first_name="Ali",
                last_name="Ahmadi",
                mobile="09123456789",
            ).exists()
        )

        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "ثبت‌نام شما با موفقیت انجام شد.")

    def test_post_invalid_form_renders_errors_without_saving_patient(self):
        response = self.client.post(
            reverse("patients:register"),
            data={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "mobile": "08123456789",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Patient.objects.exists())
        self.assertContains(response, "شماره موبایل با 09 شروع شود.")
        self.assertTrue(response.context["form"].is_bound)

    def test_post_handles_duplicate_mobile_integrity_error(self):
        with patch.object(
            PatientRegistrationForm,
            "save",
            side_effect=IntegrityError(
                "UNIQUE constraint failed: patients_patient.mobile"
            ),
        ):
            response = self.client.post(
                reverse("patients:register"),
                data={
                    "first_name": "Ali",
                    "last_name": "Ahmadi",
                    "mobile": "09123456789",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Patient.objects.exists())
        self.assertContains(response, DUPLICATE_MOBILE_ERROR)
        self.assertEqual(
            response.context["form"].errors["mobile"], [DUPLICATE_MOBILE_ERROR]
        )

    def test_post_handles_generic_database_save_error(self):
        with patch.object(
            PatientRegistrationForm,
            "save",
            side_effect=DatabaseError("database unavailable"),
        ):
            response = self.client.post(
                reverse("patients:register"),
                data={
                    "first_name": "Ali",
                    "last_name": "Ahmadi",
                    "mobile": "09123456789",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Patient.objects.exists())
        self.assertContains(
            response, "در ذخیره‌سازی اطلاعات مشکلی رخ داد. لطفاً دوباره تلاش کنید."
        )
