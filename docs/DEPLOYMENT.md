# GitHub Pages Deployment

## Target

Expected URL: `https://ultron1846-oss.github.io/ULTRON/`.

## Workflow behavior

The proposed `.github/workflows/pages.yml` stages only root HTML, CSS, and JavaScript files. It has no package installation or build command. It publishes only on pushes to `main` or a manual dispatch from `main`; pull requests do not publish. The artifact root contains `index.html`.

## One-time repository setup

After the workflow is merged, open **Repository Settings → Pages** and select **GitHub Actions** as the build and deployment source. This setting has not been changed by the proposal. A workflow file alone does not prove that Pages is enabled.

## Verification and recovery

After a deployment run succeeds, open the public URL and verify the dashboard, styles, module imports, and navigation. Also test on iPad Safari and a mobile viewport. If the site fails, inspect the latest Pages workflow run and confirm the artifact contains `index.html`, `styles.css`, `app.js`, and `math-engine.js` at its root. Do not report deployment complete before public verification.
