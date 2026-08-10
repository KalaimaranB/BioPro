# Contributing to BioPro

This is the practical, day-to-day guide: how to branch, commit, open a PR, and ship a release. For *why* the system is shaped this way — the purpose of each branch, how CI cost scales with branch, how the enforcement gate works mechanically — see [Git Branching Engine](docs/internal/23_Git_Branching_Engine.md).

## Branch naming

| Prefix | Off of | Into | Purpose |
| --- | --- | --- | --- |
| `feature/<slug>` | `develop` | `develop` | New functionality |
| `fix/<slug>` | `develop` | `develop` | Non-urgent bug fix |
| `chore/<slug>` | `develop` | `develop` | Tooling, CI, deps, cleanup |
| `docs/<slug>` | `develop` or `main` | `develop` or `main` | Documentation only |
| `hotfix/<slug>` | `main` | `main`, then back-merged to `develop` | Urgent production fix |

Branch names and PR titles are **checked automatically** by the `enforce-workflow` CI job — a branch or title that doesn't match will fail the required check and cannot merge.

## Commit & PR title convention

Use [Conventional Commits](https://www.conventionalcommits.org/) for commit subjects and, most importantly, **PR titles** (PR titles become the commit message on `main`, since merges are squash-only):

```
feat: add lane detection to western blot plugin
fix: handle empty FCS file in flow cytometry loader
chore: bump ruff to 0.8
docs: document the plugin signing flow
refactor: extract registry fetch into its own module
test: cover corrupted manifest handling
ci: add windows runner to test matrix
```

Format: `type(optional-scope)!: description` — the `!` marks a breaking change. This is enforced twice:
- **Locally**, by a `commit-msg` pre-commit hook (fast feedback, bypassable with `--no-verify`).
- **In CI**, by `enforce-workflow` checking the PR title (the real gate — not bypassable on a protected branch).

One-time setup so the local hook actually runs (pre-commit only installs the default `pre-commit` stage unless told otherwise):
```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

## PR & merge policy

- All merges are **squash merges** — one clean commit per PR on both `develop` and `main`.
- Branches are **auto-deleted on merge**.
- Required status checks must pass before merge:
  - Into `develop`: `audit-and-lint`, `enforce-workflow`. (Except `docs/*` branches, which skip `audit-and-lint` and run `docs-lint`).
  - Into `main`: `audit-and-lint`, `test` (full macOS/Windows matrix), `enforce-workflow`. (Except `docs/*` branches, which skip both and run `docs-lint`).
- Branch protection applies to administrators too — there's no silent bypass, including for the repo owner.

## Day-to-day lifecycle

1. Branch off `develop`: `git checkout develop && git pull && git checkout -b feature/my-thing`
2. Commit as you go — the `commit-msg` hook checks format at commit time.
3. Push and open a PR into `develop` with a Conventional Commits title.
4. `enforce-workflow` + `audit-and-lint` run (lint, mypy, pip-audit, ubuntu pytest — fast, cheap). If checks fail, push more commits to the same branch; the same PR re-runs automatically.
5. Squash-merge once green. Branch is deleted automatically.

## Promoting `develop` to `main` (shipping a release)

1. Open one PR from `develop` into `main` when you're ready to ship (title still Conventional Commits, e.g. `chore: promote v1.6.0`).
2. This triggers the full pipeline: `audit-and-lint`, the macOS/Windows `test` matrix, and `enforce-workflow`.
3. If it fails, push the fix straight to `develop` — the same promotion PR reruns automatically. No need to close/reopen.
4. **If this release should ship a build**, bump the `version` in `pyproject.toml` as part of this PR (see Versioning below). If it's a promotion of purely internal changes (docs, CI, refactors), you can skip the bump — the code still lands on `main`, but no build/release is produced.
5. Squash-merge. If the version was bumped, the `build`, `generate-registry`, and `release` jobs run automatically and publish a GitHub Release plus the self-published `registry.json`.

## Hotfix procedure

1. Branch off `main`: `git checkout main && git pull && git checkout -b hotfix/urgent-thing`
2. Fix, commit, bump `pyproject.toml`'s **PATCH** version (see below — this is what makes the hotfix auto-ship).
3. PR into `main` (title like `fix: ...`). `enforce-workflow` allows `hotfix/*` branches to target `main` directly.
4. After merge, **also merge/cherry-pick the fix into `develop`** so it isn't lost on the next promotion. (An automated back-merge PR will be created for you).

## Documentation updates

1. Branch off `main`: `git checkout main && git pull && git checkout -b docs/add-new-guide`
2. Write docs. PR into `main`. 
3. `enforce-workflow` allows `docs/*` branches to target `main` directly.
4. The expensive `audit-and-lint` and `test` CI jobs are bypassed to save runner time. Only `docs-lint` (markdown formatting and mermaid validation) runs.
5. After merge, an automated PR is opened to back-merge `main` into `develop` so your docs propagate everywhere.

## Versioning & release mechanics

`pyproject.toml`'s `version` field is the single source of truth (SemVer: `MAJOR.MINOR.PATCH`).

- **A merge to `main` without a version bump still lands the code and runs full CI — it just produces no build/release.** This is intentional: it lets non-shippable changes (docs, CI, internal refactors) go through the same promotion path without triggering a release.
- **A hotfix meant to actually ship a new installer should always bump PATCH** (e.g. `1.5.0 → 1.5.1`), not rely on re-running the pipeline against the same version. Here's why: `action-gh-release`'s `overwrite_files` defaults to `true`, so re-triggering a release against an *unchanged* version tag silently replaces the existing build assets under the same tag — which is what manually triggering the workflow via `workflow_dispatch` has been doing. That works, but it invalidates the meaning of the SLSA provenance attestation for that tag (it was generated for the *original* artifact, not the swapped one). Bumping PATCH gives every shipped build its own tag, its own valid provenance, and removes the need to ever manually trigger the workflow.
- The self-published `registry.json` (generated automatically by the `generate-registry` CI job whenever a build ships) is what the in-app update banner reads — see the [Git Branching Engine](docs/internal/23_Git_Branching_Engine.md) doc for the full data flow.

## Visualizing branches

- **Git Graph** VS Code extension (`mhutchie.git-graph`) — install it and use the "Git Graph" view for a live, clickable branch/merge topology right in the editor. This is the easiest way to actually *see* what's happening as you learn the flow.
- Terminal: `git log --graph --oneline --all --decorate`
- GitHub: repo → Insights → Network, for the remote-side view.

## Command cheatsheet

```bash
# Start a feature
git checkout develop && git pull && git checkout -b feature/my-thing

# Keep it current
git fetch origin && git rebase origin/develop

# See the graph
git log --graph --oneline --all --decorate

# Promote develop -> main (open via GitHub UI or gh)
gh pr create --base main --head develop --title "chore: promote vX.Y.Z"

# Hotfix
git checkout main && git pull && git checkout -b hotfix/urgent-thing
```
