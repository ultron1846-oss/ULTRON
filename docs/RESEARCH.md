# Research Notes

**Last reviewed:** 2026-11-23. Research here is limited to the immediate static deployment decision. It does not establish a neural architecture or validate a model design.

## GitHub Pages delivery

**Question:** How should a dependency-free static site be deployed reliably from this repository?

**Sources consulted:**

- GitHub Docs, [Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), accessed 2026-11-23.
- GitHub Docs, [Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site), accessed 2026-11-23.
- GitHub Docs, [Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), accessed 2026-11-23.

**Established facts from the official documentation:** A custom workflow can upload a Pages artifact and deploy it; the deploy job needs `pages: write` and `id-token: write`; GitHub Pages expects the entry page at the artifact root; repository settings must select GitHub Actions as the source. The documentation demonstrates the official `configure-pages`, `upload-pages-artifact`, and `deploy-pages` actions.

**Decision:** Use one static deployment workflow that stages only the site files, has no site build step, and deploys on pushes to `main`. Keep PR workflows separate from deployment so unmerged changes do not publish. Project asset references remain relative (`styles.css`, `app.js`) so they work beneath the repository project path.

**Limitations:** The workflow has not run in this repository, Pages settings have not been changed, and the public URL has not been verified. This research does not verify iPad Safari behavior.

## Subspace

The inspected repository snapshot and foundation PR contain no Subspace identifier or implementation. No research into an external product is justified until the user or repository supplies a specific meaning or reference.

## Unresearched decisions

No neural architecture, tokenizer, optimizer, dataset split, checkpoint format, or free compute provider is selected. Research those questions in the milestone where a concrete design is proposed. Do not infer that published research results apply to ULTRON.
