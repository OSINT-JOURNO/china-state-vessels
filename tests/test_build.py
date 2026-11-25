"""Offline tests: the build's rules, and that the published CSV keeps them. Run: python3 -m unittest discover -s tests"""
import csv, importlib.util, os, re, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build", os.path.join(ROOT, "tools", "build.py")); build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
BASE = {"category": "research", "name_en": "Test", "sources": "https://example.org", "last_checked": "2026-11-25"}

class Rules(unittest.TestCase):
    def test_imo_check_digit(self):
        self.assertTrue(build.imo_ok("9779680")); self.assertFalse(build.imo_ok("9779681")); self.assertFalse(build.imo_ok("12345"))
    def test_militia_needs_attribution(self):
        p = build.problems({**BASE, "category": "militia"})
        self.assertTrue(any("label_source" in x for x in p)); self.assertTrue(any("label_tier" in x for x in p))
        self.assertEqual(build.problems({**BASE, "category": "militia", "label_source": "CSIS AMTI, 2024", "label_tier": "assessed (cited)"}), [])
    def test_bad_values(self):
        self.assertTrue(build.problems({**BASE, "mmsi": "41325569"})); self.assertTrue(build.problems({**BASE, "sources": "none"}))
        self.assertTrue(build.problems({**BASE, "identifier_sources": "https://www.marinetraffic.com/x"}))

class PublishedData(unittest.TestCase):
    def test_csv_keeps_the_rules(self):
        rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "vessels.csv"), encoding="utf-8")))
        self.assertGreater(len(rows), 0)
        for r in rows:
            self.assertEqual(build.problems(r), [], r["id"])
            self.assertRegex(r["id"], r"^CNV-[RNCM]\d{3}$")
        ids = [r["id"] for r in rows]; self.assertEqual(len(ids), len(set(ids)))
        for r in rows:
            if r["category"] == "militia": self.assertNotRegex(r["notable_activity"], r"^(It|This boat) is (a )?militia")

if __name__ == "__main__": unittest.main()
