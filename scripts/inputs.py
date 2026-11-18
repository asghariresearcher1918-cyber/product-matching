"""All supplier listings: the owner's original file (products_input.csv) + products found later (data/products_added.csv)."""
import csv
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent


def load_rows():
    rows = list(csv.DictReader(open(ROOT / "products_input.csv", encoding="utf-8-sig")))
    add = ROOT / "data" / "products_added.csv"
    if add.exists():
        rows += [{k: r[k] for k in ("id", "supplier", "title", "url")} for r in csv.DictReader(open(add, encoding="utf-8"))]
    return rows
