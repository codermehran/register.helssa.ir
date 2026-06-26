from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0004_visitevent_visitreport_and_more"),
    ]

    operations = [
        migrations.AddField("visitevent", "masked_ip", models.CharField(blank=True, db_index=True, max_length=64, verbose_name="آی‌پی ماسک‌شده")),
        migrations.AddField("visitevent", "ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="آی‌پی کامل")),
        migrations.AddField("visitevent", "device_type", models.CharField(blank=True, db_index=True, max_length=32, verbose_name="نوع دستگاه")),
        migrations.AddField("visitevent", "browser", models.CharField(blank=True, max_length=80, verbose_name="مرورگر")),
        migrations.AddField("visitevent", "os", models.CharField(blank=True, max_length=80, verbose_name="سیستم‌عامل")),
        migrations.AddField("visitevent", "is_bot", models.BooleanField(db_index=True, default=False, verbose_name="ربات")),
        migrations.AddField("visitevent", "utm_source", models.CharField(blank=True, db_index=True, max_length=120, verbose_name="منبع UTM")),
        migrations.AddField("visitevent", "utm_medium", models.CharField(blank=True, max_length=120, verbose_name="مدیوم UTM")),
        migrations.AddField("visitevent", "utm_campaign", models.CharField(blank=True, db_index=True, max_length=120, verbose_name="کمپین UTM")),
        migrations.AddField("visitevent", "utm_content", models.CharField(blank=True, max_length=120, verbose_name="محتوای UTM")),
        migrations.AddField("visitevent", "utm_term", models.CharField(blank=True, max_length=120, verbose_name="کلمه UTM")),
    ]
