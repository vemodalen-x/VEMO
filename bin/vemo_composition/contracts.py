"""Declarative contracts and typed contribution points for VEMO composition."""

import json
from pathlib import PurePosixPath
import re


MANIFEST_SCHEMA_VERSION = 1
MAX_CAPABILITIES = 64
MAX_SEAMS = 32
MAX_TOTAL_SEAMS = 128
PLATFORM_OWNERS = {"ingress", "control", "policy", "execution", "enforcement", "evidence"}
ROLE_IDS = {"definition", "provider", "consumer"}
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_VERSION_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]*$")


class ExtensionManifestError(ValueError):
    """Carry content-minimized validation issues for one rejected manifest. @codex-comment"""

    def __init__(self, issues):
        """Preserve normalized issue rows behind a non-sensitive message. @codex-comment"""
        super().__init__("extension manifest is invalid")
        self.issues = list(issues)


class _DuplicateJsonKey(ValueError):
    """Signal duplicate JSON object keys without exposing their values. @codex-comment"""


def issue(code, **details):
    """Build a stable diagnostic from allowlisted metadata only. @codex-comment"""
    row = {"code": code}
    row.update({key: value for key, value in details.items() if value is not None})
    return row


def _unique_json_object(pairs):
    """Reject duplicate JSON keys so later values cannot override contract data. @codex-comment"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey()
        result[key] = value
    return result


def decode_json(data):
    """Decode bounded UTF-8 JSON and return a stable error code instead of parser text. @codex-comment"""
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_json_object), None
    except UnicodeDecodeError:
        return None, "json_not_utf8"
    except _DuplicateJsonKey:
        return None, "json_duplicate_key"
    except (RecursionError, ValueError, TypeError):
        return None, "json_invalid"


def safe_relative_path(value):
    """Accept one normalized POSIX-relative path with no traversal, drive, or NUL. @codex-comment"""
    if not isinstance(value, str) or not value or len(value) > 240:
        return False
    if "\x00" in value or "\\" in value or value.startswith("/"):
        return False
    path = PurePosixPath(value)
    if path.as_posix() != value or path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        return False
    return not (path.parts and ":" in path.parts[0])


def valid_id(value):
    """Validate stable extension, capability, contribution, and item identifiers. @codex-comment"""
    return isinstance(value, str) and len(value) <= 96 and bool(_ID_PATTERN.fullmatch(value))


def _valid_label(value):
    """Accept a bounded UTF-8 display label without terminal control characters. @codex-comment"""
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


class ContributionSpec:
    """Define one trusted declarative contribution validator and aggregation policy. @codex-comment"""

    def __init__(
        self, key, validate_item, identity, *, max_per_manifest, max_total,
        count_code, duplicate_code, total_code, diagnostic_field="item",
    ):
        """Validate a spec's stable key, callbacks, limits, and diagnostic vocabulary. @codex-comment"""
        if not valid_id(key) or not callable(validate_item) or not callable(identity):
            raise ValueError("contribution spec needs a stable key and callable validators")
        if any(isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
               for limit in (max_per_manifest, max_total)):
            raise ValueError("contribution limits must be positive integers")
        if not all(isinstance(code, str) and code for code in (count_code, duplicate_code, total_code)):
            raise ValueError("contribution diagnostics must be non-empty strings")
        if not isinstance(diagnostic_field, str) or not diagnostic_field:
            raise ValueError("contribution diagnostic field must be non-empty")
        self.key = key
        self.validate_item = validate_item
        self.identity = identity
        self.max_per_manifest = max_per_manifest
        self.max_total = max_total
        self.count_code = count_code
        self.duplicate_code = duplicate_code
        self.total_code = total_code
        self.diagnostic_field = diagnostic_field

    def validate(self, value, extension_id, source):
        """Normalize one manifest's items through the spec's bounded trusted validator. @codex-comment"""
        if not isinstance(value, list) or len(value) > self.max_per_manifest:
            return [], [issue(self.count_code, extension=extension_id, source=source)]
        normalized_items = []
        issues = []
        for item in value:
            normalized, item_issues = self.validate_item(item, extension_id, source)
            issues.extend(item_issues)
            if normalized is not None:
                try:
                    item_id = self.identity(normalized)
                except Exception:
                    item_id = None
                if not valid_id(item_id):
                    issues.append(issue(
                        "contribution_identity_invalid", extension=extension_id,
                        source=source, contribution=self.key,
                    ))
                else:
                    normalized_items.append(normalized)
        identities = [self.identity(item) for item in normalized_items]
        if len(identities) != len(set(identities)):
            issues.append(issue(self.duplicate_code, extension=extension_id, source=source))
        return normalized_items, issues


