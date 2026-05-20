CREATE TABLE IF NOT EXISTS product_queries
(
    sku                   UInt64,
    offer_id              String,
    name                  String,
    category              String,
    unique_search_users   UInt32,
    gmv                   Decimal(18, 2),
    date_from             Date,
    date_to               Date,
    synced_at             DateTime64(3, 'UTC')
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(date_from)
ORDER BY (sku, date_from);
