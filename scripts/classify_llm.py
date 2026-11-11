"""Step 3 - per-row decision by Claude (structured output), constrained to catalogue IDs.

For each row: page text + attributes/options + product image + the catalogue candidates of the row's brand.
The model must pick catalogue IDs (or NONE), quote evidence, and say where each fact came from.
Results are cached per row in llm_results/<id>.json (resumable; never re-sent once stored).

Usage:
  python -I scripts/classify_llm.py --ids FILE --dry-run [--show N]   # build requests only, no API call
  python -I scripts/classify_llm.py --ids FILE --sync --limit 50       # small test, one request at a time
  python -I scripts/classify_llm.py --ids FILE --batch-submit          # Message Batches API (50% price)
  python -I scripts/classify_llm.py --batch-collect BATCH_ID
Credentials: ANTHROPIC_API_KEY (or an `ant auth login` profile) must be available to the SDK.
"""
import argparse
import base64
import csv
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "llm_results"
CAT = ROOT / "catalogue"
MODEL = "claude-opus-5-5"

SYSTEM = """You classify one supplier product listing for a UK aesthetic-pharmacy price-comparison site.
Goal: put the listing in the right FAMILY (brand + product line), VARIANT and PACK, using the PRODUCT PAGE and IMAGE,
checked against the OFFICIAL UK reference given in the catalogue candidates. The listing title is unreliable.

Hard rules (from the domain owner):
1. Never decide route, strength, volume, pack size, form, lidocaine or market from the title alone. Use page text, options,
   attributes and the image; for each such fact say which source it came from. If only the title states it, say so (source=title_only).
2. Equivalences: IV = I/V = i.v. = intravenous; IM = I/M = i.m. = intramuscular; SC = S/C = SubQ = subcutaneous.
3. Status/admin words are not part of the name ("out of stock", "prescription item zero VAT", "stock item VAT payable",
   "POM", "available on request", "training required", "chilled", "new", "clone", expiry dates). Report them in status_words.
4. Descriptive words do not create a new product ("injection", "dermal filler", "skin booster", "UK official", "CE").
5. VARIANT = things that make it a different product: model/line, strength/units, lidocaine yes/no, UK/CE vs Korean/non-UK
   version, form. PACK = number of syringes/vials and volume per unit. Volume and count are NEVER variant identity.
6. If the page contradicts itself, the image, or the official catalogue presentation, do NOT guess: needs_human_review=true and explain.
7. "clone", "replaced for X", "alternative to X", "equivalent": decide from page + catalogue whether it is the same product.
8. Bundles/kits ("A + B", "kit", "bundle", "buy X get Y") -> kind=bundle. Posters, banners, forms, leaflets, rulers, cooling
   packs -> kind=marketing_or_accessory. Creams, serums, peels, masks, supplements, microneedles -> kind=non_injectable.
   Courses -> kind=training_or_service.
9. If one page offers a selector with several products/packs, describe the default/first option and list the others in options_seen.
10. Use the image: read the pack text; if it shows a different product, model, strength or count than the text, report it.
11. Never merge different models of one brand (Ultra 2 vs Ultra 3; RHA vs Redensity) or lidocaine vs non-lidocaine.
Pick family_id / variant_id / presentation_id ONLY from the candidates. If none fits, use "NONE" and fill proposed_line.
confidence: confirmed = page (+image) agree with an OFFICIAL catalogue presentation; likely = page clear but the catalogue
entry is not official, or minor gaps; uncertain = conflict or insufficient information (then needs_human_review=true).
Quotes must be copied verbatim from the page text or read from the image (max 25 words each)."""

