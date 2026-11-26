# GitHub Pages Deployment

## Target

Expected public URL: https://ultron1846-oss.github.io/ULTRON/

## Current deployment status — 2026-11-26

GitHub Pages build-and-deployment run #146 completed successfully for main commit `394ecd1da246c642de2ac3cc3515265358d5da4e`.

- Build job: success
- Build-status report job: success
- Deploy job: success

Run details: https://github.com/ultron1846-oss/ULTRON/actions/runs/45774110692

The repository's current Pages deployment is driven by GitHub's Pages build/deployment workflow. The older description of a proposed `.github/workflows/pages.yml` is obsolete; that file is not present on main.

## Public-site and device acceptance

A successful Actions deployment confirms that GitHub completed its deployment job. It does not by itself confirm that the public URL loads correctly in every browser or that all interactive behavior works.

Manual acceptance remains pending:
1. Open the public URL in Safari on an iPad.
2. Confirm no login or sign-up is required.
3. Check portrait and landscape layouts, navigation, module loading, and the local memory-preference slider.
4. Follow the complete checklist in [IPAD_FRONTEND_ACCEPTANCE.md](IPAD_FRONTEND_ACCEPTANCE.md).

## RAM slider limitation

The 2–10 GB slider is stored as a browser-local preference. It does not allocate physical RAM, enforce a process memory cap, or configure hosted runner resources. No training runtime is connected to it yet.

## Safety status

Training, dataset import, corpus generation, optimizer steps, and remote execution remain disabled. Do not report training or dataset upload as completed.
