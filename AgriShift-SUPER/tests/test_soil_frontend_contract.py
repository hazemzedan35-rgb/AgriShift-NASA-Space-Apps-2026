"""Static contract checks when a full browser is unavailable in CI."""
import unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
class Elements(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.names=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.add(a['id'])
        if 'name' in a:self.names.add(a['name'])
class TestSoilFrontEndContract(unittest.TestCase):
    def test_expected_html_fields_and_results(self):
        obj=Elements();obj.feed((ROOT/'frontend/dashboard.html').read_text(encoding='utf-8'))
        self.assertTrue({'soil_type','soil_awc_mm_per_m','soil_ece_ds_m'}.issubset(obj.names))
        self.assertTrue({'soilInsight','soilStatus','farmForm','scenarioList'}.issubset(obj.ids))
    def test_js_handlers_and_no_obsolete_text(self):
        js=(ROOT/'frontend/dist/js/decision-studio.js').read_text(encoding='utf-8')
        html=(ROOT/'frontend/dashboard.html').read_text(encoding='utf-8')
        self.assertIn('function renderSoil(',js)
        self.assertIn('renderSoil(data);',js)
        self.assertNotIn('Recorded for context only; not yet used in scoring',html)
if __name__=='__main__':unittest.main()
