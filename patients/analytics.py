import hashlib
import logging
import uuid
from collections import OrderedDict

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from .models import VisitEvent

logger = logging.getLogger(__name__)


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def hash_ip(ip):
    if not ip:
        return ""
    salt = getattr(settings, "ANALYTICS_IP_HASH_SALT", settings.SECRET_KEY)
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()


def _valid_uuid(value):
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return ""


def get_or_create_visitor_id(request, response=None):
    cookie_name = getattr(settings, "ANALYTICS_VISITOR_COOKIE_NAME", "helssa_vid")
    visitor_id = _valid_uuid(request.COOKIES.get(cookie_name))
    if not visitor_id:
        visitor_id = str(uuid.uuid4())
        request.COOKIES[cookie_name] = visitor_id
        setattr(request, "_analytics_visitor_cookie_needs_update", True)

    if response is not None and getattr(request, "_analytics_visitor_cookie_needs_update", False):
        response.set_cookie(
            cookie_name,
            visitor_id,
            max_age=getattr(settings, "ANALYTICS_VISITOR_COOKIE_MAX_AGE", 60 * 60 * 24 * 365),
            httponly=True,
            samesite="Lax",
            secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
        )
        setattr(request, "_analytics_visitor_cookie_needs_update", False)
    return visitor_id


def _safe_metadata(metadata):
    if not isinstance(metadata, dict):
        return {}
    blocked = {"mobile", "national_code", "first_name", "last_name", "phone", "raw", "data"}
    return {str(k): v for k, v in metadata.items() if str(k) not in blocked}


def log_visit_event(request, event_type, response=None, patient=None, metadata=None, status_code=None):
    if not getattr(settings, "ANALYTICS_ENABLED", True):
        return None
    try:
        visitor_id = get_or_create_visitor_id(request, response=response)
        session = getattr(request, "session", None)
        session_key = getattr(session, "session_key", "") or ""
        if session is not None and not session_key:
            try:
                session.save()
                session_key = session.session_key or ""
            except Exception:
                session_key = ""
        ip = get_client_ip(request)
        raw_ip = ip if getattr(settings, "ANALYTICS_STORE_RAW_IP", False) else ""
        event_metadata = _safe_metadata(metadata)
        if raw_ip:
            event_metadata["raw_ip"] = raw_ip
        return VisitEvent.objects.create(
            visitor_id=visitor_id,
            session_key=session_key,
            event_type=event_type,
            method=request.method[:10],
            path=request.path[:255],
            query_string=request.META.get("QUERY_STRING", ""),
            referrer=request.META.get("HTTP_REFERER", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip_hash=hash_ip(ip),
            status_code=status_code if status_code is not None else getattr(response, "status_code", None),
            patient=patient,
            metadata=event_metadata,
        )
    except Exception:
        logger.exception("Failed to log visit event %s.", event_type)
        return None


def get_visit_report_queryset(start_datetime, end_datetime):
    return VisitEvent.objects.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)


def get_visit_report_summary(queryset):
    total_events = queryset.count()
    def count(event_type):
        return queryset.filter(event_type=event_type).count()
    top_paths = list(queryset.values("path").annotate(count=Count("id")).order_by("-count", "path")[:10])
    top_referrers = list(queryset.exclude(referrer="").values("referrer").annotate(count=Count("id")).order_by("-count", "referrer")[:10])
    daily = OrderedDict()
    for row in queryset.datetimes("created_at", "day", order="ASC"):
        start = row
        end = row + timezone.timedelta(days=1)
        daily[start.date().isoformat()] = queryset.filter(created_at__gte=start, created_at__lt=end).count()
    return {
        "total_events": total_events,
        "page_views": queryset.filter(event_type__in=[VisitEvent.EVENT_PAGE_VIEW, VisitEvent.EVENT_FORM_VIEW]).count(),
        "unique_visitors": queryset.values("visitor_id").distinct().count(),
        "form_views": count(VisitEvent.EVENT_FORM_VIEW),
        "submit_attempts": count(VisitEvent.EVENT_FORM_SUBMIT_ATTEMPT),
        "successful_registrations": count(VisitEvent.EVENT_FORM_SUBMIT_SUCCESS),
        "invalid_submits": count(VisitEvent.EVENT_FORM_SUBMIT_INVALID),
        "error_submits": count(VisitEvent.EVENT_FORM_SUBMIT_ERROR),
        "top_paths": top_paths,
        "top_referrers": top_referrers,
        "daily_counts": daily,
    }
