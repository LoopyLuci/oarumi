# Security Policy

## Reporting a vulnerability

Email security@oarumi.com. Do **not** open a public issue for vulnerabilities.
Acknowledge target: 48 hours. Fix target: 14 days for critical.

## Scope

- The desktop and Android applications.
- The model manifest and download pipeline.
- The CI/CD configuration.
- The `oarumi.com` domain and its DNS.

## Model supply-chain integrity

- Model files are referenced by manifest, never committed.
- Each manifest records SHA-256 of every artifact.
- The apps verify the hash before loading a model into memory.
- Publishing a new model version is a high-risk change (see AGENT.md § 4).
- Manifests are signed; the public key is pinned in `models/manifests/TRUSTED_KEYS`.

## Threat model

See `docs/adr/0005-threat-model.md` (in progress). High-level:
- **Adversary:** supply-chain attacker replacing a model file, a dependency, or the domain.
- **Mitigation:** hash pinning, signed manifests, SBOM generation, dependency
  scanning in CI, domain registrar lock, two-maintainer sign-off for manifest
  changes.

## Supported versions

Only the latest minor release receives security fixes during pre-alpha.
