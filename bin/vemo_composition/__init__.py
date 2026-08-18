"""Public composition API used by VEMO's CLI and platform probes."""

from .context import CompositionContext, EffectScope, ExtensionRegistry
from .contracts import (
    ContributionSpec,
    DEFAULT_CONTRIBUTION_SPECS,
    ExtensionManifestError,
    PLATFORM_SEAM_SPEC,
    validate_manifest,
)
from .loader import ExtensionLoader, HOST_CAPABILITIES, build_extension_report, discover_extension_manifests


__all__ = [
    "CompositionContext",
    "ContributionSpec",
    "DEFAULT_CONTRIBUTION_SPECS",
    "EffectScope",
    "ExtensionLoader",
    "ExtensionManifestError",
    "ExtensionRegistry",
    "HOST_CAPABILITIES",
    "PLATFORM_SEAM_SPEC",
    "build_extension_report",
    "discover_extension_manifests",
    "validate_manifest",
]
