# Testing Status

## Available command

```sh
node --test
```

The `package.json` also defines `npm test`. No third-party test framework is required; Node.js 18 or later is recommended.

## Current evidence

The open foundation milestone's last local run completed 4 tests: 4 passed, 0 failed. Tests cover representative expression precedence, invalid and unsafe expression rejection, three linear equation outcomes, application navigation entry points, a responsive viewport declaration, local persistence hooks, and absence of `eval()` / `new Function()` in the application source.

These checks do not verify browser rendering, touch interactions, actual persistence behavior in Safari, accessibility with assistive technology, or deployment. The repository had no GitHub Actions runs when assessed. The proposed CI workflow runs tests on pull requests and pushes to `main`. Source-level tests check that the Pages workflow is main-only and has the expected limited permissions; do not report the workflow checks as passing before a GitHub Actions run completes.
