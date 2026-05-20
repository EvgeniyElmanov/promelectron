CREATE TABLE IF NOT EXISTS stocks
(
    sku                     UInt64,
    item_code               String,
    item_name               String,
    warehouse_name          LowCardinality(String),

    -- Stock levels
    free_to_sell_amount     UInt32,
    promised_amount         UInt32,
    reserved_amount         UInt32,

    -- Snapshot timestamp
    snapshot_at             DateTime64(3, 'UTC') CODEC(DoubleDelta, LZ4),

    INDEX idx_item_code item_code TYPE bloom_filter GRANULARITY 1
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(snapshot_at)
ORDER BY (sku, warehouse_name, snapshot_at)
SETTINGS index_granularity = 8192;
