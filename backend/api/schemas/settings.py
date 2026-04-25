from __future__ import annotations

# Settings DTOs are intentionally absent: the frontend contract is that
# GET returns `{data: Settings}` where Settings is a free-form JSON tree,
# and PATCH body is the partial tree itself (not wrapped in a `patch` key).
# Routes use `dict[str, Any]` directly and wrap with the generic `Data[...]`
# envelope from `backend.api.schemas.base`.
