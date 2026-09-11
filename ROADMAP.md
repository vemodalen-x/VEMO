# Roadmap

VEMO adds nothing to the core until a repeated failure cannot be solved by the existing five concepts.

Near-term work:

- exercise the minimal kernel in several real repositories;
- measure false blocks, escaped scope violations, stale-evidence blocks, and time-to-first-verified-change;
- improve adapters without adding policy logic outside `enforcement/core.py`;
- split bundled plugin implementation files into independently installable packages if real adoption requires it.

Explicitly out of core:

- model routing;
- workflow orchestration;
- fleet management;
- dashboards and telemetry analytics;
- sandbox implementation;
- policy marketplaces and remote plugin registries.
