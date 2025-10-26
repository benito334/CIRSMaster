# Release Process

- Update `VERSION` and `CHANGELOG.md`.
- Tag release: `git tag v$(cat VERSION)` and `git push --tags`.
- GitHub Actions `release.yml` builds and pushes images to GHCR and uploads SBOMs.
- Deploy locally with `scripts/deploy_local.sh`.
