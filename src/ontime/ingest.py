"""Network-only phase. All analytical phases are offline.

The tracked manifest pins immutable raw URLs and hashes. A missing/corrupt file
is downloaded atomically; a valid cache is never refreshed or re-dated.
"""
import csv
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from .config import DATA, RAW, ensure_dirs

NAMES = (
    "olist_orders_dataset", "olist_order_items_dataset", "olist_order_payments_dataset",
    "olist_order_reviews_dataset", "olist_customers_dataset", "olist_sellers_dataset",
    "olist_products_dataset", "olist_geolocation_dataset", "product_category_name_translation",
)
REVISION = "d9e49802f3e92d09ee94ab9ccc5e457f207a8959"
BASE = f"https://raw.githubusercontent.com/olist/work-at-olist-data/{REVISION}/datasets"


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def download():
    ensure_dirs()
    manifest_path = DATA / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for name in NAMES:
        filename = name + ".csv"
        target = RAW / filename
        previous = manifest.get(filename, {})
        if target.exists() and previous.get("sha256") == sha256(target):
            print(f"cache verified: {filename}", flush=True)
            continue
        url = previous.get("url", f"{BASE}/{filename}")
        partial = target.with_suffix(".csv.partial")
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "OnTime-reproducible-analysis"})
                with urllib.request.urlopen(req, timeout=120) as response, partial.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                digest = sha256(partial)
                if previous.get("sha256") and digest != previous["sha256"]:
                    raise ValueError(f"Pinned checksum mismatch: {filename}")
                with partial.open(encoding="utf-8-sig", newline="") as handle:
                    reader = csv.reader(handle)
                    header = next(reader)
                    if len(header) < 2 or "<html" in header[0].lower():
                        raise ValueError(f"Not a CSV: {filename}")
                partial.replace(target)
                manifest[filename] = previous or {
                    "url": url, "sha256": digest, "bytes": target.stat().st_size,
                    "retrieved_utc": datetime.now(timezone.utc).date().isoformat(),
                }
                manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
                print(f"downloaded: {filename} ({target.stat().st_size:,} bytes)", flush=True)
                break
            except Exception:
                partial.unlink(missing_ok=True)
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    source = """# Data provenance

Source: **Brazilian E-Commerce Public Dataset by Olist**, provided by Olist and
André Sionek, covering anonymised marketplace orders from 2016–2018.
[Original data card](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
No Kaggle API or authentication is used by this project.

Dataset licence: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The project's MIT licence covers its code, not the underlying data. Analytical
tables and figures derived from the data are attributed here under CC BY-NC-SA 4.0.
Raw data are intentionally excluded from git. A mirror's repository-level MIT
licence is not treated as permission to relicense the original data.

Raw GitHub source: [olist/work-at-olist-data](https://github.com/olist/work-at-olist-data),
Olist's own practical data-team exercise. All nine files are pinned to one commit.
Headers were checked across Athospd/work-at-olist-data, Faroja/Olist-Customers-Segementation,
olist/work-at-olist-data and vishalkirtaniya/e-com-data-analysis. The Athospd
revision 9f4e18586e6cb6b35b37361ec1939c75e5ba416c was rejected: its review CSV has
extra unnamed columns and malformed rows with review text in timestamp fields.
The clean upstream Olist copy was selected instead; rejected bytes are not used.

No modifications to the downloaded bytes. Transformations: explicit typed
staging; median coordinate per zip; deterministic review/payment/item reduction;
documented eligibility filters, histories, and statistical aggregations.

| File | Retrieval (UTC) | Bytes | SHA-256 | Exact raw URL |
|---|---|---:|---|---|
"""
    for filename, record in sorted(manifest.items()):
        source += f"| {filename} | {record['retrieved_utc']} | {record['bytes']} | `{record['sha256']}` | {record['url']} |\n"
    (DATA / "SOURCE.md").write_text(source, encoding="utf-8")


if __name__ == "__main__":
    download()
