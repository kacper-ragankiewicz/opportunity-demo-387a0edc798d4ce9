import tempfile
import unittest
from pathlib import Path

from migration_audit import audit_rows, read_csv, write_csv


class MigrationAuditTests(unittest.TestCase):
    def test_valid_catalog_is_prepared_for_import(self):
        rows = [
            {
                "sku": "MUG-001",
                "name": "Ceramic Mug",
                "price": "29.90",
                "stock": "42",
                "status": "publish",
                "categories": "Home > Mugs",
                "images": "https://img.example.com/mug.jpg",
                "slug": "",
                "parent_sku": "",
                "attributes": "",
            },
            {
                "sku": "TSHIRT-001",
                "name": "Classic T-Shirt",
                "price": "",
                "stock": "",
                "status": "publish",
                "categories": "Men> T-Shirts",
                "images": "https://img.example.com/shirt-parent.jpg",
                "slug": "",
                "parent_sku": "",
                "attributes": "",
            },
            {
                "sku": "TSHIRT-001-BLK-M",
                "name": "Classic T-Shirt Black M",
                "price": "79",
                "stock": "8",
                "status": "publish",
                "categories": "Men > T-Shirts",
                "images": "https://img.example.com/shirt-black-m.jpg",
                "slug": "",
                "parent_sku": "TSHIRT-001",
                "attributes": "Color=Black|Size=M",
            },
        ]
        report = audit_rows(rows)

        self.assertEqual(report["errors"], [])
        self.assertEqual(report["types"], {"simple": 1, "variable": 1, "variation": 1})
        self.assertEqual(report["prepared_rows"][0]["slug"], "ceramic-mug")
        self.assertEqual(report["prepared_rows"][1]["categories"], "Men > T-Shirts")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "prepared.csv"
            write_csv(out, report["prepared_rows"])
            reloaded = read_csv(out)
            self.assertEqual(len(reloaded), 3)
            self.assertEqual(reloaded[2]["type"], "variation")

    def test_invalid_rows_are_reported(self):
        rows = [
            {
                "sku": "DUP-001",
                "name": "First",
                "price": "10",
                "stock": "1",
                "status": "publish",
                "categories": "A > B",
                "images": "https://img.example.com/a.jpg",
                "slug": "",
                "parent_sku": "",
                "attributes": "",
            },
            {
                "sku": "DUP-001",
                "name": "Duplicate",
                "price": "12",
                "stock": "2",
                "status": "publish",
                "categories": "A > B",
                "images": "https://img.example.com/b.jpg",
                "slug": "",
                "parent_sku": "",
                "attributes": "",
            },
            {
                "sku": "VAR-001",
                "name": "Broken Variation",
                "price": "-5",
                "stock": "x",
                "status": "live",
                "categories": "A > B",
                "images": "file://bad",
                "slug": "",
                "parent_sku": "MISSING-PARENT",
                "attributes": "",
            },
        ]
        report = audit_rows(rows)
        messages = {e["error"] for e in report["errors"]}

        self.assertIn("duplicate sku", messages)
        self.assertIn("missing parent sku", messages)
        self.assertIn("variation missing attributes", messages)
        self.assertIn("invalid status", messages)
        self.assertIn("price must be >= 0", messages)
        self.assertIn("invalid stock", messages)
        self.assertTrue(any(m.startswith("invalid image url:") for m in messages))
        self.assertEqual(report["valid_rows"], 1)
        self.assertEqual(report["invalid_rows"], 2)


if __name__ == "__main__":
    unittest.main()