STR = {"type": "string"}
SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["product", "bundle", "marketing_or_accessory", "non_injectable", "training_or_service", "other"]},
        "family_id": STR, "variant_id": STR, "presentation_id": STR, "proposed_line": STR,
        "lidocaine": {"type": "string", "enum": ["yes", "no", "not_stated"]},
        "lidocaine_source": {"type": "string", "enum": ["page_text", "options", "image", "title_only", "none"]},
        "market": {"type": "string", "enum": ["UK/CE", "KR", "other_non_UK", "not_stated"]},
        "strength": STR,
        "unit_type": {"type": "string", "enum": ["syringe", "vial", "ampoule", "kit", "other", "not_stated"]},
        "unit_count": STR, "unit_volume_ml": STR,
        "pack_source": {"type": "string", "enum": ["page_text", "options", "image", "title_only", "none"]},
        "status_words": {"type": "array", "items": STR},
        "options_seen": {"type": "array", "items": STR},
        "image_reads": STR,
        "image_matches_text": {"type": "string", "enum": ["yes", "no", "no_image", "unclear"]},
        "evidence": {"type": "array", "items": {"type": "object", "properties": {
            "source": {"type": "string", "enum": ["page_text", "page_title", "options", "image", "catalogue"]}, "quote": STR},
            "required": ["source", "quote"], "additionalProperties": False}},
        "conflicts": {"type": "array", "items": STR},
        "confidence": {"type": "string", "enum": ["confirmed", "likely", "uncertain"]},
        "needs_human_review": {"type": "boolean"},
        "review_reason": STR,
    },
    "required": ["kind", "family_id", "variant_id", "presentation_id", "proposed_line", "lidocaine", "lidocaine_source", "market",
                 "strength", "unit_type", "unit_count", "unit_volume_ml", "pack_source", "status_words", "options_seen", "image_reads",
                 "image_matches_text", "evidence", "conflicts", "confidence", "needs_human_review", "review_reason"],
    "additionalProperties": False,
}


def load_catalogue():
    fam = list(csv.DictReader(open(CAT / "families.csv", encoding="utf-8")))
    var = list(csv.DictReader(open(CAT / "variants.csv", encoding="utf-8")))
    pre = list(csv.DictReader(open(CAT / "presentations.csv", encoding="utf-8")))
    src = list(csv.DictReader(open(CAT / "sources.csv", encoding="utf-8")))
    return fam, var, pre, src


def candidates(brand, fam, var, pre, src):
    """Stage 2 (pre-selection): every catalogue family of the row's brand, with its variants/presentations/sources."""
    b = brand.split("/")[0].split("(")[0].strip().lower()
    out = []
    for f in fam:
        if f["brand"].lower().startswith(b[:6]) or b.startswith(f["brand"].lower()[:6]):
            out.append({
                "family_id": f["family_id"], "brand": f["brand"], "line": f["line"], "reference_status": f["reference_status"],
                "variants": [{"variant_id": v["variant_id"], "label": v["label"], "attributes": json.loads(v["attributes"]),
                              "reference_status": v["reference_status"]} for v in var if v["family_id"] == f["family_id"]],
                "presentations": [{k: p[k] for k in ("presentation_id", "unit", "unit_volume_ml", "units_per_pack", "pack_sizes", "reference_status")}
                                  for p in pre if any(p["variant_id"] == v["variant_id"] for v in var if v["family_id"] == f["family_id"])],
                "official_quote": [s["quote"] for s in src if s["family_id"] == f["family_id"]][:2],
            })
    return out


def image_block(page):
    d = ROOT / "cache" / re.sub(r"[^a-z0-9]+", "_", page["supplier"].lower()).strip("_")
    files = list(d.glob(page["id"] + ".img.*"))
    if not files:
        return None
    try:
        from PIL import Image
        im = Image.open(files[0]).convert("RGB")
        im.thumbnail((800, 800))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        data = base64.standard_b64encode(buf.getvalue()).decode()
    except Exception:
        return None
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}}


def user_content(row, page, cands):
    pg = {
        "input_title (unreliable)": row["title"], "supplier": row["supplier"], "url": row["url"],
        "page_title": page.get("page_title", ""), "breadcrumb": page.get("breadcrumb", ""), "stock_text": page.get("stock_text", ""),
        "short_description": (page.get("short_description") or "")[:1500],
        "description": (page.get("description") or "")[:3500],
        "main_text_excerpt": (page.get("main_text") or "")[:2500] if len(page.get("description") or "") < 300 else "",
        "attributes": page.get("attributes", {}), "options": page.get("options", {}),
    }
    content = []
    img = image_block(page)
    if img:
        content.append(img)
    content.append({"type": "text", "text":
                    "CATALOGUE CANDIDATES (choose IDs only from here):\n" + json.dumps(cands, ensure_ascii=False) +
                    "\n\nSUPPLIER PAGE:\n" + json.dumps(pg, ensure_ascii=False) +
                    ("\n\n(The image above is the main product image of this page.)" if img else "\n\n(No product image available.)")})
    return content


