CREATE TABLE IF NOT EXISTS products
(
    product_id          UInt64,
    offer_id            String,
    name                String,
    barcode             String,

    -- Pricing
    marketing_price     Decimal(18, 2),
    min_price           Decimal(18, 2),
    old_price           Decimal(18, 2),
    price               Decimal(18, 2),
    currency_code       LowCardinality(String),
    vat                 LowCardinality(String),

    -- FBO stocks
    fbo_present         UInt32,
    fbo_reserved        UInt32,

    -- FBS stocks
    fbs_present         UInt32,
    fbs_reserved        UInt32,

    -- Status
    visible             UInt8,
    status              LowCardinality(String),
    archived            UInt8,

    -- Images
    images              Array(String),
    primary_image       String,

    -- Dimensions
    volume_weight       Float32,
    is_kgt              UInt8,

    -- Timestamps
    created_at          DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),
    updated_at          DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),

    INDEX idx_offer_id offer_id TYPE bloom_filter GRANULARITY 1
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(created_at)
ORDER BY product_id
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS sync_checkpoints
(
    sync_key        String,
    entity_type     String,
    last_synced_at  DateTime64(3, 'UTC'),
    synced_at       DateTime64(3, 'UTC') DEFAULT now64(3),
    items_synced    UInt64
)
ENGINE = ReplacingMergeTree(synced_at)
ORDER BY (sync_key, entity_type)
SETTINGS index_granularity = 8192;
