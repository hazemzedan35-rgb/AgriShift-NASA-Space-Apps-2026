> **HISTORICAL DOCUMENT** — The original integrated build QA; this file predates the 12-crop submission extension. See `SUBMISSION-TEST-RESULTS.md` for the current verified results and scope.

# Final QA – merged AgriShift build (2026-11-15)

## Scope
Three user-supplied ZIPs: A3 decision backend, cinematic/floating-chat frontend, and separate Gemini chatbot. The merged project includes the original scientific 2025 pilot files and images without inventing crop data.

## Automated checks
- Default `python -m pytest -q` runs the integrated test suite after excluding two outdated AdminLTE-only static contract files and one outdated AdminLTE asset route assertion. These tests refer to files deliberately replaced by the new frontend; their source remains in the repository for audit. This is NOT equivalent to every original test passing.
- `tests/test_super_integration.py`: six checks for modern assets, dynamic coordinate endpoint behavior, NASA failure status, 4/6-season results, source-status honesty, and chatbot mount without bundled secrets.
- JavaScript syntax verified with `node --check`.
- Isolated Chromium UI test (not a full hosted browser test) uses **mocked API responses** to validate current page form inputs, rendering and chatbot adapter. This does NOT validate live NASA/Gemini and does NOT establish scientific correctness.
- Full-site browser navigation was blocked by the sandbox's localhost access policy; don't claim the responsive/animation experience was end-to-end tested here.

## What does NOT work without network or account setup
- Arbitrary new coordinates fetch NASA POWER 2025 historical daily data live; outside network access fails visibly with HTTP 503 rather than fabricated fallback.
- Gemini chat answers require `GEMINI_API_KEY` set privately by the team and network access. No user-supplied `.env` copied into this distribution.
- Offline historical Nile Delta pilot and static visual catalogue are available without outside API access.
- AppEEARS, EcoCrop automated API and CROPWAT executable were not integrated; documentation links are provided as research references only.

## Limits
- Only 4 crops quantified; 12 in visual library.
- No future weather forecasts, no site-calibrated agronomic planting calendars, no field-validated water savings, no measured soil moisture or yield.
- Latitude limited to ±66.5° by the current FAO-56 method implementation; "any point on Earth" would be false.
- Product not production-ready: add permanent secrets management, independent dataset validation, service-side rate limits for all endpoints, runtime monitoring, more automated browsers, user data policy, official legal review and local agronomic validation.
- A generated crop image is illustrative, not an observation or photo of the selected farm.