def _validate_string_list(value, field, extension_id, source, allow_empty=True):
    """Normalize a bounded unique capability list and report schema failures. @codex-comment"""
    issues = []
    if not isinstance(value, list):
        return [], [issue("manifest_field_type", extension=extension_id, source=source, field=field)]
    if len(value) > MAX_CAPABILITIES or (not allow_empty and not value):
        return [], [issue("manifest_field_count", extension=extension_id, source=source, field=field)]
    normalized = []
    for item in value:
        if not valid_id(item):
            issues.append(issue("manifest_capability_invalid", extension=extension_id, source=source, field=field))
            continue
        normalized.append(item)
    if len(normalized) != len(set(normalized)):
        issues.append(issue("manifest_capability_duplicate", extension=extension_id, source=source, field=field))
    return normalized, issues


def _validate_platform_role(value, extension_id, source):
    """Validate one Definition/Provider/Consumer role and its local path quorum. @codex-comment"""
    issues = []
    if not isinstance(value, dict):
        return None, [issue("platform_role_type", extension=extension_id, source=source)]
    if set(value) != {"id", "required", "minimum", "paths"}:
        issues.append(issue("platform_role_fields", extension=extension_id, source=source))
    role_id = value.get("id")
    required = value.get("required")
    minimum = value.get("minimum")
    paths = value.get("paths")
    if role_id not in ROLE_IDS:
        issues.append(issue("platform_role_id", extension=extension_id, source=source))
    if not isinstance(required, bool):
        issues.append(issue("platform_role_required", extension=extension_id, source=source))
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        issues.append(issue("platform_role_minimum", extension=extension_id, source=source))
    if not isinstance(paths, list) or not paths or len(paths) > 32:
        issues.append(issue("platform_role_paths", extension=extension_id, source=source))
        paths = []
    elif any(not safe_relative_path(path) for path in paths):
        issues.append(issue("platform_role_path_unsafe", extension=extension_id, source=source))
    elif len(paths) != len(set(paths)):
        issues.append(issue("platform_role_path_duplicate", extension=extension_id, source=source))
    if isinstance(minimum, int) and not isinstance(minimum, bool) and paths and minimum > len(paths):
        issues.append(issue("platform_role_minimum", extension=extension_id, source=source))
    if issues:
        return None, issues
    return {"id": role_id, "required": required, "minimum": minimum, "paths": list(paths)}, []


def _validate_platform_seam(value, extension_id, source):
    """Validate one platform seam contribution and require all composition roles. @codex-comment"""
    issues = []
    if not isinstance(value, dict):
        return None, [issue("platform_seam_type", extension=extension_id, source=source)]
    if set(value) != {"id", "name", "owner", "roles"}:
        issues.append(issue("platform_seam_fields", extension=extension_id, source=source))
    seam_id = value.get("id")
    name = value.get("name")
    owner = value.get("owner")
    roles = value.get("roles")
    if not valid_id(seam_id):
        issues.append(issue("platform_seam_id", extension=extension_id, source=source))
    if not _valid_label(name):
        issues.append(issue("platform_seam_name", extension=extension_id, source=source))
    if owner not in PLATFORM_OWNERS:
        issues.append(issue("platform_seam_owner", extension=extension_id, source=source))
    if not isinstance(roles, list) or len(roles) != 3:
        issues.append(issue("platform_seam_roles", extension=extension_id, source=source))
        roles = []
    normalized_roles = []
    for role in roles:
        normalized, role_issues = _validate_platform_role(role, extension_id, source)
        issues.extend(role_issues)
        if normalized is not None:
            normalized_roles.append(normalized)
    if normalized_roles and {role["id"] for role in normalized_roles} != ROLE_IDS:
        issues.append(issue("platform_seam_role_set", extension=extension_id, source=source))
    if issues:
        return None, issues
    return {"id": seam_id, "name": name.strip(), "owner": owner, "roles": normalized_roles}, []


