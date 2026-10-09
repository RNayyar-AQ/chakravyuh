"""CAP 1.2 / ITU-T X.1303 alert envelopes. Y.3172 node: PP (format, no model)."""
from .cap import CAP_REQUIRED_FIELDS, build_cap, cap_shape_errors

__all__ = ["CAP_REQUIRED_FIELDS", "build_cap", "cap_shape_errors"]
