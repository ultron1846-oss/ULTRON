# iPad frontend acceptance

**Automated static contract:** verified by the frontend release tests (viewport meta, responsive breakpoint, safe-area inset, 44 px touch-target minimum, and local RAM-preference persistence).

**Manual Safari acceptance:** pending. CI cannot substitute for testing the deployed GitHub Pages site on an actual iPad.

## Manual checklist

- [ ] Open https://ultron1846-oss.github.io/ULTRON/ in Safari on iPad. Confirm the site opens without login or sign-up. GitHub Pages deployment run #146 succeeded, but this manual browser check is still required.
- [ ] Test portrait and landscape orientation; confirm no horizontal page overflow.
- [ ] Open and close the mobile sidebar; visit each primary page; confirm navigation closes correctly.
- [ ] Move the preferred training-memory slider from 2 GB to 10 GB; confirm the value label updates and persists after reload.
- [ ] Confirm the slider is a local preference only. It does not allocate physical RAM, change hosted-runner limits, or start training.
- [ ] Confirm the Training page displays generic status only and has no Start/Pause/Stop/Resume/Save checkpoint or pairing controls.
- [ ] Confirm Memory Vault export/import controls remain reachable and local; do not use private or sensitive practice content during acceptance.
- [ ] Confirm buttons and slider are usable by touch and text remains readable at the default iPad display zoom.

## Current limits

The RAM slider stores a requested memory preference in browser-local storage. There is no approved training runtime connected to it yet, so it does not enforce an actual process-memory budget. Training, corpus generation, optimizer steps, and remote execution remain disabled.
