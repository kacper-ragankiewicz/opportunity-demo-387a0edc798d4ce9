import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ALLOWED_STATUS = {"publish", "draft"}
OUTPUT_FIELDS = [
    "type",
    "sku",
    "parent_sku",
    "name",
    "slug",
    "regular_price",
    "stock_quantity",
    "status",
    "categories",
    "images",
    "attributes",
]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text or "item"


def split_pipe(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split("|") if part.strip()]


def normalize_categories(value: str) -> str:
    paths = []
    for path in split_pipe(value):
        parts = [part.strip() for part in path.split(">")]
        parts = [part for part in parts if part]
        if parts:
            paths.append(" > ".join(parts))
    return " | ".join(paths)


def parse_price(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    value = float(raw)
    if value < 0:
        raise ValueError("price must be >= 0")
    return f"{value:.2f}"


def audit_rows(rows: list[dict]) -> dict:
    errors = []
    sku_rows = {}
    parent_children = {}

    for idx, row in enumerate(rows, start=2):
        sku = row.get("sku", "").strip()
        if not sku:
            errors.append({"row": idx, "error": "missing sku"})
            continue
        if sku in sku_rows:
            errors.append({"row": idx, "sku": sku, "error": "duplicate sku"})
        else:
            sku_rows[sku] = idx
        parent = row.get("parent_sku", "").strip()
        if parent:
            parent_children.setdefault(parent, []).append(sku)

    normalized = []
    counts = {"simple": 0, "variable": 0, "variation": 0}

    for idx, row in enumerate(rows, start=2):
        start_errors = len(errors)
        sku = row.get("sku", "").strip()
        if not sku or sku_rows.get(sku) != idx:
            continue

        parent_sku = row.get("parent_sku", "").strip()
        row_type = "variation" if parent_sku else ("variable" if sku in parent_children else "simple")
        name = row.get("name", "").strip()
        status = row.get("status", "").strip().lower()
        price_raw = row.get("price", "").strip()
        images = split_pipe(row.get("images", ""))
        stock = row.get("stock", "").strip()
        attributes = row.get("attributes", "").strip()

        if not name:
            errors.append({"row": idx, "sku": sku, "error": "missing name"})
        if status not in ALLOWED_STATUS:
            errors.append({"row": idx, "sku": sku, "error": "invalid status"})
        if row_type == "variation" and parent_sku not in sku_rows:
            errors.append({"row": idx, "sku": sku, "error": "missing parent sku"})
        if row_type == "variation" and not attributes:
            errors.append({"row": idx, "sku": sku, "error": "variation missing attributes"})

        try:
            price = parse_price(price_raw) if (row_type != "variable" or price_raw) else None
            if row_type in {"simple", "variation"} and price is None:
                errors.append({"row": idx, "sku": sku, "error": "missing price"})
        except ValueError as exc:
            errors.append({"row": idx, "sku": sku, "error": str(exc)})
            price = None

        if stock and not stock.isdigit():
            errors.append({"row": idx, "sku": sku, "error": "invalid stock"})

        normalized_images = []
        for url in images:
            if not url.startswith(("http://", "https://")):
                errors.append({"row": idx, "sku": sku, "error": f"invalid image url: {url}"})
            else:
                normalized_images.append(url)

        if len(errors) != start_errors:
            continue

        normalized.append(
            {
                "type": row_type,
                "sku": sku,
                "parent_sku": parent_sku,
                "name": name,
                "slug": row.get("slug", "").strip() or slugify(name),
                "regular_price": price or "",
                "stock_quantity": stock,
                "status": status,
                "categories": normalize_categories(row.get("categories", "")),
                "images": " | ".join(normalized_images),
                "attributes": attributes,
            }
        )
        counts[row_type] += 1

    invalid_rows = len({e["row"] for e in errors})
    return {
        "input_rows": len(rows),
        "valid_rows": len(normalized),
        "invalid_rows": invalid_rows,
        "types": counts,
        "errors": errors,
        "prepared_rows": normalized,
    }


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a WooCommerce migration CSV.")
    parser.add_argument("input_csv")
    parser.add_argument("--out", dest="output_csv")
    args = parser.parse_args()

    report = audit_rows(read_csv(Path(args.input_csv)))
    printable = {k: v for k, v in report.items() if k != "prepared_rows"}

    if report["errors"]:
        print(json.dumps(printable, indent=2, ensure_ascii=False))
        return 1

    if args.output_csv:
        write_csv(Path(args.output_csv), report["prepared_rows"])
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
