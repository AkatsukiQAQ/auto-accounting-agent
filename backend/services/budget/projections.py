from decimal import Decimal, ROUND_HALF_UP


def project_spend(spent: int, elapsed: int, total: int) -> int:
    if elapsed == 0:
        return 0
    return int((Decimal(spent) * total / elapsed).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def item_status(spent: int, limit: int, elapsed: int, total: int,
                warning_ratio: float = 0.8, watch_ratio: float = 0.6) -> str:
    if spent > limit:
        return "over"
    if limit <= 0:
        return "safe"
    used = Decimal(spent) / limit
    if used >= Decimal(str(warning_ratio)) and spent * total > limit * elapsed:
        return "warning"
    if used >= Decimal(str(watch_ratio)):
        return "watch"
    return "safe"
