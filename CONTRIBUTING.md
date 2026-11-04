# Contributing to Oarumi

Humans and AI agents are both welcome. Both follow the same review process.
Agents have additional requirements in [AGENT.md](AGENT.md).

---

## Before you start

- Read [README.md](README.md) for orientation.
- Read [HANDOVER.md](HANDOVER.md) § 5 for load-bearing decisions.
- Check [TODO.md](TODO.md) for unclaimed work.
- Skim [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — you need the map.

## Development setup

```bash
git clone https://github.com/<org>/oarumi.git
cd oarumi
./scripts/bootstrap.sh
```

`bootstrap.sh` is idempotent. It installs Python deps, seeds the SQLite
language DB, downloads small dev-time model stubs (not the full model stack),
and sets up git hooks that run validators on commit.

Manual setup: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Finding something to work on

- Issues labeled `good first issue` are scoped for new contributors.
- Issues labeled `agent-friendly` are scoped for AI agents.
- Everything in [TODO.md](TODO.md) with a blank `Owner` is unclaimed.
- **Claim before you work.** Comment on the issue or add your name to TODO.md
  in the same PR. This prevents duplicate effort.

## The contribution loop

1. **Issue first** for non-trivial changes. Bug fixes and doc improvements
   can go straight to PR.
2. **Branch**: `feat/<slug>`, `fix/<slug>`, or `agent/<id>/<slug>`.
3. **Change small**: one logical change per PR.
4. **Test**: `./scripts/verify_all.sh` must pass locally.
5. **Document**: update the relevant docs in the same PR. If you changed a
   language file, update `docs/LANGUAGE_SPEC.md` and `CHANGELOG.md`.
6. **PR**: fill out the template. Include what/why/how-verified.
7. **Review**: a maintainer reviews. High-risk changes (see
   [AGENT.md](AGENT.md) § 4) require two maintainers.

## What to contribute

| Type | Welcome? | Notes |
|---|---|---|
| Bug fixes | Yes | Include a regression test |
| New tests | Yes | Especially parity tests |
| Documentation | Yes | Keep it factual; link to sources |
| New languages in the pivot | Yes | Requires parallel corpus and a LoRA adapter |
| New models | Discuss first | Open an issue; models affect reliability |
| Language spec changes | ADR required | See below |
| UI changes | Yes | Screenshots in PR |
| Performance work | Yes | Include benchmarks |
| Renames / rebrands | **No** | The name is fixed by ADR-0005 |

## Language spec changes

Any change to `language/` is high-risk because it cascades everywhere.

1. Open an issue describing the change and its rationale.
2. Write an ADR in `docs/adr/` using the template.
3. Get sign-off from two maintainers.
4. Make the change, update `LANGUAGE_SPEC.md`, add a CHANGELOG entry.
5. Run `./scripts/verify_all.sh` and all parity suites with
   `OARUMI_STRICT_PARITY=1`.

## Code style

- **Python**: PEP 8, `ruff` for lint, `black` for format, `mypy --strict` for types.
- **Kotlin**: `ktlint`, no wildcard imports, prefer `val` over `var`.
- **YAML/SQL**: 2-space indent; validated by `tools/validate_schemas.py`.

## Commit messages

Conventional Commits: `type(scope): summary`. Types: `feat`, `fix`, `docs`,
`test`, `refactor`, `perf`, `chore`, `ci`, `lang` (language-file changes).

Example: `lang(primes): add DO-combinator for instrument role`

## Review expectations

- Maintainers respond to PRs within 5 business days.
- Agents: if a PR has no review after 7 days, ping the issue with a status
  comment (do not close and reopen).
- If a change is contested, the decision goes to an ADR.

## Community

- Discord / Matrix: link in pinned issue #1.
- Weekly maintainer sync: time in pinned issue.
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing, you agree your contribution is licensed under Apache 2.0.
