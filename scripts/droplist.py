"""Shared list of listing ids to exclude everywhere — pages the shop silently repointed to a DIFFERENT product
(confirmed via structured JSON-LD name vs our title). Kept in data/listing_drop.csv."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def dropped():
    p = ROOT / "data/listing_drop.csv"
    if not p.exists():
        return set()
    return {r["id"] for r in csv.DictReader(open(p, encoding="utf-8")) if r.get("id")}