def build(ids_file):
    rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "data" / "scope_rows.csv", encoding="utf-8"))}
    pages = {}
    for l in open(ROOT / "pages.jsonl", encoding="utf-8"):
        p = json.loads(l)
        pages[p["id"]] = p
    fam, var, pre, src = load_catalogue()
    ids = [l.strip() for l in open(ROOT / ids_file) if l.strip()]
    reqs = []
    for i in ids:
        if i not in rows or i not in pages or (RES / f"{i}.json").exists():
            continue
        cands = candidates(rows[i]["brand"], fam, var, pre, src)
        params = {
            "model": MODEL, "max_tokens": 8000,
            "system": [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            "output_config": {"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": [{"role": "user", "content": user_content(rows[i], pages[i], cands)}],
        }
        reqs.append((i, params))
    return reqs


def save(i, msg_json, usage):
    RES.mkdir(exist_ok=True)
    (RES / f"{i}.json").write_text(json.dumps({"id": i, "result": msg_json, "usage": usage}, ensure_ascii=False, indent=1), encoding="utf-8")


def parse_message(msg):
    if msg.stop_reason == "refusal":
        return {"_error": "refusal"}
    if msg.stop_reason == "max_tokens":
        return {"_error": "max_tokens"}
    text = next((b.text for b in msg.content if b.type == "text"), "")
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="scope_ids.txt")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch-submit", action="store_true")
    ap.add_argument("--batch-collect")
    a = ap.parse_args()
    if a.batch_collect:
        import anthropic
        c = anthropic.Anthropic()
        n = 0
        for r in c.messages.batches.results(a.batch_collect):
            if r.result.type == "succeeded":
                save(r.custom_id, parse_message(r.result.message), r.result.message.usage.model_dump())
                n += 1
            else:
                print("not succeeded:", r.custom_id, r.result.type)
        print("collected", n)
        return
    reqs = build(a.ids)
    if a.limit:
        reqs = reqs[: a.limit]
    print(f"{len(reqs)} requests to send (rows already in llm_results/ are skipped)")
    if a.dry_run:
        for i, p in reqs[: a.show]:
            txt = p["messages"][0]["content"][-1]["text"]
            print(f"--- {i}: image={'yes' if len(p['messages'][0]['content']) > 1 else 'no'} chars={len(txt)}\n{txt[:1500]}\n")
        tot = sum(len(p["messages"][0]["content"][-1]["text"]) for _, p in reqs)
        print(f"approx text tokens: {tot // 4:,} (+ ~{len(SYSTEM) // 4} cached system, + images)")
        return
    import anthropic
    c = anthropic.Anthropic()
    if a.batch_submit:
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request
        b = c.messages.batches.create(requests=[Request(custom_id=i, params=MessageCreateParamsNonStreaming(**p)) for i, p in reqs])
        print("batch id:", b.id, b.processing_status)
        (ROOT / "logs").mkdir(exist_ok=True)
        with open(ROOT / "logs" / "batches.txt", "a") as f:
            f.write(f"{b.id}\t{len(reqs)}\n")
        return
    if a.sync:
        for i, p in reqs:
            try:
                msg = c.messages.create(**p)
                save(i, parse_message(msg), msg.usage.model_dump())
                print("ok", i, msg.usage.input_tokens, msg.usage.output_tokens)
            except anthropic.RateLimitError as e:
                print("rate limited, stop and resume later:", e)
                break
            except anthropic.APIStatusError as e:
                print("API error", i, e.status_code, e.message)
            except anthropic.APIConnectionError as e:
                print("connection error", i, e)
                break


if __name__ == "__main__":
    sys.exit(main())
