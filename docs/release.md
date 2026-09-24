# 📦 Release Process

This document describes the steps to release a new version of `rawfile-localpv`.

---

## 🛠 Prerequisites

- Git installed and configured
- Access to the GitHub repository
- Familiarity with semantic versioning (e.g., `v1.2.3`)
- All tests must pass and documentation should be up to date

---

## Development Process

All development process should be done targetting the `develop` branch. \
Pull requests must be reviewed by at least 1 codeowner and all CI tests must pass. You can find out more information on the
testing side in the [contributor docs](./contributor.md).

## Version Numbering

We follow [semantic versioning](https://semver.org/) rules when releasing, ensuring consumes of the chart have reasonably defined expectations of breaking changes.

This means we have a three-digit version number:

- New patch versions (e.g. from `4.3.2` to `4.3.3`) indicate bug fixes only. No new functionality
- New minor versions (e.g. from `4.3.3` to `4.4.0`) indicate added functionality
- New major versions (e.g. from `4.4.0` to `5.0.0`) indicate major revisions. All bets are off in terms of compatibility, you may find breaking changes

> [!WARNING]
We've yet to release the first stable release (we're `0.x.y`), which means minor releases fall in the purview of breaking changes
This doesn't mean the product itself is not stable, but the API may change in a breaking way

Please not that the helm chart version is devoid of a `v` prefix, though we still tag with the `v`, example: `v4.3.2`

## 🚀 Steps to Release

Only a codeowner may create a new release. The release should be prepared in the `develop` branch. \
Please read the following steps carefully:

- [ ] Review and merge all pending PRs which are targetted for the release
- [ ] Freeze `develop` branches from any changes
- [ ] Ensure the pyproject.yoml `version` is set to the release version
- [ ] Ensure the Chart.yaml `version` and `appVersion` are set to the release version (the pre-commit hook will do this for you)
- [ ] Update `$minVersion` in `deploy/helm/rawfile-localpv/templates/upgrade-check.yaml` if required
- [ ] Fixup the helm chart docs (the pre-commit hook will do this for you)
- [ ] Update `CHANGELOG.md` with the new version and changes
- [ ] Raise PR to merge the changes above
- [ ] Create a git tag with the format `v${Chart.yaml/version}` and push it!
- [ ] If all goes well the chart and container images should be tested, pushed and a new github release will be created!
- [ ] Update the github release description as required
- [ ] Feel free to update `CHANGELOG.md` post-release if you spot anything missing!
