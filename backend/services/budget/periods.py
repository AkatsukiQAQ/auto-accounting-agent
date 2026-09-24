from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.services.errors import ValidationError


def period_bounds(period_type: str, on_date: date) -> tuple[date, date]:
    if period_type == "week":
        start = on_date - timedelta(days=on_date.weekday())
        return start, start + timedelta(days=6)
    if period_type == "month":
        return on_date.replace(day=1), on_date.replace(day=monthrange(on_date.year, on_date.month)[1])
    raise ValidationError("periodType must be week or month")


def zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
        raise ValidationError("Invalid profile timezone") from exc


def utc_bounds(start: date, end: date, timezone_name: str) -> tuple[datetime, datetime]:
    tz = zone(timezone_name)
    # SQLite stores naive timestamps. Existing UTC rows and new budget entries
    # are compared against a half-open UTC interval, including DST boundaries.
    return tuple(datetime.combine(d, time.min, tz).astimezone(timezone.utc).replace(tzinfo=None)
                 for d in (start, end + timedelta(days=1)))


def elapsed_days(start: date, end: date, as_of: date) -> tuple[int, int]:
    total = (end - start).days + 1
    elapsed = max(0, min(total, (as_of - start).days + 1))
    return elapsed, total - elapsed
