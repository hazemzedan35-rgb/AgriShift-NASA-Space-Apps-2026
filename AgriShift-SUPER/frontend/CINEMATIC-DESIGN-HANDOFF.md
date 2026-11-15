# AgriShift Cinematic Frontend — Implementation and Merge Handoff

## Starting point
Modified the uploaded `AgriShift-Frontend-Premium-Visuals-v2(1).zip`, **frontend directory only**. No backend source code was changed. This is an original AgriShift UI inspired by the motion style in the supplied Agrumea Farm walkthrough: layered floating objects, oversized typography, editorial full-bleed sections, fullscreen nav, scroll-driven motion, and horizontal product-style storytelling — without copying their code, assets, branding, or layouts directly.

## Main changes
- New immersive landing-page orbit scene: four *photographic* crop tiles with light pointer parallax and scroll depth.
- Full-height real farmland editorial story, and draggable/swipeable four-crop carousel.
- Cinematic dashboard hero with real farmland photographic background and geographic context label.
- Photo editorial strip in the dashboard, plus a persistent crop gallery of four concrete source images.
- Fullscreen keyboard-accessible nav overlay, scroll progress indicator, reveal animations and reduced-motion support.
- Smaller team badge integration (logo from user upload), not a repeated gigantic logo.
- Actual coordinate-based OpenStreetMap map frame and optional Wikimedia Commons geotagged photo search (within approx. 10km, if indexed). Explicit disclosure that visual coordinates **do not change `/api/analyze`** with the legacy backend.
- No dependence on GSAP, Three.js, Lenis, new builds, or paid APIs. All motion is native JS/CSS.

## File map
- `index.html`: cinematic homepage.
- `dashboard.html`: cinematic decision studio, existing analysis controls retained.
- `dist/css/agrishift.css`: prior frontend CSS retained for compatibility.
- `dist/css/cinema-overrides.css`: isolated new design layer and responsive overrides.
- `dist/js/decision-studio.js`: same original `/api/*` request/response contract; geotagged photo search now uses a real Wikimedia API, not random Unsplash URL templates.
- `dist/js/cinema-effects.js`: motion effects, navigation, carousel, scroll triggers.
- `dist/img/team-logo.webp`: supplied asset.
- `PHOTO-CREDITS.md`: photograph authors, licenses, and source pages.

## Run against legacy MVP backend
1. Extract the original `AgriShift-Working-MVP(1).zip`.
2. Copy this `frontend/` directory over the existing `AgriShift-MVP/frontend/` directory.
3. From `AgriShift-MVP/`, run:
   ```powershell
   python -m pip install -r requirements.txt
   python start_agrishift.py
   ```
4. Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/dashboard.html`.
5. To test API: `python frontend/verify_integration.py --base http://127.0.0.1:8000`.

For static preview only: `cd frontend && python -m http.server 8765`. This will not calculate new rotations; use the saved pilot example.

## What the frontend DOES NOT do
- Does not request live farm coordinates as analysis input from the current fixed-location MVP backend.
- Does not train ML or invent crop yield, water saving or accuracy figures.
- Does not implement NASA HLS or SMAP imagery. Images on the site are labeled photos.
- Does not use satellite imagery as a substitute for a geographic map.
- Does not guarantee that arbitrary coordinates yield Commons photos.

## Merge contract for teammate's newer backend
See `API-CONTRACT.md`. UI currently expects `GET /api/health`, `/api/climate`, `/api/monthly`, `POST /api/analyze`, and `plans[]`, `inputs`, `climate`. The decorative visual explorer is separate from those endpoints. For dynamic location analysis and 4/6 season UI support, first agree on a versioned capabilities endpoint and response fields, then intentionally add controls and adapt the renderer.

## Browser/accessibility checks
- Used an isolated headless Chromium in-memory DOM test at 1440px and 390px with the real HTML/CSS/JS, because the environment blocks direct navigation to local HTTP/file URLs.
- No JavaScript page errors in those tests.
- Menu opens/closes via keyboard; carousel next arrow scrolls.
- In-memory API mock using the **supplied actual saved pilot report**: 4 plan cards, within-budget filter shows 2, compare panel works, changing farm input invalidates the export/previous cards.
- Page width fits both viewports after responsive fixes.
- External image requests and live Wikimedia/OSM fetches were not end-to-end verified in this restricted environment. A machine with internet access must test them after extraction.
