# Contributing to BioPro

This is the practical, day-to-day guide for BioPro engineers: how to branch, commit, open a Pull Request (PR), and ship a release. BioPro uses a dual-branch topology (`develop` as staging, `main` as production) driven by automated CI/CD pipelines.

For an architectural explanation of *why* the system is shaped this way, see the [Git Branching Engine](docs/internal/23_Git_Branching_Engine.md).

---

## 1. Branch Naming & Policy

Your branch name explicitly dictates what you are allowed to merge into. The `enforce-workflow` CI job automatically physically blocks any PR that does not follow this matrix.

| Prefix | Source Branch | Target Branch | Purpose |
| --- | --- | --- | --- |
| `feature/<slug>` | `develop` | `develop` | New functionality |
| `fix/<slug>` | `develop` | `develop` | Non-urgent bug fix |
| `chore/<slug>` | `develop` | `develop` | Tooling, CI, dependencies, cleanup |
| `docs/<slug>` | `main` | `main` | Documentation only |
| `hotfix/<slug>` | `main` | `main` | Urgent production fixes |

---

## 2. Standard Development (`develop`)

All standard work (`feature/*`, `fix/*`, `chore/*`) MUST target `develop`. 

### The Lifecycle
1. **Branch Off `develop`**
   ```bash
   git checkout develop && git pull
   git checkout -b feature/my-awesome-feature
   ```
2. **Commit**
   We enforce [Conventional Commits](https://www.conventionalcommits.org/). Your commit messages and PR title must start with `feat:`, `fix:`, `chore:`, etc.
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

## 4. Hotfixes & Docs (The Fast-Track)

Urgent fixes (`hotfix/*`) and documentation updates (`docs/*`) bypass `develop` and go straight to production (`main`).

### The Lifecycle
1. **Branch Off `main`**
   ```bash
   git checkout main && git pull
   git checkout -b docs/update-readme
   ```
   *Note: If doing a `hotfix/`, remember to bump the PATCH version in `pyproject.toml` so a new build is deployed!*
2. **Push and PR**
   ```bash
   git push -u origin docs/update-readme
   gh pr create --base main --head docs/update-readme --title "docs: update readme instructions"
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

---

## 5. Visualizing the Graph

To understand this topology, you need to be able to see it. 
Instead of relying on third-party IDE extensions, we have configured two built-in Git aliases for you.

Run these anywhere in your terminal:
- `git tree` - Shows the topological graph of your current branch.
- `git tree-all` - Shows the topological graph of every branch in the repository (ideal for seeing how `develop` and `main` interact).

### Reading the Graph
- **Squash Merge**: You will see a straight line with a single dot. This is used for bringing features into `develop`, or hotfixes into `main`, keeping the history clean.
- **Standard Merge**: You will see a line loop out and reconnect. This is used for Promotions (`develop` -> `main`) and Back-merges (`main` -> `develop`) to prove to Git that the environments share identical history.

---

## 6. GitHub UI & Code Reviews

When dealing with PRs, you will encounter automated bots and features. Here is how to handle them:

### CodeRabbit AI
CodeRabbit AI is our automated code reviewer. By default, it automatically ignores any PR whose title starts with `docs:`, `chore:`, or `ci:`.
It does this to save compute resources, as these branches do not contain core logic changes. 
If CodeRabbit says "Review skipped" but all other required CI checks (like tests and linters) have passed, **you are clear to merge**.

### Auto-Merge
Some of our GitHub Action robots (like the back-merge robot) are configured to automatically merge their own PRs once CI passes.
If an automated PR ever gets stuck or has a merge conflict, it will pause. If you need to manually intervene and stop the robot from merging, you can disable the auto-merge setting directly from the GitHub UI, or by running this command locally:
```bash
gh pr merge <PR_NUMBER> --disable-auto
```
