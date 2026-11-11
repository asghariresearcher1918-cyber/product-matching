"""Step 4 - deterministic checks on the model's decisions, then the grouped outputs.

Checks (any failure -> needs_human_review):
  C1 IDs exist in the catalogue (or NONE)
  C2 pack / lidocaine / market taken from the title only (rule: never from title alone)
  C3 presentation not among the OFFICIAL presentations of the chosen variant (official families only)
  C4 cross-supplier: same variant, different volume per unit, and no official reference to settle it
  C5 model's own conflicts / image mismatch / refusal / missing result
Outputs (output/scope/): products_grouped.csv, review_queue.csv, non_products.csv, run_report.md

Usage: python -I scripts/validate.py [--ids scope_ids.txt]
"""
import argparse
import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "scope"
COLS = ["id", "supplier", "title", "url", "kind", "family_id", "family_name", "variant_id", "variant_label", "pack_id", "pack_label",
        "lidocaine", "market", "strength", "unit_type", "unit_count", "unit_volume_ml", "status_words", "image_url", "image_reads",
        "evidence", "reference_status", "confidence", "needs_human_review", "review_reason"]


def fnum(x):
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="scope_ids.txt")
    a = ap.parse_args()
    ids = [l.strip() for l in open(ROOT / a.ids) if l.strip()]
    rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "data" / "scope_rows.csv", encoding="utf-8"))}
    pages = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "pages.jsonl", encoding="utf-8")}
    errs = {e["id"]: e["error"] for e in csv.DictReader(open(ROOT / "scrape_errors.csv", encoding="utf-8"))}
    fam = {f["family_id"]: f for f in csv.DictReader(open(ROOT / "catalogue" / "families.csv", encoding="utf-8"))}
    var = {v["variant_id"]: v for v in csv.DictReader(open(ROOT / "catalogue" / "variants.csv", encoding="utf-8"))}
    pre = {p["presentation_id"]: p for p in csv.DictReader(open(ROOT / "catalogue" / "presentations.csv", encoding="utf-8"))}
    out = []
    for i in ids:
        r = rows[i]
        base = {c: "" for c in COLS} | {"id": i, "supplier": r["supplier"], "title": r["title"], "url": r["url"]}
        f = ROOT / "llm_results" / f"{i}.json"
        if i not in pages:
            out.append(base | {"confidence": "uncertain", "needs_human_review": "true",
                               "review_reason": f"page not available ({errs.get(i, 'not scraped')}) - not classified"})
            continue
        if not f.exists():
            out.append(base | {"confidence": "", "needs_human_review": "", "review_reason": "not yet classified (step 3 not run)"})
            continue
        d = json.loads(f.read_text(encoding="utf-8"))["result"]
        reasons = []
        if "_error" in d:
            out.append(base | {"confidence": "uncertain", "needs_human_review": "true", "review_reason": f"model: {d['_error']}"})
            continue
        fid, vid, pid = d["family_id"], d["variant_id"], d["presentation_id"]
        # C1
        if fid != "NONE" and fid not in fam:
            reasons.append(f"C1 unknown family_id {fid}")
        if vid not in ("", "NONE") and vid not in var:
            reasons.append(f"C1 unknown variant_id {vid}")
        # C2
        for k, src in (("pack", d["pack_source"]), ("lidocaine", d["lidocaine_source"])):
            if src == "title_only":
                reasons.append(f"C2 {k} only in title")
        # C3
        fr = fam.get(fid, {})
        if fr.get("reference_status") == "official" and d["kind"] == "product":
            offs = [p for p in pre.values() if p["variant_id"] == vid and p["reference_status"] == "official"]
            vol, cnt = fnum(d["unit_volume_ml"]), d["unit_count"]
            if offs and vol is not None and not any(fnum(p["unit_volume_ml"]) == vol for p in offs if p["unit_volume_ml"]):
                reasons.append(f"C3 volume {vol} ml not an official presentation ({', '.join(p['unit_volume_ml'] for p in offs)})")
            if offs and cnt and offs[0]["pack_sizes"] and not any(str(cnt) in p["pack_sizes"] or str(cnt) == p["units_per_pack"] for p in offs):
                reasons.append(f"C3 count {cnt} not an official pack size ({offs[0]['pack_sizes']})")
        # C5
        reasons += [f"model: {c}" for c in d["conflicts"]]
        if d["image_matches_text"] == "no":
            reasons.append("image does not match text: " + d["image_reads"][:120])
        if d["needs_human_review"] and d["review_reason"]:
            reasons.append("model: " + d["review_reason"])
        vlabel = " / ".join(x for x in [fr.get("line") or d["proposed_line"], d["strength"],
                                         {"yes": "lidocaine", "no": "no lidocaine"}.get(d["lidocaine"], "lidocaine not stated"),
                                         d["market"] if d["market"] != "not_stated" else ""] if x)
        plabel = f"{d['unit_count'] or '?'} x {d['unit_volume_ml'] + ' ml ' if d['unit_volume_ml'] else ''}{d['unit_type']}"
        vkey = vid if vid not in ("", "NONE") else f"{fid}/{vlabel}"
        conf = d["confidence"]
        hard = [x for x in reasons if not x.startswith("model: ") or d["needs_human_review"]]
        if any(x.startswith(("C1", "C2", "C3")) for x in reasons) or d["image_matches_text"] == "no":
            conf = "uncertain"
        out.append(base | {
            "kind": d["kind"], "family_id": fid, "family_name": f"{fr.get('brand', '')} {fr.get('line', '')}".strip() or d["proposed_line"],
            "variant_id": vkey, "variant_label": vlabel, "pack_id": f"{vkey}/{plabel}", "pack_label": plabel,
            "lidocaine": d["lidocaine"], "market": d["market"], "strength": d["strength"], "unit_type": d["unit_type"],
            "unit_count": d["unit_count"], "unit_volume_ml": d["unit_volume_ml"], "status_words": "; ".join(d["status_words"]),
            "image_url": pages[i].get("image_url", ""), "image_reads": d["image_reads"],
            "evidence": " | ".join(f"{e['source']}: \"{e['quote']}\"" for e in d["evidence"][:4]),
            "reference_status": fr.get("reference_status", "not_found"), "confidence": conf,
            "needs_human_review": "true" if conf == "uncertain" or hard else "false", "review_reason": "; ".join(reasons)})
    # C4 cross-supplier volume consistency where no official reference
    byv = collections.defaultdict(list)
    for r in out:
        if r["kind"] == "product" and r["reference_status"] != "official" and r["unit_volume_ml"]:
            byv[r["variant_id"]].append(r)
    xnotes = []
    for vid, rs in byv.items():
        vols = collections.Counter(r["unit_volume_ml"] for r in rs)
        if len(vols) > 1:
            xnotes.append(f"{vid}: {dict(vols)}")
            for r in rs:
                r["review_reason"] = "; ".join(x for x in [r["review_reason"], f"C4 suppliers disagree on volume {dict(vols)} (no official ref)"] if x)
                r["confidence"], r["needs_human_review"] = "uncertain", "true"
    OUT.mkdir(parents=True, exist_ok=True)
    prods = [r for r in out if r["kind"] in ("product", "") or not r["kind"]]
    others = [r for r in out if r["kind"] and r["kind"] != "product"]
    for name, rs in (("products_grouped", prods), ("non_products", others)):
        with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            w.writerows(rs)
    sup = collections.defaultdict(set)
    for r in out:
        sup[r["family_id"]].add(r["supplier"])
    rq = sorted([r for r in out if r["needs_human_review"] == "true"], key=lambda r: (-len(sup[r["family_id"]]), r["family_id"]))
    with open(OUT / "review_queue.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["suppliers_in_family"] + COLS)
        w.writeheader()
        for r in rq:
            w.writerow({"suppliers_in_family": len(sup[r["family_id"]])} | r)
    json.dump({"cross_supplier_volume_conflicts": xnotes}, open(OUT / "_validate_notes.json", "w"), indent=1)
    c = collections.Counter(r["confidence"] or "not_classified" for r in out)
    k = collections.Counter(r["kind"] or "-" for r in out)
    print(f"rows {len(out)} | kinds {dict(k)} | confidence {dict(c)} | review {len(rq)}")


if __name__ == "__main__":
    main()