PLATFORM_SEAM_SPEC = ContributionSpec(
    "platform_seams",
    _validate_platform_seam,
    lambda seam: seam["id"],
    max_per_manifest=MAX_SEAMS,
    max_total=MAX_TOTAL_SEAMS,
    count_code="platform_seam_count",
    duplicate_code="platform_seam_duplicate",
    total_code="platform_seam_total_limit",
    diagnostic_field="seam",
)
DEFAULT_CONTRIBUTION_SPECS = (PLATFORM_SEAM_SPEC,)


def _spec_map(contribution_specs):
    """Normalize contribution specs and reject duplicate stable keys. @codex-comment"""
    specs = tuple(contribution_specs)
    if any(not isinstance(spec, ContributionSpec) for spec in specs):
        raise TypeError("contribution specs must be ContributionSpec instances")
    mapped = {spec.key: spec for spec in specs}
    if len(mapped) != len(specs):
        raise ValueError("contribution spec keys must be unique")
    return mapped


def validate_manifest(value, source, contribution_specs=None):
    """Normalize a schema-v1 manifest through registered typed contribution specs. @codex-comment"""
    specs = _spec_map(DEFAULT_CONTRIBUTION_SPECS if contribution_specs is None else contribution_specs)
    issues = []
    if not safe_relative_path(source):
        return None, [issue("manifest_source_unsafe")]
    if not isinstance(value, dict):
        return None, [issue("manifest_type", source=source)]
    expected = {"schema_version", "id", "name", "version", "provides", "requires", "contributes"}
    if set(value) != expected:
        issues.append(issue("manifest_fields", source=source))
    extension_id = value.get("id") if valid_id(value.get("id")) else None
    if type(value.get("schema_version")) is not int or value.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        issues.append(issue("manifest_schema_version", extension=extension_id, source=source))
    if extension_id is None:
        issues.append(issue("manifest_id", source=source))
    name = value.get("name")
    version = value.get("version")
    if not _valid_label(name):
        issues.append(issue("manifest_name", extension=extension_id, source=source))
    if not isinstance(version, str) or len(version) > 40 or not _VERSION_PATTERN.fullmatch(version):
        issues.append(issue("manifest_version", extension=extension_id, source=source))
    provides, provide_issues = _validate_string_list(
        value.get("provides"), "provides", extension_id, source, allow_empty=False
    )
    requires, require_issues = _validate_string_list(
        value.get("requires"), "requires", extension_id, source, allow_empty=True
    )
    issues.extend(provide_issues)
    issues.extend(require_issues)
    contributes = value.get("contributes")
    normalized_contributions = {key: [] for key in specs}
    if not isinstance(contributes, dict) or not set(contributes) <= set(specs):
        issues.append(issue("manifest_contributions", extension=extension_id, source=source))
    else:
        for key, spec in specs.items():
            normalized, contribution_issues = spec.validate(contributes.get(key, []), extension_id, source)
            normalized_contributions[key] = normalized
            issues.extend(contribution_issues)
    if issues:
        return None, issues
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "id": extension_id,
        "name": name.strip(),
        "version": version,
        "provides": list(provides),
        "requires": list(requires),
        "contributes": normalized_contributions,
    }, []


__all__ = [
    "ContributionSpec",
    "DEFAULT_CONTRIBUTION_SPECS",
    "ExtensionManifestError",
    "MANIFEST_SCHEMA_VERSION",
    "PLATFORM_SEAM_SPEC",
    "decode_json",
    "issue",
    "safe_relative_path",
    "valid_id",
    "validate_manifest",
]
