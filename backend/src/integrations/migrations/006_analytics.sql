CREATE TABLE IF NOT EXISTS analytics_sales
(
    sku             UInt64,
    sku_name        String,
    date            Date,
    revenue         Decimal(18, 2),
    ordered_units   UInt32,
    synced_at       DateTime64(3, 'UTC')
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(date)
ORDER BY (sku, date);
