# Standards and Commercial Governance Mapping

VEMO uses public frameworks as design inputs and vocabulary. This mapping is evidence-oriented: it identifies which
VEMO mechanisms support an outcome and where an external control is still required. It is not a certification,
attestation, legal opinion, or claim of full conformance.

## Design baseline

- [NIST SSDF 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) provides outcome-based secure development practices
  that can be integrated into an existing SDLC. VEMO maps task planning, protected development, verification evidence,
  and vulnerability-response documentation to those outcomes.
- [NIST CSF 2.0](https://www.nist.gov/cyberframework) adds a GOVERN function and emphasizes supply-chain risk.
  Fleet profiles provide a local policy inventory; accountable ownership, risk appetite, supplier management, and
  incident governance remain organizational responsibilities.
- [SLSA 1.2](https://slsa.dev/spec/v1.2/) separates Source and Build tracks and prefers explicit provenance over
  inference. VEMO receipts and judge records are local evidence; signed source/build provenance must be issued and
  verified by the source control or hosted build platform.
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
  informs least privilege, explicit approval for elevated actions, execution boundaries, audit trails, and fail-secure
  defaults in VEMO's agent governance model.
- [OpenSSF Scorecard](https://github.com/ossf/scorecard) informs repository-health checks such as branch protection,
  review, CI tests, token permissions, dependency updates, security policy, and signed releases. Scorecard findings are
  heuristics, not a universal pass/fail authority; VEMO follows the same caveat.

## Outcome mapping

| Outcome | VEMO evidence/mechanism | External or manual control still required |
|---|---|---|
| Document development requirements | versioned specs, profiles, task criteria | organization risk appetite and legal requirements |
| Protect source changes | scope guard, secret gate, risk-tier integrity | identity provider, least privilege, protected branches |
| Review critical changes | R2 human review and independent judge provenance | source-platform review enforcement and reviewer independence |
| Execute verification | `vemo verify` receipt and evidence log | product-specific test adequacy and independent test environment |
| Detect governance drift | Fleet status, strict JSON report, doctor/selfcheck | scheduled execution and accountable remediation owner |
| Preserve audit evidence | task history, judge log, Fleet hash chain | retention policy, access controls, external immutable storage |
| Secure dependencies | profile checks for update automation | SBOM, vulnerability triage, supplier acceptance policy |
| Prove artifact origin | release-provenance readiness check | hosted build, signed attestation, trusted builder policy, verification |
| Respond and recover | task failure dispositions and security policy check | incident plan, notification duties, recovery tests and objectives |

## Profile interpretation

`solo`, `team`, and `regulated` express increasing operating maturity. They intentionally combine machine-detectable
checks with clearly listed manual controls. A 100% local readiness score means only that required detectable controls
were present; it does not verify remote branch settings, organizational behavior, control effectiveness, or legal
compliance.

For commercial deployment, treat Fleet JSON as one input to a broader assurance process. Validate remote controls via
the hosting platform API, generate signed artifact attestations in hosted CI, retain evidence independently, and review
exceptions with an accountable owner and expiration date.
