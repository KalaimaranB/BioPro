# Contributing to Karcytics

This is the practical, day-to-day guide for Karcytics engineers: how to branch, commit, open a Pull Request (PR), and ship a release. Karcytics uses a dual-branch topology (`develop` as staging, `main` as production) driven by automated CI/CD pipelines.

For an architectural explanation of *why* the system is shaped this way, see the [Git Branching Engine](docs/internal/23_Git_Branching_Engine.md).

---

## 1. Branch Naming & Policy

Your branch name explicitly dictates what you are allowed to merge into. The `enforce-workflow` CI job automatically physically blocks any PR that does not follow this matrix.

| Prefix | Source Branch | Target Branch | Purpose |
| --- | --- | --- | --- |
| `feature/<slug>` | `develop` | `develop` | New functionality |
| `fix/<slug>` | `develop` | `develop` | Non-urgent bug fix |
| `chore/<slug>` | `develop` | `develop` | Tooling, CI, dependencies, cleanup |
| `docs/<slug>` | `develop` | `develop` | Documentation only |
| `hotfix/<slug>` | `main` | `main` | Urgent production fixes |

---

## 2. Standard Development (`develop`)

All standard work (`feature/*`, `fix/*`, `chore/*`, `docs/*`) MUST target `develop`.

### The Lifecycle
1. **Branch Off `develop`**
   ```bash
   git checkout develop && git pull
   git checkout -b feature/my-awesome-feature
   ```
