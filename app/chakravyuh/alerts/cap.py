"""Build a CAP 1.2 / ITU-T X.1303 alert envelope from a simulated alert. Y.3172 node: PP.

Why this exists as its own module. The simulator's `Alert` is an internal record: an area, a
time, a list of languages. That is enough to score property P3, but it is not enough to show a
judge that what `sdma_alerts` emits is the *shape* a real alerting authority emits. ITU-T X.1303
is the ITU's own adoption of OASIS CAP 1.2, and SACHET -- India's national alerting platform --
publishes CAP 1.2. So the envelope is built here, deterministically, from the alert plus the
scenario's own metadata, and stored on the alert itself.

Honest scope:
  - The FIELD NAMES and their allowed values are CAP 1.2 / X.1303. Nothing here is invented.
  - The VALUES are the simulation's. `areaDesc` is the scenario's area id and the polygon is the
    scenario's declared district polygon; where the scenario declares no polygon the field is
    absent rather than filled with a made-up boundary.
  - This is not a published alert. It is never signed and never leaves the run directory.

No LLM is involved, so an alert's shape is identical on every replay.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from ..y3172 import node

# CAP 1.2 / X.1303 element paths that a well-formed single-info alert must carry. Checked by
# `cap_shape_errors` and asserted in tests, so an envelope cannot silently lose a field.
CAP_REQUIRED_FIELDS: tuple[str, ...] = (
    "identifier", "sender", "sent", "status", "msgType", "scope",
    "info.language", "info.category", "info.event", "info.urgency", "info.severity",
    "info.certainty", "info.area.areaDesc",
)

# CAP 1.2 enumerations, used so a wrong value fails here rather than in a validator downstream.
CAP_STATUS = ("Actual", "Exercise", "System", "Test", "Draft")
CAP_MSGTYPE = ("Alert", "Update", "Cancel", "Ack", "Error")
CAP_SCOPE = ("Public", "Restricted", "Private")
CAP_URGENCY = ("Immediate", "Expected", "Future", "Past", "Unknown")
CAP_SEVERITY = ("Extreme", "Severe", "Moderate", "Minor", "Unknown")
CAP_CERTAINTY = ("Observed", "Likely", "Possible", "Unlikely", "Unknown")

# CAP's `info/language` element takes an RFC 3066 tag (`bn-IN`), not a bare language code
# (`bn`) and not a language name ("Bengali"). The simulator stores bare ISO 639-1 codes, because
# that is what a scenario's `local_languages` block is written in, so the tag has to be assembled
# from the code plus a region. `und` is the ISO 639-2 code for "undetermined" and is what CAP
# expects when the language genuinely is not known -- it must never stand in for "we did not
# bother to map this", which is why `language_tag` is total over the codes the scenarios use.
LANGUAGE_CODES: Mapping[str, str] = {
    "en": "en", "hi": "hi", "bn": "bn", "or": "or", "as": "as", "ta": "ta", "te": "te",
    # Tolerate names as well as codes: a hand-written pack or a model-written param may use either.
    "english": "en", "hindi": "hi", "bengali": "bn", "bangla": "bn", "odia": "or", "oriya": "or",
}

# Area-id prefix -> ISO 3166-1 alpha-2 region. The same language takes a different tag on each
# side of the border (`bn-IN` in West Bengal, `bn-BD` in Khulna) and P3 is precisely a
# cross-border property, so the region cannot be hard-coded to IN.
AREA_REGION: Mapping[str, str] = {
    "OD": "IN", "WB": "IN", "AS": "IN", "TN": "IN", "AP": "IN", "IN": "IN",
    "BD": "BD", "BT": "BT", "NP": "NP", "LK": "LK", "US": "US",
}
DEFAULT_REGION = "IN"

# A run is an exercise, not a live alert. CAP 1.2 has an element that says exactly this, and
# using "Actual" for a simulated alert would be the one genuinely misleading choice available.
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
    """CAP `sent`: epoch + t, as a dateTime with a timezone offset. Never 'now'.

    CAP 1.2 requires an offset and forbids a bare local time. `sent` must be a function of the
    scenario clock alone: deriving it from wall-clock time would make a replayed run produce a
    different envelope every time, which is exactly what the record/replay design exists to stop.
    """
    if not epoch_iso:
        # No epoch declared: emit the offset the scenario clock is measured in, from T+0.
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
    """Return a CAP 1.2 / X.1303 envelope as a plain dict (one `info` block).

    `languages` are the languages the alert was actually issued in. CAP's `info.language` is
    single-valued, so the first language becomes the block's tag and the rest are recorded in
    `info.parameter` -- the CAP-sanctioned place for data with no dedicated element. A real
    multilingual alert uses one `info` block per language; we keep one block and record the set,
    because P3 scores *whether* a local language was used, not how the blocks were split.
    """
    for value, allowed, name in ((status, CAP_STATUS, "status"), (urgency, CAP_URGENCY, "urgency"),
                                 (severity, CAP_SEVERITY, "severity"),
                                 (certainty, CAP_CERTAINTY, "certainty")):
        if value not in allowed:
            raise ValueError(f"CAP 1.2 {name}={value!r} is not one of {allowed}")

    langs = [lang for lang in languages if lang]
    info: dict[str, Any] = {
        "language": language_tag(langs[0], area) if langs else "und",
        "category": "Met",                      # CAP 1.2 category for meteorological hazards
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
        "sender": f"{issued_by}@chakravyuh.sim",   # not a real alerting authority OID
        "sent": _sent_iso(epoch_iso, t_minutes),
        "status": status,
        "msgType": "Alert",
        "scope": "Public",
        "note": f"simulated alert from CHAKRAVYUH scenario {scenario_id or 'unknown'}; "
                f"shape per ITU-T X.1303 / OASIS CAP 1.2; not issued by any authority",
        "info": info,
    }


def check_polygon(polygon: str) -> str:
    """Validate a CAP 1.2 `polygon`: >=4 space-separated `lat,lon` pairs, first pair == last.

    CAP 1.2 requires the ring to be closed. An unclosed ring is the single most common CAP
    authoring error and it is silent: most parsers accept it and draw a different area.
    """
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
