CREATE TABLE IF NOT EXISTS transactions
(
    -- Operation identifiers
    operation_id        Int64,
    operation_type      String,
    operation_type_name String,
    operation_date      DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),

    -- Linked posting
    posting_number      String,
    delivery_schema     LowCardinality(String),

    -- Financial amounts
    amount              Decimal(18, 2),
    accruals_for_sale   Decimal(18, 2),
    sale_commission     Decimal(18, 2),
    delivery_charge     Decimal(18, 2),
    return_delivery_charge Decimal(18, 2),

    -- Associated items (first item sku/name for quick access)
    item_sku            UInt64,
    item_name           String,

    -- Services as parallel arrays
    service_names       Array(String),
    service_prices      Array(Decimal(18, 2)),

    INDEX idx_posting_number posting_number TYPE bloom_filter GRANULARITY 1,
    INDEX idx_operation_type operation_type TYPE set(50) GRANULARITY 1
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(operation_date)
ORDER BY (operation_id, operation_date)
SETTINGS index_granularity = 8192;