2. **Commit**
   We enforce [Conventional Commits](https://www.conventionalcommits.org/). Your commit messages and PR title must start with `feat:`, `fix:`, `chore:`, `docs:`, etc.
   ```bash
   git commit -m "feat: added new UI dashboard"
   ```
3. **Push and PR**
   ```bash
   git push -u origin feature/my-awesome-feature
   gh pr create --base develop --head feature/my-awesome-feature --title "feat: added new UI dashboard"
   ```
4. **Merge (Squash Only)**
   Once CI passes, click the green **Squash and Merge** button on GitHub. This compresses all your messy granular commits into a single, clean dot on the `develop` history.

---

## 3. Promotions to Production (`develop` -> `main`)

When `develop` is stable and ready to ship to users, we promote it to `main`.

### The Lifecycle
1. **Prepare the Release**
   If this release should produce a new executable, bump the `version` field in `pyproject.toml` (e.g., `1.5.2` -> `1.6.0`). Commit this to `develop`.
2. **Open the Promotion PR**
   Open a PR pushing `develop` directly into `main`.
   ```bash
   gh pr create --base main --head develop --title "chore: promote v1.6.0"
   ```
3. **Merge (Standard Merge Only)**
   > [!WARNING]
   > You MUST merge promotions using a **Create a Merge Commit** (Standard Merge). Do NOT click "Squash and Merge"!
   >
   > To do this, click the dropdown arrow next to the green merge button on GitHub and select **Create a merge commit**.

   Using a standard merge preserves the common history between `main` and `develop`. If you squash it, Git will forget the two branches are related and you will encounter massive textual merge conflicts on your next promotion.

---

## 4. Versioning & Release Mechanics

`pyproject.toml`'s `version` field is the single source of truth (SemVer: `MAJOR.MINOR.PATCH`).

- **A merge to `main` without a version bump still lands the code and runs full CI — it just produces no build/release.** This is intentional: it lets non-shippable changes (docs, CI, internal refactors) go through the same promotion path without triggering a release.
- **How a build gets triggered**: on every push to `main`, CI checks whether a GitHub Release for `v<version>` already exists (`gh release view`). If it doesn't, the full build/test/release pipeline runs. If it does, nothing happens — that version has already shipped.
- **This means a failed promotion can just be retried, at the same version.** If a promotion at `v1.6.0` merges but `build` or `test` fails, no release for `v1.6.0` is ever published. Push your fix to `main` (still `v1.6.0`, no bump needed) and CI automatically retries on the next push — you do NOT need to bump to `v1.6.1` just to unstick the pipeline. Only bump the version again if you're intentionally shipping *different* content under a new version.
- **Once a version has actually shipped, don't reuse its tag.** Manually re-triggering an already-published release (e.g. via `workflow_dispatch`) would overwrite its build assets in place — `action-gh-release`'s `overwrite_files` defaults to `true` — which breaks the meaning of the SLSA provenance attestation for that tag (it was generated for the *original* artifact). Bump PATCH for a genuinely new hotfix instead.

---

## 5. Hotfixes (The Fast-Track)

Urgent fixes (`hotfix/*`) bypass `develop` and go straight to production (`main`).

### The Lifecycle
1. **Branch Off `main`**
   ```bash
   git checkout main && git pull
   git checkout -b hotfix/fix-crash-on-launch
   ```
   *Remember to bump the PATCH version in `pyproject.toml` so a new build actually ships — see [Versioning & Release Mechanics](#4-versioning--release-mechanics) above.*
2. **Push and PR**
   ```bash
   git push -u origin hotfix/fix-crash-on-launch
   gh pr create --base main --head hotfix/fix-crash-on-launch --title "fix: crash on launch when no recent projects"
   ```
3. **Merge (Squash Only)**
   Once CI passes, click the green **Squash and Merge** button on GitHub to merge this PR into `main`.

### The Automated Back-Merge
Because you just pushed new code directly to production (`main`), staging (`develop`) is now out of date! Do not panic.
As soon as your PR hits `main`, a GitHub Action robot (`back-merge.yml`) wakes up.
1. The robot pulls your squashed commit off `main`.
2. It creates a branch named `chore/back-merge-main-<SHA>`.
3. It opens a PR against `develop`.
4. It automatically uses a **Standard Merge** to merge the PR, drawing a beautiful loop connecting `main` back into `develop`.

This isn't hotfix-only — the same back-merge fires after *any* push to `main`, including a regular promotion, since a promotion's merge commit exists on `main` but not (by SHA) on `develop`.

---

## 6. Visualizing the Graph

To understand this topology, you need to be able to see it.
Instead of relying on third-party IDE extensions, we have configured two built-in Git aliases for you.

Run these anywhere in your terminal:
- `git tree` - Shows the topological graph of your current branch.
- `git tree-all` - Shows the topological graph of every branch in the repository (ideal for seeing how `develop` and `main` interact).

### Reading the Graph
- **Squash Merge**: You will see a straight line with a single dot. This is used for bringing features into `develop`, or hotfixes into `main`, keeping the history clean.
- **Standard Merge**: You will see a line loop out and reconnect. This is used for Promotions (`develop` -> `main`) and Back-merges (`main` -> `develop`) to prove to Git that the environments share identical history.

---

## 7. GitHub UI & Code Reviews

When dealing with PRs, you will encounter automated bots and features. Here is how to handle them:

### CodeRabbit AI
CodeRabbit AI is our automated code reviewer, scoped to only run on PRs **targeting `main`** (via `auto_review.base_branches` in `.coderabbit.yaml`) — promotions and hotfixes get reviewed; day-to-day `feature/*`/`fix/*`/`chore/*`/`docs/*` PRs into `develop` do not.
This keeps review usage concentrated on the PRs that actually reach production. If CodeRabbit doesn't comment on a `develop`-targeted PR, that's expected — it's out of scope for that base branch, not a failure.

### Auto-Merge
Some of our GitHub Action robots (like the back-merge robot) are configured to automatically merge their own PRs once CI passes.
If an automated PR ever gets stuck or has a merge conflict, it will pause. If you need to manually intervene and stop the robot from merging, you can disable the auto-merge setting directly from the GitHub UI, or by running this command locally:
```bash
gh pr merge <PR_NUMBER> --disable-auto
```

---

## 8. Documentation Contributions

We welcome documentation updates. Follow these lightweight rules to keep the docs professional and consistent.

### Docstring & Style
- Use Google-style docstrings for public modules, classes, and functions.
- Keep docstrings concise: module summary (one line), extended description (optional), Args, Returns, Raises, Examples.
- Prefer type hints in signatures and short descriptions in docstrings — `mkdocstrings` will render types automatically.

Example:
```py
def compute(signal: np.ndarray, threshold: float) -> dict:
    """Compute metrics on `signal` above `threshold`.

    Args:
       signal: Input array of samples.
       threshold: Value to threshold the signal.

    Returns:
       A mapping of metric name to value.
    """
    ...
```

### Local Preview
- Build the docs locally before opening a PR:

```bash
python -m pip install -r reqs.txt  # or use the repo venv
python -m pip install -e .[dev]
mkdocs build
mkdocs serve  # optional for live preview
```

### PR Checklist for Docs Changes
- Title starts with `docs:` for documentation-only PRs, targeting `develop` like any other change (see §1).
- Run `mkdocs build` locally and ensure no warnings.
- Add or update API docstrings for any public API changes.
- Run `markdownlint` (CI will run this automatically).
- Add examples or tutorials in `docs/user/` for user-facing features.

If your change touches both code and docs, create a single PR describing both the code change and the documentation updates.
