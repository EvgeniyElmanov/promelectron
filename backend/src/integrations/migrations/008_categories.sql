CREATE TABLE IF NOT EXISTS categories
(
    category_id     UInt64,
    category_name   String,
    parent_id       UInt64,
    level           UInt8,
    type_id         UInt64,
    type_name       String
)
ENGINE = ReplacingMergeTree
ORDER BY category_id
SETTINGS index_granularity = 8192;
