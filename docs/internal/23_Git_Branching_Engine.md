# Git Branching Engine

This document explains the *system*, not the commands — what each branch is for, how CI cost maps to each one, how the enforcement gate actually blocks a bad merge, and how a release flows through to the in-app update banner. For day-to-day commands (how to open a PR, commit format, hotfix steps), see [CONTRIBUTING.md](https://github.com/KalaimaranB/BioPro/blob/main/CONTRIBUTING.md).

## The branches

| Branch | Role | Protection | Lifetime |
| --- | --- | --- | --- |
| `main` | Production. What a released build was compiled from. | Protected, `enforce_admins: true`, requires `audit-and-lint` + `test` + `enforce-workflow` | Permanent |
| `develop` | Staging/integration. Where feature work lands and accumulates before a release. | Protected, `enforce_admins: true`, requires `audit-and-lint` + `enforce-workflow` | Permanent |
| `feature/*`, `fix/*`, `chore/*`, `docs/*` | A single unit of work | None (auto-deleted on merge) | Days |
| `hotfix/*` | An urgent fix that can't wait for the next `develop → main` promotion | None (auto-deleted on merge) | Hours |

```mermaid
gitGraph
   commit id: "..."
   branch develop
   checkout develop
   commit id: "..."
   branch feature/x
   checkout feature/x
   commit id: "feat: x"
   checkout develop
   merge feature/x tag: "squash"
   branch fix/y
   checkout fix/y
   commit id: "fix: y"
   checkout develop
   merge fix/y tag: "squash"
   checkout main
   merge develop tag: "promotion"
   checkout develop
   commit id: "next work"
   checkout main
   branch hotfix/z
   checkout hotfix/z
   commit id: "fix: z, patch bump"
   checkout main
   merge hotfix/z tag: "squash"
   checkout develop
   merge main tag: "back-merge"
```

Everything short-lived (`feature/*`, `fix/*`, `chore/*`, `docs/*`, `hotfix/*`) points at `develop` or `main` and disappears on merge. Only `main` and `develop` are permanent — that's deliberate: a permanent branch is something you have to protect, gate, and reason about forever, so the count is kept to exactly the two that need it.

## Why CI cost differs by branch

`pipeline.yml` triggers on both `main` and `develop`, but the expensive jobs are gated by which one is the *target*:

- **Every PR into `develop`**: `audit-and-lint` (ruff, mypy, pip-audit, one ubuntu pytest run) + `enforce-workflow`. This is the cheap, fast-fail tier — cheap enough to run on every small feature merge without worrying about cloud spend.
- **Only the `develop → main` promotion PR** (or a direct push to `main`, or manual dispatch): additionally runs the `test` job's full macOS + Windows matrix, and — if `pyproject.toml`'s version was bumped — `build` (PyInstaller compilation on both platforms), `generate-registry`, SLSA provenance, and the GitHub Release itself.

The tradeoff being made: cross-platform coverage and packaging are expensive (multiple paid runner-minutes per run) and only actually matter right before something ships. Day-to-day feature work doesn't need macOS/Windows executables built on every commit — it needs fast feedback. Concentrating the expensive tier at the promotion point means you pay for full coverage exactly once per release, not once per feature branch.

## How `enforce-workflow` is a hard gate, not a suggestion

`enforce-workflow` is a required status check on both `develop` and `main` branch protection, with `enforce_admins: true`. Concretely, on every `pull_request` event it:

1. Regex-checks the PR title against Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`, optional `(scope)` and `!`).
2. Checks `github.base_ref`/`github.head_ref`: a PR targeting `main` must come from `develop` or `hotfix/*`; a PR targeting `develop` must come from `feature/*`, `fix/*`, `chore/*`, `docs/*`, or `hotfix/*`.

If either check fails, the job exits non-zero and the check goes red. Because it's a *required* check on a *protected* branch with admin enforcement on, GitHub's merge button is disabled for that PR — there is no environment where a `feature/x → main` PR or a non-conventional title can be merged through the UI or API, including by the repo owner. This is what makes the branch model real instead of a convention that erodes the moment things get busy.

## How a release reaches the update banner

This is the self-published registry flow, replacing the old path where the app depended on `BioPro-Distribution` for its own version:

```mermaid
sequenceDiagram
    participant Dev as develop -> main PR (version bumped)
    participant CI as pipeline.yml (main)
    participant Rel as GitHub Release
    participant App as BioPro app (NetworkUpdater)

    Dev->>CI: merge triggers build/test/generate-registry
    CI->>CI: generate-registry job computes changelog<br/>since last tag, writes registry.json
    CI->>Rel: release job uploads registry.json<br/>as a release asset (with the executables, SBOM, provenance)
    App->>Rel: fetch releases/latest/download/registry.json<br/>(CORE_REGISTRY_URL, no BioPro-Distribution involved)
    Rel-->>App: {version, download_url, notes, release_date}
    App->>App: UpdateChecker emits CORE_UPDATE_AVAILABLE<br/>with notes as a 3rd argument
    App->>App: UpdateBannerWidget shows the banner,<br/>sets notes as the label tooltip
```

`registry.json`'s `notes` field is built from `git log <last-tag>..HEAD --no-merges`, one bullet per commit subject — which is why PR titles following Conventional Commits matter beyond just passing `enforce-workflow`: they're literally what shows up as the "what changed" text in the app.

Plugin version lookups are unchanged and still go through `BioPro-Distribution/registry.json` — this self-published path is core-app-only, by design, since plugins are a separate versioning surface with their own release cadence.

## Versioning quick reference

See [CONTRIBUTING.md § Versioning & release mechanics](https://github.com/KalaimaranB/BioPro/blob/main/CONTRIBUTING.md#versioning--release-mechanics) for the full explanation of when a merge to `main` does and doesn't produce a build, and why hotfixes should bump PATCH rather than relying on same-tag asset overwriting.
