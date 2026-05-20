CREATE TABLE IF NOT EXISTS orders
(
    -- Posting identifiers
    posting_number      String,
    order_id            UInt64,
    order_number        String,
    delivery_schema     LowCardinality(String),  -- FBO or FBS

    -- Status
    status              LowCardinality(String),

    -- Timestamps
    created_at          DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),
    in_process_at       DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),

    -- Product line item
    sku                 UInt64,
    offer_id            String,
    product_name        String,
    quantity            UInt32,
    price               Decimal(18, 4),
    currency_code       LowCardinality(String),

    -- Analytics data
    region              String,
    city                String,
    delivery_type       LowCardinality(String),

    -- Financial data (per product line)
    commission_amount   Decimal(18, 2),
    commission_percent  Float32,
    payout              Decimal(18, 2),

    INDEX idx_posting_number posting_number TYPE bloom_filter GRANULARITY 1,
    INDEX idx_sku sku TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_at)
ORDER BY (posting_number, sku)
SETTINGS index_granularity = 8192;
