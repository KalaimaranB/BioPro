# Documentation Handover & Maintenance

This page describes how to publish, maintain, and update the Karcytics documentation portal.

## Publish (GitHub Pages)

1. Ensure all docs changes are merged to `main`.
2. CI (`.github/workflows/deploy_docs.yml`) will build using `mkdocs build` and deploy to GitHub Pages automatically on push to `main`.

## Local verification

- Build locally:

```bash
python -m pip install -r reqs.txt
python -m pip install -e .[dev]
mkdocs build
mkdocs serve  # for local preview
```

- Run QA checks:
  - `codespell docs`
  - `markdownlint` is executed in PR jobs

## Maintenance tasks

- Keep `karcytics` docstrings up to date; `mkdocstrings` generates API pages from code.
- Periodically run the docs QA job locally or rely on the GitHub Action.
- Update `mkdocs.yml` nav when adding new internal pages.

## Owners & Contacts

- Docs owner: @maintainer (replace with GitHub user)
- SDK owner: @sdk-maintainer
- CI owner: @ci-ops

## Rollback

If the published site contains incorrect content, revert the PR that introduced the change and merge to `main`. The `deploy_docs` workflow will re-deploy the previous site.
