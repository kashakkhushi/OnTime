# Data provenance

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
| olist_customers_dataset.csv | 2026-09-09 | 8562270 | `c26c17f59f3027a6a0dbeb8f1fa373c38f3323ecc84f225a8f4820e5bb288df8` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_customers_dataset.csv |
| olist_geolocation_dataset.csv | 2026-09-09 | 61273883 | `b514f6fc991b9566aeba02aa5d67e2c3630f034b60a0e05aa0d082a3b66d88d6` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_geolocation_dataset.csv |
| olist_order_items_dataset.csv | 2026-09-09 | 15007623 | `4f6abdbbc94036d0df4a76fa0520c072e31a40119d70f7f370fba1e2285d2bcb` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_order_items_dataset.csv |
| olist_order_payments_dataset.csv | 2026-09-09 | 5647783 | `61674868ed7b872aac3dcd95bf774448a88f6426b183f21be55f75af021ffdec` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_order_payments_dataset.csv |
| olist_order_reviews_dataset.csv | 2026-09-09 | 14451670 | `012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_order_reviews_dataset.csv |
| olist_orders_dataset.csv | 2026-09-09 | 17654914 | `8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_orders_dataset.csv |
| olist_products_dataset.csv | 2026-09-09 | 2379446 | `3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_products_dataset.csv |
| olist_sellers_dataset.csv | 2026-09-09 | 163589 | `31eb9bd50d684526a78f2389413ce61841e97692de7b828fe7d956b534586312` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/olist_sellers_dataset.csv |
| product_category_name_translation.csv | 2026-09-09 | 2613 | `a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278` | https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/datasets/product_category_name_translation.csv |
