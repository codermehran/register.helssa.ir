from django.db import migrations, models


def mark_patients_with_successful_done_sms(apps, _schema_editor):
    from django.conf import settings

    done_template = getattr(settings, "KAVENEGAR_DONE_TEMPLATE", "")
    if not done_template:
        return

    Patient = apps.get_model("patients", "Patient")
    SMSMessageLog = apps.get_model("patients", "SMSMessageLog")
    patient_ids = SMSMessageLog.objects.filter(
        patient__isnull=False,
        status="success",
        template=done_template,
    ).values("patient_id")
    Patient.objects.filter(pk__in=patient_ids).update(done_sms_sent=True)


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0005_visitevent_analytics_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="done_sms_sent",
            field=models.BooleanField(default=False, verbose_name="پیامک انجام شد"),
        ),
        migrations.RunPython(
            mark_patients_with_successful_done_sms,
            migrations.RunPython.noop,
        ),
    ]
