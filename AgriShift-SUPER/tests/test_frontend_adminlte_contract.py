"""Static guards for the AdminLTE-based dashboard (no browser needed)."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'frontend'


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.classes = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'link' and a.get('rel') == 'stylesheet' and a.get('href'):
            self.refs.append(a['href'])
        if tag == 'script' and a.get('src'):
            self.refs.append(a['src'])
        self.classes.update((a.get('class') or '').split())


def parse(name):
    p = Assets()
    p.feed((WEB / name).read_text(encoding='utf-8'))
    return p


class TestAdminLteDashboard(unittest.TestCase):
    def test_uses_adminlte_layout_and_stylesheet(self):
        page = parse('dashboard.html')
        self.assertIn('dist/css/adminlte.min.css', page.refs)
        self.assertIn('dist/js/adminlte.min.js', page.refs)
        for cls in ('app-wrapper', 'app-header', 'app-sidebar', 'sidebar-menu', 'app-main', 'app-content', 'app-footer', 'info-box', 'card'):
            self.assertIn(cls, page.classes, cls)

    def test_every_asset_is_local_and_exists(self):
        refs = parse('dashboard.html').refs
        self.assertTrue(refs)
        for ref in refs:
            self.assertFalse(re.match(r'^(https?:)?//', ref), f'external asset (breaks offline use): {ref}')
            self.assertTrue((WEB / ref).is_file(), f'missing asset: {ref}')

    def test_no_font_cdn_import_in_custom_css(self):
        css = (WEB / 'dist/css/agrishift-dashboard.css').read_text(encoding='utf-8')
        self.assertNotIn('@import', css)
        self.assertNotIn('googleapis', css)

    def test_custom_css_does_not_hardcode_colours(self):
        css = (WEB / 'dist/css/agrishift-dashboard.css').read_text(encoding='utf-8')
        body = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        self.assertIsNone(re.search(r'#[0-9a-fA-F]{3,8}\b', body), 'use Bootstrap/AdminLTE variables so dark mode works')

    def test_icon_font_files_referenced_by_vendor_css_exist(self):
        css = (WEB / 'dist/vendor/bootstrap-icons/bootstrap-icons.min.css').read_text(encoding='utf-8')
        for rel in re.findall(r'url\("([^"?]+)', css):
            self.assertTrue((WEB / 'dist/vendor/bootstrap-icons' / rel).is_file(), rel)


if __name__ == '__main__':
    unittest.main()
