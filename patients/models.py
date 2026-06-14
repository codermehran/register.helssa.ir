from django.db import models


class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=11, unique=True)
    national_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.mobile}"


class SMSMessageLog(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_SUCCESS, "موفق"),
        (STATUS_FAILED, "ناموفق"),
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="sms_logs",
        verbose_name="بیمار",
    )
    mobile = models.CharField(max_length=11, verbose_name="شماره موبایل")
    template = models.CharField(max_length=100, verbose_name="تمپلت")
    token = models.CharField(max_length=255, verbose_name="توکن ارسال‌شده")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, verbose_name="وضعیت"
    )
    response = models.TextField(blank=True, verbose_name="پاسخ سرویس")
    error = models.TextField(blank=True, verbose_name="خطا")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ارسال")

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "لاگ پیامک"
        verbose_name_plural = "لاگ‌های پیامک"

    def __str__(self):
        return f"{self.patient} - {self.template} - {self.get_status_display()}"
