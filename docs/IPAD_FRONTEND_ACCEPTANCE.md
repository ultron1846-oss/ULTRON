# iPad frontend acceptance

**Automated static contract:** verified by the frontend release tests (viewport meta, responsive breakpoints, safe-area inset, 44 px touch-target minimum, and local RAM-preference persistence).

**Manual Safari acceptance:** pending. CI cannot substitute for testing the deployed GitHub Pages site on an actual iPad.

## Automated contract coverage

The Node release suite statically checks the responsive viewport, phone, iPad-width tablet, and narrow-landscape CSS, 44 px touch-target minimum, visible keyboard focus, Escape/outside-click navigation dismissal, active navigation state, IndexedDB transaction/error contracts, backup import validation, and save-retry UI. These checks do not simulate Safari rendering or device storage.

## Manual checklist

- [ ] Open https://ultron1846-oss.github.io/ULTRON/ in Safari on iPad. Confirm the site opens without login or sign-up. GitHub Pages deployment run #146 succeeded, but this manual browser check is still required.
- [ ] Test portrait and landscape orientation; confirm no horizontal page overflow.
- [ ] Open and close the mobile sidebar; visit each primary page; confirm navigation closes correctly.
- [ ] Move the requested workload-memory slider from 2 GiB to 10 GiB; confirm the requested GiB value label and accessible value text update and persists after reload.
- [ ] Confirm the slider is a local preference only. It does not allocate physical RAM, set a device memory limit, change hosted-runner limits, or start training.
- [ ] Confirm the Training page displays generic status only and has no Start/Pause/Stop/Resume/Save checkpoint or pairing controls.
- [ ] Disconnect and reconnect the network; confirm status changes to offline/stale and then refreshes when connectivity returns. Verify the last successful timestamp and age are shown.
- [ ] Confirm Memory Vault export/import controls remain reachable and local; do not use private or sensitive practice content during acceptance.
- [ ] Confirm buttons and slider are usable by touch and text remains readable at the default iPad display zoom.

## Current limits

The RAM slider stores a requested memory preference in browser-local storage. There is no approved training runtime connected to it yet, so it does not enforce an actual process-memory budget. Training, corpus generation, optimizer steps, and remote execution remain disabled.
