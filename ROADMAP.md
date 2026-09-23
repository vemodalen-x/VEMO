# Roadmap

VEMO adds nothing to the core until a repeated failure cannot be solved by the existing five concepts.

Near-term work:

- exercise the minimal kernel in several real repositories;
- exercise the optional Fleet control plane against mixed installed, unmanaged, stale, and unavailable projects;
- measure false blocks, escaped scope violations, stale-evidence blocks, and time-to-first-verified-change;
- improve adapters without adding policy logic outside `enforcement/core.py`;
- validate Fleet launchers on macOS and Windows and split bundled plugins into independently installable packages
  only if real adoption requires it.

Explicitly out of core:

- model routing;
- workflow orchestration;
- fleet management and dashboards (implemented only as the optional local Fleet plugin);
- remote monitoring and telemetry analytics;
- sandbox implementation;
- policy marketplaces and remote plugin registries.
