"""Build a CAP 1.2 / ITU-T X.1303 alert envelope from a simulated alert. Y.3172 node: PP."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from ..y3172 import node

CAP_REQUIRED_FIELDS: tuple[str, ...] = (
    "identifier", "sender", "sent", "status", "msgType", "scope",
    "info.language", "info.category", "info.event", "info.urgency", "info.severity",
    "info.certainty", "info.area.areaDesc",
)

CAP_STATUS = ("Actual", "Exercise", "System", "Test", "Draft")
CAP_MSGTYPE = ("Alert", "Update", "Cancel", "Ack", "Error")
CAP_SCOPE = ("Public", "Restricted", "Private")
CAP_URGENCY = ("Immediate", "Expected", "Future", "Past", "Unknown")
CAP_SEVERITY = ("Extreme", "Severe", "Moderate", "Minor", "Unknown")
CAP_CERTAINTY = ("Observed", "Likely", "Possible", "Unlikely", "Unknown")

LANGUAGE_CODES: Mapping[str, str] = {
    "en": "en", "hi": "hi", "bn": "bn", "or": "or", "as": "as", "ta": "ta", "te": "te",
    "english": "en", "hindi": "hi", "bengali": "bn", "bangla": "bn", "odia": "or", "oriya": "or",
}

AREA_REGION: Mapping[str, str] = {
    "OD": "IN", "WB": "IN", "AS": "IN", "TN": "IN", "AP": "IN", "IN": "IN",
    "BD": "BD", "BT": "BT", "NP": "NP", "LK": "LK", "US": "US",
}
DEFAULT_REGION = "IN"

DEFAULT_STATUS = "Exercise"


def region_for_area(area: str) -> str:
    """ISO 3166-1 alpha-2 region for an area id, from its jurisdiction prefix."""
    return AREA_REGION.get(area.split("-", 1)[0].upper(), DEFAULT_REGION)


def language_tag(code: str, area: str = "") -> str:
    """RFC 3066 tag for a language code or name in an area; `und` when genuinely unmapped."""
    base = LANGUAGE_CODES.get(code.strip().lower())
    if base is None:
        return "und"
    return f"{base}-{region_for_area(area)}"


def _sent_iso(epoch_iso: Optional[str], t_minutes: int) -> str:
    """CAP `sent`: epoch + t, as a dateTime with a timezone offset. Never 'now'."""
    if not epoch_iso:
        base = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        base = datetime.fromisoformat(epoch_iso)
        if base.tzinfo is None:
            raise ValueError(f"scenario epoch {epoch_iso!r} has no timezone offset; CAP 1.2 "
                             f"requires one (e.g. 2020-05-16T08:45:00+05:30)")
    return (base + timedelta(minutes=t_minutes)).isoformat()


@node("PP")
def build_cap(*, alert_id: str, area: str, t_minutes: int, languages: Sequence[str],
              issued_by: str, severity: str = "Severe", channel: str = "cell_broadcast",
              event: str = "Cyclone", urgency: str = "Immediate", certainty: str = "Likely",
              epoch_iso: Optional[str] = None, polygon: Optional[str] = None,
              circle: Optional[str] = None, scenario_id: str = "",
              status: str = DEFAULT_STATUS, headline: str = "",
              instruction: str = "") -> dict[str, Any]:
    """Return a CAP 1.2 / X.1303 envelope as a plain dict (one `info` block)."""
    for value, allowed, name in ((status, CAP_STATUS, "status"), (urgency, CAP_URGENCY, "urgency"),
                                 (severity, CAP_SEVERITY, "severity"),
                                 (certainty, CAP_CERTAINTY, "certainty")):
        if value not in allowed:
            raise ValueError(f"CAP 1.2 {name}={value!r} is not one of {allowed}")

    langs = [lang for lang in languages if lang]
    info: dict[str, Any] = {
        "language": language_tag(langs[0], area) if langs else "und",
        "category": "Met",
        "event": event,
        "urgency": urgency,
        "severity": severity,
        "certainty": certainty,
        "area": {"areaDesc": area},
        "parameter": [
            {"valueName": "languages", "value": ",".join(langs) or "none"},
            {"valueName": "languageTags",
             "value": ",".join(language_tag(x, area) for x in langs) or "und"},
            {"valueName": "channel", "value": channel},
            {"valueName": "layer:simulated", "value": "true"},
        ],
    }
    if polygon:
        info["area"]["polygon"] = check_polygon(polygon)
    if circle:
        info["area"]["circle"] = check_circle(circle)
    if headline:
        info["headline"] = headline
    if instruction:
        info["instruction"] = instruction

    return {
        "identifier": alert_id,
        "sender": f"{issued_by}@chakravyuh.sim",
        "sent": _sent_iso(epoch_iso, t_minutes),
        "status": status,
        "msgType": "Alert",
        "scope": "Public",
        "note": f"simulated alert from CHAKRAVYUH scenario {scenario_id or 'unknown'}; "
                f"shape per ITU-T X.1303 / OASIS CAP 1.2; not issued by any authority",
        "info": info,
    }


def check_polygon(polygon: str) -> str:
    """Validate a CAP 1.2 `polygon`: >=4 space-separated `lat,lon` pairs, first pair == last."""
    pairs = polygon.split()
    if len(pairs) < 4:
        raise ValueError(f"CAP 1.2 polygon needs at least 4 points, got {len(pairs)}: {polygon!r}")
    for pair in pairs:
        lat, _, lon = pair.partition(",")
        if not lon:
            raise ValueError(f"CAP 1.2 polygon point {pair!r} is not 'lat,lon'")
        for value, name, limit in ((lat, "latitude", 90.0), (lon, "longitude", 180.0)):
            try:
                number = float(value)
            except ValueError as exc:
                raise ValueError(f"CAP 1.2 polygon {name} {value!r} is not a number") from exc
            if abs(number) > limit:
                raise ValueError(f"CAP 1.2 polygon {name} {number} is out of range")
    if pairs[0] != pairs[-1]:
        raise ValueError(f"CAP 1.2 polygon is not closed: first point {pairs[0]!r} != "
                         f"last {pairs[-1]!r}")
    return polygon


def check_circle(circle: str) -> str:
    """Validate a CAP 1.2 `circle`: `lat,lon radius-in-km`."""
    point, _, radius = circle.partition(" ")
    lat, _, lon = point.partition(",")
    if not lon or not radius:
        raise ValueError(f"CAP 1.2 circle {circle!r} is not 'lat,lon radius'")
    try:
        if abs(float(lat)) > 90 or abs(float(lon)) > 180 or float(radius) < 0:
            raise ValueError(f"CAP 1.2 circle {circle!r} is out of range")
    except ValueError as exc:
        raise ValueError(f"CAP 1.2 circle {circle!r} is not numeric: {exc}") from exc
    return circle


def cap_shape_errors(cap: Mapping[str, Any]) -> list[str]:
    """Names of `CAP_REQUIRED_FIELDS` that are missing or empty. Empty list = well-formed."""
    errors: list[str] = []
    for path in CAP_REQUIRED_FIELDS:
        cursor: Any = cap
        for part in path.split("."):
            if not isinstance(cursor, Mapping) or part not in cursor:
                cursor = None
                break
            cursor = cursor[part]
        if cursor in (None, "", [], {}):
            errors.append(path)
    return errors
