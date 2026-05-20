from django import forms

from .models import Patient


DUPLICATE_MOBILE_ERROR = "این شماره قبلاً ثبت شده است."
DUPLICATE_NATIONAL_CODE_ERROR = "این کد ملی قبلاً ثبت شده است."


class PatientRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        label="نام",
        required=True,
        widget=forms.TextInput(
            attrs={"autocomplete": "given-name", "placeholder": "مثلاً علی"}
        ),
        error_messages={"required": "نام را وارد کنید."},
    )
    last_name = forms.CharField(
        label="نام خانوادگی",
        required=True,
        widget=forms.TextInput(
            attrs={"autocomplete": "family-name", "placeholder": "مثلاً رضایی"}
        ),
        error_messages={"required": "نام خانوادگی را وارد کنید."},
    )
    national_code = forms.CharField(
        label="کد ملی",
        required=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "aria-describedby": "national-code-help",
                "dir": "ltr",
                "inputmode": "numeric",
                "maxlength": "10",
                "placeholder": "1234567890",
            }
        ),
        error_messages={"required": "کد ملی را وارد کنید."},
    )

    mobile = forms.CharField(
        label="شماره موبایل",
        required=True,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "tel",
                "aria-describedby": "mobile-help",
                "dir": "ltr",
                "inputmode": "numeric",
                "maxlength": "11",
                "placeholder": "09123456789",
            }
        ),
        error_messages={"required": "شماره موبایل را وارد کنید."},
    )

    class Meta:
        model = Patient
        fields = ["first_name", "last_name", "national_code", "mobile"]

    def clean_mobile(self):
        mobile = self.cleaned_data["mobile"]

        if len(mobile) != 11:
            raise forms.ValidationError("شماره را ۱۱ رقمی وارد کنید.")

        if not mobile.isdigit():
            raise forms.ValidationError("فقط عدد وارد کنید.")

        if not mobile.startswith("09"):
            raise forms.ValidationError("شماره موبایل با 09 شروع شود.")

        if Patient.objects.filter(mobile=mobile).exists():
            raise forms.ValidationError(DUPLICATE_MOBILE_ERROR)

        return mobile

    def clean_national_code(self):
        national_code = self.cleaned_data["national_code"]

        if len(national_code) != 10:
            raise forms.ValidationError("کد ملی را ۱۰ رقمی وارد کنید.")

        if not national_code.isdigit():
            raise forms.ValidationError("کد ملی باید فقط شامل عدد باشد.")

        if Patient.objects.filter(national_code=national_code).exists():
            raise forms.ValidationError(DUPLICATE_NATIONAL_CODE_ERROR)

        return national_code
