"""Chromium integration smoke test for the AdminLTE dashboard.

The browser loads the REAL frontend files (dashboard.html, AdminLTE CSS/JS, vendor
libraries, decision-studio.js) from a virtual host, while /api/analyze answers come
from the real FastAPI app through TestClient. No NASA live request is made and no
local HTTP port is opened. Run with `python tools/offline_ui_smoke.py`.
Requires: playwright + a Chromium browser (python -m playwright install chromium).
"""
from pathlib import Path
import mimetypes
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from agrishift_decision.api import app

WEB = ROOT / 'frontend'
HOST = 'http://agrishift.test'
client = TestClient(app)
ALL = ('wheat', 'faba', 'maize', 'sunflower')


def api_result(seasons=4, allowed=None, strict=False, budget=30000):
    response = client.post('/api/analyze', json={
        'planning_seasons': seasons, 'allowed_crops': allowed or list(ALL),
        'strict_family_rotation': strict, 'max_results': 12, 'water_budget_m3': budget,
        'latitude': 30.5, 'longitude': 31.5})
    assert response.status_code == 200, response.text
    return response.json()


fixtures = {'four': api_result(), 'six': api_result(6), 'reduced': api_result(4, ['wheat', 'maize', 'sunflower']),
            'strict': api_result(4, strict=True), 'two': api_result(2)}


def pick_fixture(x):
    """Return (status, body) the real backend would give for this request."""
    import json
    if x['latitude'] != 30.5 or x['longitude'] != 31.5:
        return 503, {'detail': 'Offline NASA unavailable (test simulation)'}
    crops = x['allowed_crops']
    if not any(c in ('wheat', 'faba') for c in crops) or not any(c in ('maize', 'sunflower') for c in crops):
        return 422, {'detail': 'Please select at least one winter crop AND one summer crop'}
    if x['planning_seasons'] == 6: return 200, fixtures['six']
    if x['planning_seasons'] == 2: return 200, fixtures['two']
    if x['strict_family_rotation']: return 200, fixtures['strict']
    if 'faba' not in crops: return 200, fixtures['reduced']
    return 200, fixtures['four']


def handler(route, request):
    import json
    path = request.url.split('agrishift.test', 1)[1].split('?')[0]
    if path == '/api/analyze':
        status, body = pick_fixture(json.loads(request.post_data))
        route.fulfill(status=status, content_type='application/json', body=json.dumps(body))
        return
    rel = 'dashboard.html' if path in ('/', '/dashboard.html') else path.lstrip('/')
    target = (WEB / rel).resolve()
    if WEB.resolve() not in target.parents or not target.is_file():
        route.fulfill(status=404, body='not found')
        return
    route.fulfill(status=200, body=target.read_bytes(), content_type=mimetypes.guess_type(target.name)[0] or 'application/octet-stream')


with sync_playwright() as playwright:
    executable = shutil.which('chromium') or shutil.which('google-chrome')
    opts = {'headless': True, 'args': ['--no-sandbox']}
    if executable: opts['executable_path'] = executable
    browser = playwright.chromium.launch(**opts)
    try:
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        context.route(HOST + '/**', handler)
        page = context.new_page()
        errors, failed = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('requestfailed', lambda r: failed.append(r.url))
        page.goto(HOST + '/dashboard.html', wait_until='load')
        page.wait_for_function("document.querySelectorAll('.scenario').length === 12", timeout=15000)
        assert '16 generated' in page.locator('#scenarioCount').inner_text()
        assert '4 seasons' in page.locator('#scenarioCount').inner_text()
        assert not page.locator('#downloadReport').is_disabled()
        assert page.locator('.app-wrapper .app-sidebar .sidebar-menu').count() == 1, 'AdminLTE layout missing'
        assert page.locator('.info-box').count() == 4
        assert not failed, 'Every asset must be local (no CDN): ' + str(failed)
        print('PASS initial: AdminLTE layout, 16 generated, 12 rendered, no external requests')
        page.screenshot(path=str(ROOT / 'outputs' / 'AgriShift-Dashboard-AdminLTE.png'), full_page=True)

        page.locator('[name="planning_seasons"]').select_option('6')
        assert page.locator('.scenario').count() == 0
        page.locator('#analyzeBtn').click()
        page.wait_for_function("document.querySelector('#scenarioCount').textContent.includes('64 generated')")
        assert page.locator('.scenario').count() == 12
        page.locator('.scenario details').first.locator('summary').click()
        assert page.locator('.scenario').first.locator('li').count() >= 7
        print('PASS: 6-season selection renders 64 generated candidates and six crop windows')

        page.locator('[name="planning_seasons"]').select_option('4')
        page.locator('[name="allowed_crops"][value="faba"]').uncheck()
        page.locator('#analyzeBtn').click()
        page.wait_for_function("document.querySelector('#scenarioCount').textContent.includes('4 generated')")
        assert page.locator('.scenario').count() == 4
        print('PASS: user crop pool changes generated combinations')

        page.locator('[name="allowed_crops"][value="faba"]').check()
        page.locator('[name="strict_family_rotation"]').check()
        page.locator('#analyzeBtn').click()
        page.wait_for_function("document.querySelector('#scenarioCount').textContent.includes('5 pass rotation rules')")
        assert page.locator('.scenario').count() == 5
        print('PASS: strict family rule prunes 16 to 5 candidates')

        page.locator('[name="allowed_crops"][value="wheat"]').uncheck()
        page.locator('[name="allowed_crops"][value="faba"]').uncheck()
        page.locator('#analyzeBtn').click()
        page.wait_for_function("document.querySelector('#feedback').textContent.includes('Could not calculate')")
        assert page.locator('.scenario').count() == 0
        assert page.locator('#downloadReport').is_disabled()
        print('PASS: invalid crop pool clears previous plans and export')

        page.locator('[name="allowed_crops"][value="wheat"]').check()
        page.locator('[name="latitude"]').fill('31.1')
        page.locator('#analyzeBtn').click()
        page.wait_for_function("document.querySelector('#feedback').textContent.includes('Could not calculate')")
        assert page.locator('.scenario').count() == 0
        assert page.locator('#temperature').inner_text() == '—'
        print('PASS: unavailable NASA source clears old location data')

        # Mobile: no horizontal scrolling, sidebar collapsed behind the toggle.
        page.set_viewport_size({'width': 390, 'height': 844})
        overflow = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        assert overflow <= 0, f'horizontal overflow {overflow}px on mobile'
        print('PASS: 390px viewport has no horizontal overflow')
        assert not errors, errors
        print('PASS: no JavaScript errors')
    finally:
        browser.close()
