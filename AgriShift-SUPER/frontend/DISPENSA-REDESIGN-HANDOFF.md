# AgriShift — Field Collection / Dispensa-informed frontend redesign

## What the brief asked for
The request was specifically about the **`/en/dispensa`** page on Agrumea Farm, not a generic homepage with random floating photos. That page presents product categories as editorial stories with striking imagery, large typography and staggered, scroll-reactive product showcases. The AgriShift implementation reproduces the *interaction patterns and category-led narrative approach*, not Agrumea's copyrighted code, visual assets, exact design, logos, or copy.

## What changed
- Both **`index.html`** and **`dashboard.html`** now use a unified light editorial AgriShift aesthetic: navy ink, cyan, lime, field green, cream, and a giant serif title hierarchy.
- Dashboard has an immersive opening scene, a crop collection introduction, two large **winter and summer crop chapters**, four oversized photographed crop cards with staggered layout and hover motion, a fullscreen field photography chapter and then the separate **Decision Studio**.
- Crop cards perform a meaningful action: clicking the arrow selects that crop as **Previous crop** in the farm form; existing results are invalidated safely.
- The real API, result cards, comparison, ET₀ chart, saved historical preview, map, and photo explorer are kept intact.
- Mobile gets a stacked layout, large editorial typography, and no horizontal overflow.
- Fullscreen menu, scroll progress, reveal effects, cursor parallax and field-photo parallax are preserved/extended, honoring `prefers-reduced-motion`.
- User-supplied team logo is a small *team badge* in the masthead/sidebar, not a repeated massive decorative image.

## What this is NOT
- Not a cloned copy of Agrumea's HTML/CSS/3D shaders or brand assets.
- Not a scientific analysis for coordinates selected in the photo explorer (legacy MVP remains fixed Nile Delta reference).
- Not live field validation, ML, satellite crop imagery, future weather prediction or harvest promises.
- The page photographs are **representative real photographs linked from Wikimedia Commons**, not photos of the user's farm. Their licenses and credits are in `PHOTO-CREDITS.md`.
- **Images are not bundled in this ZIP** because the source files could not be downloaded in the development environment; they load from Wikimedia when online. If a photo fails, the site displays a clearly labeled fallback. For a fully offline demo, download and license-check the originals, bundle under `dist/img/`, and switch the references to local paths.

## Files and separation
- `index.html` — landing page (now same visual vocabulary)
- `dashboard.html` — editorial crop collection + functional decision studio
- `dist/css/dispensa-inspired.css` — all new design rules isolated from existing CSS
- `dist/js/dispensa-interactions.js` — chapter nav, 3D-ish lightweight parallax, previous-crop actions and image fallback
- Existing `/api/` contract unchanged. `dist/js/decision-studio.js` untouched.
- Original `dist/img/team-logo.webp` remains inside frontend; no backend files were modified.

## Local use
Copy this `frontend/` over the original project frontend folder; run the FastAPI app as before. See `README.md` and `API-CONTRACT.md`. For a static UI preview in this `frontend/` folder:

```powershell
python -m http.server 8765
```

Then visit `http://127.0.0.1:8765/` and `http://127.0.0.1:8765/dashboard.html?preview=1`. No *new* analysis works without the backend.

## Tests performed
Tested an in-memory rendering of the actual HTML/CSS/JS in headless Chromium at **1440×900 and 390×844**. No JavaScript page errors or horizontal overflow. With the authentic saved analysis response mocked into the original API contract: **4 modeled cards, 2 within-budget after filtering; crop selection invalidated old results; fullscreen menu opened and closed by Escape**. Also tested landing page menu at both sizes. Not tested: remote image loads, geolocation photo API or original Agrumea animation timing (network not accessible during browser QA).
