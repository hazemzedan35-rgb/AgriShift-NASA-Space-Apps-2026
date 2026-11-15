# AgriShift — Flow Edition (frontend-only)

## What changed

- Two-page editorial navigation inspired by the **motion rhythm** of the supplied Agrumea Farm video, not a reproduction of the site's code, imagery, or brand.
- Full-viewport spring-green navigation overlay with oversized typography, staggered entry, and a crop/field preview.
- Marine-blue + green page transition curtain when moving between `index.html` and `dashboard.html`, including deep links to crop and analysis chapters.
- In-page links scroll smoothly after the menu closes. The navigation is keyboard-accessible and closes on Escape.
- Reduced-motion users get near-instant transitions. Native scroll and lightweight CSS transforms keep the site responsive.

## Important

- The original `index.html` / `dashboard.html`, all 12 crop visuals, user's **Sorghum** and **Sugar Beet** photos, the field hero image, form IDs, saved reference data, and API paths are preserved.
- No Three.js, WebGL, extra remote animation library or backend changes.
- This is a **frontend-only** ZIP. Run `python -m http.server 8765` inside `frontend` and visit `http://127.0.0.1:8765` to explore navigation. A running backend is necessary for *new* analysis; the saved pilot preview remains available.
- For the global menu on both pages use the **MENU** button, select a destination, and observe the branded page wipe.
- For cross-page transitions the browser sessionStorage signal is used. It stores only a 1-time navigation flag and display title; not user inputs.

## Quick test checklist

1. Open MENU → six links appear with staggered large typography.
2. Hover the entries (desktop) → the local photo preview changes.
3. Choose **Crop Atlas** → wipe into `dashboard.html#crop-atlas`.
4. From the dashboard menu choose **Home** → wipe back to `index.html`.
5. On mobile, check that the menu fits and Escape/Close works.
6. `dashboard.html?preview=1` loads the saved pilot reference when served from HTTP.

## Files added

- `dist/css/agrishift-flow.css`
- `dist/js/flow-navigation.js`
- `FLOW-EDITION.md`

## Files patched

- `index.html`, `dashboard.html`: unified menu/curtain and assets.
- `dist/js/cinema-effects.js`: old menu event handlers removed to avoid double handling. Other parallax, reveal, and progress logic preserved.
