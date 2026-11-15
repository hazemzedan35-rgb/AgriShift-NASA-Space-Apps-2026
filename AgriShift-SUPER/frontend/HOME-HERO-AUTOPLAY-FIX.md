# Homepage opening-photo motion fix

- Root cause: `index.html` did not load the photo-motion script. The previous photo movement was available only in `dispensa-interactions.js`, which runs on the dashboard (`.dispensa-edition`) but not the homepage (`.dispensa-home`).
- Added `dist/js/home-hero-motion.js` to `index.html`. The three opening images now start a gentle, independent floating animation automatically on page load, even without mouse/scroll interaction. The images respond to pointer movement and page scroll as well.
- Uses only `transform` via existing `--dp-mx` and `--dp-my` CSS variables. No new dependency or backend changes. It pauses when scrolled out of view or when the page is hidden, and honors reduced-motion preferences.
- The dashboard retains its existing interactions and photo assets; the original images, text and routing remain unchanged.
