# AgriShift integrated research build – evidence and limits

## Implemented
- One FastAPI project serves the existing cinematic frontend, NASA/FAO-56 decision engine, and the supplied Gemini chat backend under `/assistant/api/chat`.
- Farm location can be entered as latitude/longitude or selected from device GPS (permission required, secure context, not automatically the farm).
- `POST /api/analyze` fetches **real NASA POWER daily 2025 observations** for new coordinates or validated cache, and returns 2-, 4-, or 6-season scenario comparisons using the four documented crop proxies.
- `GET /api/climate` and `GET /api/monthly` accept optional `latitude` and `longitude`; without coordinates they explicitly return the bundled Nile Delta reference.
- Frontend displays the requested location and 2/4/6 seasons; monthly chart updates from `POST /api/analyze` instead of silently keeping the pilot.
- The existing 12 visual crops remain explorable; the additional eight are **not supported for quantitative rotation generation** yet.
- The standalone chatbot app is mounted in-process; the UI adapter forwards the message history and user-selected coordinates. A user-supplied Gemini API key is required for model answers.

## Scientific non-claims
- The backend uses a historical **single year (2025) analogue**, not a future weather forecast or a multi-year climate normal.
- The crop ETc Kc examples are sourced to FAO-56 but are *not locally calibrated*. No CROPWAT executable, AppEEARS extraction, or automatic ECOCROP/GAEZ import is present.
- A GPS position is an input coordinate, **not a soil test**, farm boundary, or actual field photo.
- Water `gross_planning_proxy_m3` = crop ETc / assumed efficiency × area; not a validated on-farm irrigation requirement.
- The chatbot includes an LLM and cannot be treated as a verified agronomist. It exposes only a NASA observations tool, not its legacy unsourced crop coefficient tables.
- No actual NASA API calls or Gemini calls were verified in this sandbox unless explicitly noted in the QA report.

## Secrets
- The uploaded chatbot ZIP contained a `.env` file. **That file was deliberately not copied**. Never commit or share it. Rotate any key that may have been circulated in archives or chats.
- Set `GEMINI_API_KEY` locally as an environment variable (or a local non-committed .env file in `agrishift_chatbot/`). Do not put it in JavaScript or public ZIPs.

## Official source links
NASA POWER: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
FAO-56: https://www.fao.org/4/X0490E/x0490e00.htm
FAO CROPWAT: https://www.fao.org/land-water/resources/tools/software/cropwat/en
FAO ECOCROP: https://www.fao.org/geospatial/data-and-tools/data-portals/ecocrop/en
NASA AppEEARS: https://appeears.earthdatacloud.nasa.gov/
2026 challenge: https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/
