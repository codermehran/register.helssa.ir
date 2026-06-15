from django.utils import timezone


_PERSIAN_DIGITS_TRANSLATION = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _gregorian_to_jalali(year, month, day):
    """Convert a Gregorian date to a Jalali (Solar Hijri) date."""

    gregorian_month_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

    if year > 1600:
        jalali_year = 979
        year -= 1600
    else:
        jalali_year = 0
        year -= 621

    if month > 2:
        gy2 = year + 1
    else:
        gy2 = year

    days = (
        365 * year
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + day
        + gregorian_month_days[month - 1]
    )

    jalali_year += 33 * (days // 12053)
    days %= 12053
    jalali_year += 4 * (days // 1461)
    days %= 1461

    if days > 365:
        jalali_year += (days - 1) // 365
        days = (days - 1) % 365

    if days < 186:
        jalali_month = 1 + days // 31
        jalali_day = 1 + days % 31
    else:
        jalali_month = 7 + (days - 186) // 30
        jalali_day = 1 + (days - 186) % 30

    return jalali_year, jalali_month, jalali_day


def to_persian_digits(value):
    return str(value).translate(_PERSIAN_DIGITS_TRANSLATION)


def format_tehran_jalali(value):
    """Format an aware/naive datetime as Jalali date and Tehran local time."""

    if value is None:
        return "-"

    local_value = timezone.localtime(value)
    jalali_year, jalali_month, jalali_day = _gregorian_to_jalali(
        local_value.year, local_value.month, local_value.day
    )
    formatted = (
        f"{jalali_year:04d}/{jalali_month:02d}/{jalali_day:02d} "
        f"{local_value:%H:%M:%S}"
    )
    return to_persian_digits(formatted)
