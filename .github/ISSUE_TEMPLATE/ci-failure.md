---
name: CI failure
about: Report a CI regression that is not a code bug
labels: ci
---

## Which job?

<!-- ci.yml job name or nightly.yml job name -->

## Failure signature

<!-- Paste the exact error or artifact path. For bench, paste the regression line. -->

## Reproduce locally

<!-- Copy the corresponding section from docs/CI.md § 2 -->

```bash
# paste reproduction commands here
```

## Suspected cause

<!-- e.g., a flaky test, a network-dependent path, a new dependency -->

## Acceptance

- [ ] Repro'd locally
- [ ] Fix merged
- [ ] Green run on `main`
- [ ] Baseline updated if this is a bench change
