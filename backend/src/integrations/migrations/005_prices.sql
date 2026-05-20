CREATE TABLE IF NOT EXISTS prices
(
    product_id                          UInt64,
    offer_id                            String,

    -- Price fields
    currency_code                       LowCardinality(String),
    price                               Decimal(18, 2),
    marketing_seller_price              Decimal(18, 2),
    min_price                           Decimal(18, 2),
    old_price                           Decimal(18, 2),
    retail_price                        Decimal(18, 2),
    net_price                           Decimal(18, 2),
    vat                                 Float32,
    auto_action_enabled                 UInt8,

    -- Commissions
    acquiring                           Float32,
    volume_weight                       Float32,
    sales_percent_fbo                   Float32,
    sales_percent_fbs                   Float32,

    -- Price indexes
    price_index_color                   LowCardinality(String),
    ozon_index_min_price                Decimal(18, 2),
    ozon_index_value                    Float32,
    external_index_min_price            Decimal(18, 2),
    external_index_value                Float32,
    self_marketplaces_index_min_price   Decimal(18, 2),
    self_marketplaces_index_value       Float32,

    -- Sync timestamp used as version for ReplacingMergeTree
    updated_at                          DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),

    INDEX idx_offer_id offer_id TYPE bloom_filter GRANULARITY 1
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY product_id
SETTINGS index_granularity = 8192;
