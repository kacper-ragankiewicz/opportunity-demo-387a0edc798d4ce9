# WooCommerce migration audit proof

This repository is a small proof of approach for a WooCommerce migration where catalog quality is a major risk before import, integration mapping, and deployment.

For a shop with ~1000 products, broken SKUs, variation links, prices, stock values, or image URLs often slow migration work down and create problems in staging or after launch.

## What this demonstrates

A minimal Python CLI that:
- reads a synthetic product export,
- validates WooCommerce-relevant rules,
- detects parent/variation issues,
- normalizes slugs and category paths,
- writes an import-ready CSV only when the dataset passes validation.

## Implemented

Validation rules:
- unique SKU
- required `sku`, `name`, `status`
- `status` must be `publish` or `draft`
- non-negative numeric price for simple products and variations
- variation rows must reference an existing parent and include attributes
- image URLs must be `http` or `https`
- stock must be a non-negative integer when present

Normalization:
- generate slug from name when missing
- normalize category path spacing (`Men > T-Shirts`)
- classify rows as `simple`, `variable`, or `variation`

## Intentionally simplified

- synthetic CSV format instead of a real client export
- no live WooCommerce API calls
- no plugin/integration migration
- no deployment or performance remediation

## Run

```bash
python migration_audit.py data/sample_products.csv --out prepared_products.csv
```

If validation passes, `prepared_products.csv` is created. If not, the CLI prints a JSON report and exits without writing the output file.

## Test

```bash
python -m unittest discover -s tests -v
```

Included tests cover both a passing catalog and failure cases. They are included for local verification and were not executed in this environment.

## Why this proof fits the opportunity

Before touching a troubled WooCommerce installation, this kind of repeatable preflight step reduces migration risk and makes later staging import, integration mapping, and cutover work more predictable.


## Verification status

Static validation of paths, sizes and Python/JSON syntax only. Application, tests and build NOT executed by the generator.
